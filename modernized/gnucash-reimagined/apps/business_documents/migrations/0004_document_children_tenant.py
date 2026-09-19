"""Give document lines and attachments their own ``tenant_id``.

Both reached a tenant only through ``AccountingDocument``, so neither was
policed: an unfiltered queryset or a raw ``SELECT`` against
``business_documents_document_line`` returned every tenant's invoice and bill
lines. Lines carry the financial payload, so they get a materialised column
rather than an ``EXISTS`` against the parent; attachments are queried directly
to list a document's files, so they get the same treatment.

Consistency with the parent is enforced by the composite foreign key added in
``rls/0003``, which makes ``line.tenant_id`` disagreeing with
``line.document.tenant_id`` unrepresentable rather than merely discouraged.

Unlike ``accounting_journalline`` these tables have no row trigger, so the
backfill is an ordinary ``UPDATE``. It is still written to touch only rows that
are actually NULL, so re-running against a partially-populated table cannot
rewrite a tenancy that is already correct.
"""

from django.db import migrations, models
import django.db.models.deletion


BACKFILL_LINES = """
UPDATE business_documents_document_line AS line
SET tenant_id = document.tenant_id
FROM business_documents_accounting_document AS document
WHERE document.guid = line.document_id
  AND line.tenant_id IS NULL;
"""

BACKFILL_ATTACHMENTS = """
UPDATE business_documents_document_attachment AS attachment
SET tenant_id = document.tenant_id
FROM business_documents_accounting_document AS document
WHERE document.guid = attachment.document_id
  AND attachment.tenant_id IS NULL;
"""


def _tenant_field(null=False):
    return models.ForeignKey(
        db_index=True,
        on_delete=django.db.models.deletion.CASCADE,
        related_name="%(class)s_set",
        to="identity.tenant",
        null=null,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("business_documents", "0003_documentline_documentline_quantity_positive_and_more"),
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentline",
            name="tenant",
            field=_tenant_field(null=True),
            preserve_default=False,
        ),
        migrations.RunSQL(sql=BACKFILL_LINES, reverse_sql=migrations.RunSQL.noop),
        migrations.AlterField(
            model_name="documentline",
            name="tenant",
            field=_tenant_field(),
        ),
        migrations.AddField(
            model_name="documentattachment",
            name="tenant",
            field=_tenant_field(null=True),
            preserve_default=False,
        ),
        migrations.RunSQL(sql=BACKFILL_ATTACHMENTS, reverse_sql=migrations.RunSQL.noop),
        migrations.AlterField(
            model_name="documentattachment",
            name="tenant",
            field=_tenant_field(),
        ),
    ]
