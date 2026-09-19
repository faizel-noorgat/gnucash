"""System checks for Document Intelligence.

Ensures configuration invariants at Django startup (e.g., required env
vars, OCR provider settings).
"""

from __future__ import annotations

import os

from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def check_object_storage_config(app_configs: object, **kwargs: object) -> list:
    """Validate object storage configuration."""
    errors: list = []
    doc_settings = getattr(settings, "DOCUMENT_INTELLIGENCE", {})
    bucket = doc_settings.get("S3_BUCKET") or os.environ.get("DOC_STORAGE_BUCKET")
    if not bucket:
        errors.append(
            Error(
                "Document Intelligence: object storage bucket is not configured.",
                hint=(
                    "Set settings.DOCUMENT_INTELLIGENCE['S3_BUCKET'] or "
                    "environment variable DOC_STORAGE_BUCKET."
                ),
                id="document_intelligence.E001",
            )
        )
    return errors


@register()
def check_ocr_provider_config(app_configs: object, **kwargs: object) -> list:
    """Validate OCR provider configuration (warn-only, since OCR is async)."""
    warnings: list = []
    doc_settings = getattr(settings, "DOCUMENT_INTELLIGENCE", {})
    provider = doc_settings.get("OCR_PROVIDER", "aws_textract")
    if provider == "aws_textract":
        if not (
            os.environ.get("AWS_ACCESS_KEY_ID")
            and os.environ.get("AWS_SECRET_ACCESS_KEY")
        ):
            warnings.append(
                Warning(
                    "Document Intelligence: AWS credentials not set; OCR tasks will fail.",
                    hint="Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY env vars.",
                    id="document_intelligence.W001",
                )
            )
    return warnings


@register()
def check_llm_provider_config(app_configs: object, **kwargs: object) -> list:
    """Validate LLM provider configuration (warn-only, since suggestions are optional)."""
    warnings: list = []
    doc_settings = getattr(settings, "DOCUMENT_INTELLIGENCE", {})
    if doc_settings.get("AI_SUGGESTIONS_ENABLED", True):
        llm_provider = doc_settings.get("LLM_PROVIDER", "openai")
        env_var = (
            "OPENAI_API_KEY" if llm_provider == "openai" else "ANTHROPIC_API_KEY"
        )
        if not os.environ.get(env_var):
            warnings.append(
                Warning(
                    f"Document Intelligence: {env_var} not set; AI suggestions disabled.",
                    hint=f"Set {env_var} or set AI_SUGGESTIONS_ENABLED=False.",
                    id="document_intelligence.W002",
                )
            )
    return warnings
