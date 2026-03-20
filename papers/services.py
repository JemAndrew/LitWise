import hashlib
import json
import logging
import os

import anthropic
import fitz
import requests
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import transaction
from django.utils import timezone
from decouple import config

from .models import Author, Paper, PaperAuthor

logger = logging.getLogger(__name__)

CROSSREF_EMAIL = config('CROSSREF_EMAIL', default='')
CROSSREF_API_URL = 'https://api.crossref.org/works/'


class DOINotFoundError(Exception):
    pass


class DuplicateDOIError(Exception):
    pass


class CrossrefFetchError(Exception):
    pass


class PaperImportService:

    @staticmethod
    def import_by_doi(doi, user):
        """Fetch metadata from Crossref and create a Paper with authors."""
        doi = doi.strip().strip('/')

        if Paper.objects.filter(doi=doi, user=user).exists():
            raise DuplicateDOIError(f'Paper with DOI {doi} already in your library.')

        data = PaperImportService._fetch_crossref(doi)
        paper = PaperImportService._create_paper(data, doi, user)
        PaperImportService._create_authors(data, paper)
        SearchService.update_search_vector(paper)
        return paper

    @staticmethod
    def _fetch_crossref(doi):
        headers = {'Accept': 'application/json'}
        params = {}
        if CROSSREF_EMAIL:
            params['mailto'] = CROSSREF_EMAIL

        try:
            response = requests.get(
                f'{CROSSREF_API_URL}{doi}',
                headers=headers,
                params=params,
                timeout=15,
            )
        except requests.RequestException as e:
            raise CrossrefFetchError(f'Failed to reach Crossref: {e}')

        if response.status_code == 404:
            raise DOINotFoundError(f'DOI not found: {doi}')
        if response.status_code != 200:
            raise CrossrefFetchError(
                f'Crossref returned status {response.status_code}'
            )

        return response.json()['message']

    @staticmethod
    @transaction.atomic
    def _create_paper(data, doi, user):
        title = ''.join(data.get('title', ['Untitled']))

        published = data.get('published-print') or data.get('published-online') or {}
        date_parts = published.get('date-parts', [[None]])[0]
        year = date_parts[0] if date_parts else None

        return Paper.objects.create(
            user=user,
            doi=doi,
            title=title,
            abstract=_clean_abstract(data.get('abstract', '')),
            year=year,
            journal=''.join(data.get('container-title', [])),
            volume=data.get('volume', ''),
            issue=data.get('issue', ''),
            pages=data.get('page', ''),
            publisher=data.get('publisher', ''),
            paper_type=data.get('type', 'article'),
            url=data.get('URL', ''),
            is_open_access=_check_open_access(data),
        )

    @staticmethod
    def _create_authors(data, paper):
        for i, author_data in enumerate(data.get('author', []), start=1):
            given = author_data.get('given', '')
            family = author_data.get('family', '')
            if not family:
                continue

            author, _ = Author.objects.get_or_create(
                given_name=given,
                family_name=family,
                defaults={
                    'orcid': author_data.get('ORCID', ''),
                    'affiliation': _first_affiliation(author_data),
                },
            )
            PaperAuthor.objects.create(paper=paper, author=author, order=i)


def _clean_abstract(abstract):
    """Strip JATS XML tags that Crossref sometimes includes."""
    if not abstract:
        return ''
    import re
    return re.sub(r'<[^>]+>', '', abstract).strip()


def _first_affiliation(author_data):
    affiliations = author_data.get('affiliation', [])
    if affiliations:
        return affiliations[0].get('name', '')
    return ''


def _check_open_access(data):
    licence = data.get('license', [])
    if not licence:
        return False
    url = licence[0].get('URL', '')
    return 'creativecommons.org' in url


class PDFService:

    @staticmethod
    def extract_text(pdf_file):
        """Extract text from a PDF file using PyMuPDF."""
        data = pdf_file.read()
        doc = fitz.open(stream=data, filetype='pdf')
        text = ''
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    @staticmethod
    def upload_pdf(paper, pdf_file):
        """Save PDF to paper, extract text, compute hash."""
        paper.pdf_file.save(pdf_file.name, pdf_file, save=False)

        pdf_file.seek(0)
        text = PDFService.extract_text(pdf_file)
        paper.full_text = text

        pdf_file.seek(0)
        file_hash = hashlib.sha256(pdf_file.read()).hexdigest()
        paper.full_text_hash = file_hash

        paper.save()
        SearchService.update_search_vector(paper)

    @staticmethod
    def create_paper_from_pdf(pdf_file, user):
        """Create a new Paper from a PDF upload."""
        name = os.path.splitext(pdf_file.name)[0]
        paper = Paper.objects.create(user=user, title=name)
        PDFService.upload_pdf(paper, pdf_file)
        return paper


class SummarisationService:

    @staticmethod
    def summarise_paper(paper_id):
        """Call Claude API to summarise a paper's full text."""
        paper = Paper.objects.get(pk=paper_id)
        if not paper.full_text:
            raise ValueError('Paper has no extracted text to summarise.')

        api_key = config('CLAUDE_API_KEY', default='')
        if not api_key:
            raise ValueError('CLAUDE_API_KEY is not configured.')

        # Truncate to ~50k chars to stay within context limits
        text = paper.full_text[:50000]

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=2000,
            messages=[{
                'role': 'user',
                'content': (
                    'You are an academic research assistant. Summarise the following '
                    'paper and return ONLY valid JSON with these keys:\n'
                    '- "overview": a concise overview (2-3 sentences)\n'
                    '- "methods": key methods used (2-3 sentences)\n'
                    '- "findings": main findings (2-3 sentences)\n'
                    '- "significance": why this paper matters (1-2 sentences)\n'
                    '- "keywords": a list of 5-8 relevant keywords\n\n'
                    f'Paper text:\n{text}'
                ),
            }],
        )

        response_text = message.content[0].text
        # Strip markdown code fences if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            lines = [l for l in lines if not l.startswith('```')]
            response_text = '\n'.join(lines)

        result = json.loads(response_text)

        paper.summary_overview = result.get('overview', '')
        paper.summary_methods = result.get('methods', '')
        paper.summary_findings = result.get('findings', '')
        paper.summary_significance = result.get('significance', '')
        paper.keywords_ai = result.get('keywords', [])
        paper.summary_generated_at = timezone.now()
        paper.save()

        logger.info('Summarisation complete for paper %s', paper_id)


class SearchService:

    @staticmethod
    def update_search_vector(paper):
        """Update the PostgreSQL full-text search vector for a paper."""
        Paper.objects.filter(pk=paper.pk).update(
            search_vector=(
                SearchVector('title', weight='A')
                + SearchVector('abstract', weight='B')
                + SearchVector('full_text', weight='C')
            )
        )

    @staticmethod
    def search(query, user):
        """Full-text search across user's papers, ranked by relevance."""
        search_query = SearchQuery(query)
        return (
            Paper.objects
            .filter(user=user, search_vector=search_query)
            .annotate(rank=SearchRank('search_vector', search_query))
            .order_by('-rank')
        )
