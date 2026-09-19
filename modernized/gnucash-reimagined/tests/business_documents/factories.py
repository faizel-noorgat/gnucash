"""
Test factories for business documents
"""
import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from datetime import date
from apps.business_documents.models import (
    Party, PartyRole, AccountingDocument, DocumentType, DocumentDirection,
    DocumentStatus, DocumentLine, DocumentAttachment, ApprovalWorkflow, ApprovalStep
)


class PartyFactory(DjangoModelFactory):
    """Factory for Party model"""

    class Meta:
        model = Party

    tenant = factory.SubFactory('tests.business_documents.factories.TenantFactory')
    name = factory.Sequence(lambda n: f'Party {n}')
    display_name = factory.LazyAttribute(lambda obj: obj.name)
    roles = factory.LazyFunction(lambda: [PartyRole.CUSTOMER])
    email = factory.LazyAttribute(lambda obj: f'{obj.name.lower().replace(" ", ".")}@example.com')
    is_active = True


class AccountingDocumentFactory(DjangoModelFactory):
    """Factory for AccountingDocument model"""

    class Meta:
        model = AccountingDocument

    tenant = factory.SubFactory('tests.business_documents.factories.TenantFactory')
    legal_entity = factory.SubFactory('tests.business_documents.factories.LegalEntityFactory')
    document_number = factory.Sequence(lambda n: f'INV-{n:06d}')
    document_type = DocumentType.INVOICE
    direction = DocumentDirection.SALES
    party = factory.SubFactory(PartyFactory)
    document_date = factory.LazyFunction(date.today)
    status = DocumentStatus.DRAFT
    currency = factory.SubFactory('tests.business_documents.factories.CurrencyFactory')


class DocumentLineFactory(DjangoModelFactory):
    """Factory for DocumentLine model"""

    class Meta:
        model = DocumentLine

    document = factory.SubFactory(AccountingDocumentFactory)
    line_number = factory.Sequence(lambda n: n + 1)
    description = factory.Sequence(lambda n: f'Line item {n}')
    quantity = Decimal('1.0000')
    unit_price = Decimal('100.0000')
    account = factory.SubFactory('tests.business_documents.factories.AccountFactory')


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

    tenant = factory.SubFactory('tests.business_documents.factories.TenantFactory')
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
    """Placeholder factory for the identity Tenant model.

    `Tenant.slug` is a unique, non-null SlugField with no default, so a factory
    that omits it gives every tenant slug='' and the second one fails on
    tenants_slug_key. The goldens' TenantFactory sets it; this one did not.
    """

    class Meta:
        model = 'identity.Tenant'

    name = factory.Sequence(lambda n: f'Tenant {n}')
    slug = factory.Sequence(lambda n: f'tenant-{n}')


class LegalEntityFactory(DjangoModelFactory):
    """Placeholder factory for the identity LegalEntity model."""

    class Meta:
        model = 'identity.LegalEntity'

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f'Entity {n}')


class CurrencyFactory(DjangoModelFactory):
    """Placeholder factory for the accounting Currency model.

    The unified Commodity/Currency model uses GnuCash's field names -
    `mnemonic` and `fullname`. The legacy round-one service used `code` and
    `name`, and those are not model fields, so every construction raised
    TypeError: Currency() got unexpected keyword arguments: 'code', 'name'.
    """

    class Meta:
        model = 'accounting.Currency'

    namespace = 'CURRENCY'
    mnemonic = factory.Sequence(lambda n: f'CUR{n}')
    fullname = factory.LazyAttribute(lambda obj: f'Currency {obj.mnemonic}')
    fraction = 100
    tenant = factory.SubFactory(TenantFactory)


class AccountFactory(DjangoModelFactory):
    """Placeholder factory for the accounting Account model.

    Account requires a non-null `commodity` and `legal_entity`; the migrated
    factory supplied neither. Both are built from the *same* tenant as the
    account, so tenant-scoped rows stay consistent.
    """

    class Meta:
        model = 'accounting.Account'

    tenant = factory.SubFactory(TenantFactory)
    legal_entity = factory.LazyAttribute(
        lambda obj: LegalEntityFactory(tenant=obj.tenant)
    )
    commodity = factory.LazyAttribute(
        lambda obj: CurrencyFactory(tenant=obj.tenant)
    )
    name = factory.Sequence(lambda n: f'Account {n}')
    account_type = 'INCOME'
