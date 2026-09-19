"""Give extractions and matches their own ``tenant_id``.

``DocumentExtraction`` and ``DocumentMatch`` reached a tenant only through
``Document``, so both were unpoliced. An extraction holds the structured
result of an OCR/AI pass - supplier, amounts, line items - and a match records
which accounting document a document was tied to; both are a tenant's business
data and both are queried directly rather than always through their parent.

Consistency with the parent is enforced by the composite foreign key added in
``rls/0003``.

``document_extractions`` has no row trigger; its immutability contract
(BR-DI-003 / BR-DI-009) is enforced in ``DocumentExtraction.save()``, which a
migration's ``UPDATE`` does not go through. The backfill is therefore an
ordinary statement, and it touches only rows whose ``tenant_id`` is still NULL
so it cannot rewrite an already-correct tenancy.
"""

from django.db import migrations, models


BACKFILL_EXTRACTIONS = """
UPDATE document_extractions AS extraction
SET tenant_id = document.tenant_id
FROM documents AS document
WHERE document.guid = extraction.document_id
  AND extraction.tenant_id IS NULL;
"""

BACKFILL_MATCHES = """
UPDATE document_matches AS match
SET tenant_id = document.tenant_id
FROM documents AS document
WHERE document.guid = match.document_id
  AND match.tenant_id IS NULL;
"""


def _tenant_field(null=False):
    """A bare ``UUIDField``, matching ``Document.tenant_id``.

    Not a foreign key. ``Document`` keeps its tenant as a plain UUID, so a
    child that demanded a real ``tenants`` row would be stricter than its own
    parent - it would reject extractions for documents the database had
    already accepted. Agreement with the parent is enforced by the composite
    foreign key in ``rls/0003`` instead, which is the invariant that actually
    matters: the child's tenant must equal its parent's, whatever the parent
    holds.
    """
    return models.UUIDField(db_index=True, null=null)


class Migration(migrations.Migration):
    dependencies = [
        ("document_intelligence", "0001_initial"),
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentextraction",
            name="tenant_id",
            field=_tenant_field(null=True),
            preserve_default=False,
        ),
        migrations.RunSQL(sql=BACKFILL_EXTRACTIONS, reverse_sql=migrations.RunSQL.noop),
        migrations.AlterField(
            model_name="documentextraction",
            name="tenant_id",
            field=_tenant_field(),
        ),
        migrations.AddField(
            model_name="documentmatch",
            name="tenant_id",
            field=_tenant_field(null=True),
            preserve_default=False,
        ),
        migrations.RunSQL(sql=BACKFILL_MATCHES, reverse_sql=migrations.RunSQL.noop),
        migrations.AlterField(
            model_name="documentmatch",
            name="tenant_id",
            field=_tenant_field(),
        ),
    ]
