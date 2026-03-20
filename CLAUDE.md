# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

LitWise is a Django-based academic paper management application for PhD and Master's
students. It helps researchers organise literature reviews with AI-powered summaries,
smart reading queues, and full-text search — going beyond basic reference managers
like Zotero or Mendeley.

## Commands
```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Run development server
python manage.py runserver

# Database
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Background task queue (required for async operations)
python manage.py qcluster

# Tests
python manage.py test
python manage.py test papers
python manage.py test papers.tests.TestClassName.test_method
```

## Architecture

- **config/** — Django project settings, URL routing, WSGI/ASGI entry points
- **papers/** — Core app: paper ingestion, metadata, AI summaries, full-text search
- **accounts/** — User authentication (uses Django's built-in User model)
- **media/** — Uploaded PDFs
- **templates/** / **static/** — Frontend (Tailwind CSS, not yet implemented)

### Layer Responsibilities (strict — do not mix)

- **Models** — data structure only, no business logic
- **Views** — request/response handling only, delegate everything to services
- **Services** — all business logic lives here (`papers/services.py`)
- **Forms** — validation only
- **Tasks** — django-q2 background jobs (`papers/tasks.py`)

### Key Models (papers/models.py)

- **Paper** — UUID primary key. Metadata (DOI, title, abstract, journal, year),
  uploaded PDFs, extracted full text (SHA-256 hash for dedup), AI summaries
  (overview/methods/findings/significance), reading status, priority.
  Has PostgreSQL `SearchVectorField` with `GinIndex` for full-text search.
- **Author** — Unique on (given_name, family_name), supports ORCID.
- **PaperAuthor** — Ordered through-table for Paper↔Author relationship.
- **Tag** — Per-user tags with colour, ManyToMany to Paper.
- **Note** — Per-user notes on papers, optionally tied to a page number.

All user-facing models are scoped to a User via ForeignKey.

### External Integrations

- **Anthropic Claude API** — AI paper summarisation (background task)
- **Crossref API** — Primary metadata source for DOIs (free, no auth needed)
- **OpenAlex API** — Fallback for abstracts and citation counts (free)
- **PyMuPDF** — PDF text extraction

### Configuration

Environment variables via `python-decouple` from `.env`:
`SECRET_KEY`, `DEBUG`, database credentials, `CLAUDE_API_KEY`, `CROSSREF_EMAIL`

PostgreSQL on localhost:5432 is required — app uses PostgreSQL-specific features
(`SearchVectorField`, `GinIndex`, `pg_trgm`).

## Development Principles

### KISS — Keep It Simple
- Write the simplest code that works
- Prefer clarity over cleverness
- If it needs a comment to explain, simplify it instead

### YAGNI — You Aren't Gonna Need It
- Only build what is explicitly requested
- No "just in case" functionality
- MVP first, iterate based on real feedback

### SOLID
- Single responsibility: one class/function does one thing
- Views depend on services, not API clients directly
- Small, focused functions over large complex ones

## British English

Always use British English spellings:
- summarise, analyse, organise, recognise
- colour, behaviour, centre, catalogue
- modelling, labelling

## Build Phases

**Current phase: Phase 1 MVP**
1. DOI import via Crossref
2. PDF upload and text extraction
3. AI summarisation via Claude API
4. Full-text search
5. Citation export

Do not build Phase 2 features (OCR, citation networks, collaboration,
browser extension) until Phase 1 is complete and in users' hands.