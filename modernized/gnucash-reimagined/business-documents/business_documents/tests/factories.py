"""
Test factories for business documents
"""
import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from datetime import date
from business_documents.models import (
    Party, PartyRole, AccountingDocument, DocumentType, DocumentDirection,
    DocumentStatus, DocumentLine, DocumentAttachment, ApprovalWorkflow, ApprovalStep
)


class PartyFactory(DjangoModelFactory):
    """Factory for Party model"""

    class Meta:
        model = Party

    tenant = factory.SubFactory('business_documents.tests.factories.TenantFactory')
    name = factory.Sequence(lambda n: f'Party {n}')
    display_name = factory.LazyAttribute(lambda obj: obj.name)
    roles = factory.LazyFunction(lambda: [PartyRole.CUSTOMER])
    email = factory.LazyAttribute(lambda obj: f'{obj.name.lower().replace(" ", ".")}@example.com')
    is_active = True


class AccountingDocumentFactory(DjangoModelFactory):
    """Factory for AccountingDocument model"""

    class Meta:
        model = AccountingDocument

    tenant = factory.SubFactory('business_documents.tests.factories.TenantFactory')
    legal_entity = factory.SubFactory('business_documents.tests.factories.LegalEntityFactory')
    document_number = factory.Sequence(lambda n: f'INV-{n:06d}')
    document_type = DocumentType.INVOICE
    direction = DocumentDirection.SALES
    party = factory.SubFactory(PartyFactory)
    document_date = factory.LazyFunction(date.today)
    status = DocumentStatus.DRAFT
    currency = factory.SubFactory('business_documents.tests.factories.CurrencyFactory')


class DocumentLineFactory(DjangoModelFactory):
    """Factory for DocumentLine model"""

    class Meta:
        model = DocumentLine

    document = factory.SubFactory(AccountingDocumentFactory)
    line_number = factory.Sequence(lambda n: n + 1)
    description = factory.Sequence(lambda n: f'Line item {n}')
    quantity = Decimal('1.0000')
    unit_price = Decimal('100.0000')
    account = factory.SubFactory('business_documents.tests.factories.AccountFactory')


class DocumentAttachmentFactory(DjangoModelFactory):
    """Factory for DocumentAttachment model"""

    class Meta:
        model = DocumentAttachment

    document = factory.SubFactory(AccountingDocumentFactory)
    filename = factory.Sequence(lambda n: f'document_{n}.pdf')
    content_type = 'application/pdf'
    size = 1024
    storage_key = factory.Sequence(lambda n: f'tenants/test/documents/{n}/file.pdf')
    content_hash = factory.Faker('sha256')


class ApprovalWorkflowFactory(DjangoModelFactory):
    """Factory for ApprovalWorkflow model"""

    class Meta:
        model = ApprovalWorkflow

    tenant = factory.SubFactory('business_documents.tests.factories.TenantFactory')
    name = factory.Sequence(lambda n: f'Workflow {n}')
    applies_to_document_types = factory.LazyFunction(lambda: [DocumentType.INVOICE])
    is_active = True


class ApprovalStepFactory(DjangoModelFactory):
    """Factory for ApprovalStep model"""

    class Meta:
        model = ApprovalStep

    workflow = factory.SubFactory(ApprovalWorkflowFactory)
    name = factory.Sequence(lambda n: f'Step {n}')
    step_order = factory.Sequence(lambda n: n + 1)


# Placeholder factories for cross-app dependencies
class TenantFactory(DjangoModelFactory):
    """Placeholder factory for Tenant model"""

    class Meta:
        model = 'identity.Tenant'

    name = factory.Sequence(lambda n: f'Tenant {n}')


class LegalEntityFactory(DjangoModelFactory):
    """Placeholder factory for LegalEntity model"""

    class Meta:
        model = 'identity.LegalEntity'

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f'Entity {n}')


class CurrencyFactory(DjangoModelFactory):
    """Placeholder factory for Currency model"""

    class Meta:
        model = 'accounting.Currency'

    code = factory.Sequence(lambda n: f'C{ n}')
    name = factory.Sequence(lambda n: f'Currency {n}')


class AccountFactory(DjangoModelFactory):
    """Placeholder factory for Account model"""

    class Meta:
        model = 'accounting.Account'

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f'Account {n}')
    account_type = 'INCOME'
