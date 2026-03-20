import logging

from .services import SummarisationService

logger = logging.getLogger(__name__)


def summarise_paper_task(paper_id):
    """Background task wrapper for AI summarisation."""
    try:
        SummarisationService.summarise_paper(paper_id)
    except Exception:
        logger.exception('Summarisation failed for paper %s', paper_id)
        raise
