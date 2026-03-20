import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django_q.tasks import async_task
from decouple import config

from .forms import DOIImportForm, PDFUploadForm, SearchForm
from .models import Paper
from .services import (
    CrossrefFetchError,
    DOINotFoundError,
    DuplicateDOIError,
    PDFService,
    PaperImportService,
    SearchService,
)

logger = logging.getLogger(__name__)

ALLOWED_SORTS = {'-created_at', 'created_at', '-year', 'year', 'title'}


@login_required
def paper_list(request):
    qs = Paper.objects.filter(user=request.user).prefetch_related('paperauthor_set__author')

    status = request.GET.get('status', '')
    if status in dict(Paper.READING_STATUS_CHOICES):
        qs = qs.filter(reading_status=status)

    sort = request.GET.get('sort', '-created_at')
    if sort not in ALLOWED_SORTS:
        sort = '-created_at'
    qs = qs.order_by(sort)

    paginator = Paginator(qs, 20)
    papers = paginator.get_page(request.GET.get('page'))

    return render(request, 'papers/paper_list.html', {
        'papers': papers,
        'status_choices': Paper.READING_STATUS_CHOICES,
        'current_status': status,
        'current_sort': sort,
    })


@login_required
def paper_detail(request, pk):
    paper = get_object_or_404(Paper, pk=pk, user=request.user)
    authors = paper.paperauthor_set.select_related('author').order_by('order')
    notes = paper.notes.filter(user=request.user)

    return render(request, 'papers/paper_detail.html', {
        'paper': paper,
        'authors': authors,
        'notes': notes,
    })


@login_required
def paper_delete(request, pk):
    paper = get_object_or_404(Paper, pk=pk, user=request.user)
    if request.method == 'POST':
        paper.delete()
        messages.success(request, 'Paper deleted.')
        return redirect('papers:paper_list')
    return redirect('papers:paper_detail', pk=pk)


@login_required
def doi_import(request):
    if request.method == 'POST':
        form = DOIImportForm(request.POST)
        if form.is_valid():
            try:
                paper = PaperImportService.import_by_doi(form.cleaned_data['doi'], request.user)
                messages.success(request, f'Imported: {paper.title}')
                return redirect('papers:paper_detail', pk=paper.pk)
            except DuplicateDOIError as e:
                form.add_error('doi', str(e))
            except DOINotFoundError as e:
                form.add_error('doi', str(e))
            except CrossrefFetchError as e:
                form.add_error('doi', str(e))
    else:
        form = DOIImportForm()

    return render(request, 'papers/doi_import.html', {'form': form})


@login_required
def pdf_upload(request):
    if request.method == 'POST':
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            paper = PDFService.create_paper_from_pdf(
                form.cleaned_data['pdf_file'], request.user,
            )
            messages.success(request, f'Paper created from PDF: {paper.title}')
            return redirect('papers:paper_detail', pk=paper.pk)
    else:
        form = PDFUploadForm()

    return render(request, 'papers/pdf_upload.html', {'form': form})


@login_required
def paper_pdf_upload(request, pk):
    paper = get_object_or_404(Paper, pk=pk, user=request.user)
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        pdf_file = request.FILES['pdf_file']
        if not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, 'Only PDF files are accepted.')
        elif pdf_file.size > 50 * 1024 * 1024:
            messages.error(request, 'File size must be under 50 MB.')
        else:
            PDFService.upload_pdf(paper, pdf_file)
            messages.success(request, 'PDF uploaded and text extracted.')
    return redirect('papers:paper_detail', pk=pk)


@login_required
def request_summary(request, pk):
    paper = get_object_or_404(Paper, pk=pk, user=request.user)
    if request.method != 'POST':
        return redirect('papers:paper_detail', pk=pk)

    if not paper.full_text:
        messages.error(request, 'Upload a PDF first to enable summarisation.')
        return redirect('papers:paper_detail', pk=pk)

    api_key = config('CLAUDE_API_KEY', default='')
    if not api_key:
        messages.error(request, 'CLAUDE_API_KEY is not configured.')
        return redirect('papers:paper_detail', pk=pk)

    async_task('papers.tasks.summarise_paper_task', str(paper.pk))
    messages.success(request, 'Summarisation queued. Refresh in a moment to see results.')
    return redirect('papers:paper_detail', pk=pk)


@login_required
def search_papers(request):
    form = SearchForm(request.GET or None)
    papers = []
    query = ''

    if form.is_valid():
        query = form.cleaned_data['q']
        papers = SearchService.search(query, request.user)

    return render(request, 'papers/search_results.html', {
        'form': form,
        'papers': papers,
        'query': query,
    })
