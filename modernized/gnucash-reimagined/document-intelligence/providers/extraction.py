"""Extraction engine interface and factory.

Converts raw OCR output into structured extraction results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from django.conf import settings

from ..models import Document
from .ocr import OCRResult


class ExtractionResult(dict):
    """Structured extraction output."""

    supplier_name: str | None
    customer_name: str | None
    invoice_number: str | None
    invoice_date: str | None
    due_date: str | None
    currency: str | None
    total_amount: str | None
    tax_amount: str | None
    line_items: list[dict]


class ExtractionEngine(Protocol):
    """Extraction engine interface."""

    def extract(self, *, ocr_result: OCRResult, document: Document) -> ExtractionResult: ...


class BaseExtractionEngine(ABC):
    """Base class for extraction engines."""

    @abstractmethod
    def extract(self, *, ocr_result: OCRResult, document: Document) -> ExtractionResult:
        pass


class MockExtractionEngine(BaseExtractionEngine):
    """Mock extraction engine for testing."""

    def extract(self, *, ocr_result: OCRResult, document: Document) -> ExtractionResult:
        return ExtractionResult(
            supplier_name="Mock Supplier",
            customer_name=None,
            invoice_number="INV-001",
            invoice_date="2024-01-15",
            due_date="2024-02-15",
            currency="SGD",
            total_amount="100.00",
            tax_amount="7.00",
            line_items=[
                {"description": "Item 1", "quantity": "1", "unit_price": "100.00"}
            ],
        )


class RuleBasedExtractionEngine(BaseExtractionEngine):
    """Rule-based extraction engine using regex patterns.

    This is a simplified implementation. Production would use more
    sophisticated NLP or call an external extraction service.
    """

    def extract(self, *, ocr_result: OCRResult, document: Document) -> ExtractionResult:
        import re

        text = ocr_result["raw_text"]

        # Simple regex patterns (very naive — real impl would be more robust)
        invoice_match = re.search(r"Invoice[:\s#]+([A-Z0-9-]+)", text, re.IGNORECASE)
        date_match = re.search(r"Date[:\s]+(\d{4}-\d{2}-\d{2})", text)
        amount_match = re.search(r"Total[:\s]+\$?([\d,]+\.\d{2})", text, re.IGNORECASE)

        return ExtractionResult(
            supplier_name=None,  # Would need NER
            customer_name=None,
            invoice_number=invoice_match.group(1) if invoice_match else None,
            invoice_date=date_match.group(1) if date_match else None,
            due_date=None,
            currency="SGD",  # Default
            total_amount=amount_match.group(1) if amount_match else None,
            tax_amount=None,
            line_items=[],
        )


def get_extraction_engine() -> BaseExtractionEngine:
    """Factory function to get the configured extraction engine."""
    engine_name = settings.DOCUMENT_INTELLIGENCE.get("EXTRACTION_ENGINE", "mock")

    if engine_name == "mock":
        return MockExtractionEngine()
    elif engine_name == "rule_based":
        return RuleBasedExtractionEngine()
    else:
        raise ValueError(f"Unknown extraction engine: {engine_name}")
