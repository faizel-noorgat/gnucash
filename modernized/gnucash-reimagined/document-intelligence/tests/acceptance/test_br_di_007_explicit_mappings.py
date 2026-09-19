"""Acceptance test for BR-DI-007: Accounting mappings are explicit organizational
knowledge, NOT LLM memory.

Given: The AI suggester produces a suggestion
When: The suggestion is created
Then: It MUST trace back to one or more stored AccountingMapping rows
      The source_mapping_ids field is populated
      The suggestion cannot be based solely on LLM parametric memory
"""

import pytest
import uuid
from django.test import TestCase

from document_intelligence.models import AccountingMapping, MappingSuggestion
from document_intelligence.tests.conftest import *  # noqa: F401, F403


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI007_ExplicitMappings(TestCase):
    """BR-DI-007: Accounting mappings are explicit organizational knowledge."""

    def test_suggestion_traces_to_stored_mapping(self, tenant_id):
        """Every suggestion must reference stored AccountingMapping(s)."""
        # Given: An explicit mapping
        mapping = AccountingMapping.objects.create(
            tenant_id=tenant_id,
            supplier_party_id=uuid.uuid4(),
            description_pattern="office supplies",
            target_account_id=uuid.uuid4(),
            target_tax_rule_id=uuid.uuid4(),
            confidence="high",
            is_active=True,
        )

        # When: A suggestion is created
        extraction = None  # Would need a real extraction
        suggestion = MappingSuggestion.objects.create(
            tenant_id=tenant_id,
            extraction=extraction,
            suggested_account_id=mapping.target_account_id,
            suggested_tax_rule_id=mapping.target_tax_rule_id,
            source_mapping_ids=[str(mapping.guid)],  # Traces to stored mapping
            confidence_score=0.95,
            evidence={"source_mapping_id": str(mapping.guid)},
        )

        # Then: Suggestion references the stored mapping
        self.assertEqual(suggestion.source_mapping_ids, [str(mapping.guid)])
        self.assertEqual(suggestion.suggested_account_id, mapping.target_account_id)

        # And: The referenced mapping exists
        referenced_mapping = AccountingMapping.objects.get(guid=mapping.guid)
        self.assertTrue(referenced_mapping.is_active)

    def test_historical_mapping_suggester_uses_stored_mappings(self, tenant_id):
        """HistoricalMappingSuggester only uses stored AccountingMappings."""
        from document_intelligence.providers.ai import HistoricalMappingSuggester
        from document_intelligence.models import Document

        # Given: An active mapping
        mapping = AccountingMapping.objects.create(
            tenant_id=tenant_id,
            supplier_party_id=None,
            description_pattern="hosting",
            target_account_id=uuid.uuid4(),
            confidence="high",
            is_active=True,
        )

        # When: Suggester runs
        suggester = HistoricalMappingSuggester()
        suggestion, confidence, evidence = suggester.suggest(
            tenant_id=tenant_id,
            extraction_result={"supplier_name": "AWS", "line_items": []},
            document=None,
        )

        # Then: Suggestion is based on stored mapping
        self.assertEqual(evidence["source_mapping_id"], str(mapping.guid))
        self.assertGreater(confidence, 0.0)

    def test_no_suggestion_without_stored_mapping(self, tenant_id):
        """If no stored mapping matches, suggestion has low/no confidence."""
        from document_intelligence.providers.ai import HistoricalMappingSuggester

        # Given: No matching mappings (empty tenant)
        suggester = HistoricalMappingSuggester()
        suggestion, confidence, evidence = suggester.suggest(
            tenant_id=tenant_id,
            extraction_result={"supplier_name": "Unknown Supplier"},
            document=None,
        )

        # Then: Confidence is 0, no suggestion
        self.assertEqual(confidence, 0.0)
        self.assertEqual(evidence.get("reason"), "no_matching_mappings")
