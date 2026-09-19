"""Matching Celery task — runs the matching pipeline asynchronously."""

from __future__ import annotations

import logging

from celery import shared_task

from ..models import Document, DocumentExtraction

logger = logging.getLogger(__name__)


@shared_task(
    name="document_intelligence.tasks.matching.run_matching_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def run_matching_task(self, document_guid: str, extraction_guid: str) -> dict:
    """Run matching pipeline on an extracted document.

    This is the entry point for async matching after extraction completes.
    """
    from ..services.matching import MatchingService
    # TODO: inject real lookup services from sibling bounded contexts

    try:
        document = Document.objects.get(guid=document_guid)
        extraction = DocumentExtraction.objects.get(guid=extraction_guid)
    except (Document.DoesNotExist, DocumentExtraction.DoesNotExist) as e:
        logger.error("Entity not found: %s", e)
        return {"status": "error", "message": str(e)}

    service = MatchingService()
    try:
        matches = service.run_matching(document, extraction)
        return {
            "status": "success",
            "matches_count": len(matches),
            "match_ids": [str(m.guid) for m in matches],
        }
    except Exception as e:
        logger.exception("Matching task failed for document %s", document_guid)
        raise self.retry(exc=e)
