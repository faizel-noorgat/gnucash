"""Management command to apply immutability triggers to the database.

This command reads the SQL file from triggers/immutability.sql and executes
it against the database. It should be run after migrations are applied.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    """Apply immutability triggers to the database."""

    help = "Apply immutability triggers for Document Intelligence tables"

    def handle(self, *args, **options):
        # Find the SQL file
        trigger_file = (
            Path(__file__).parent.parent.parent.parent.parent
            / "triggers"
            / "immutability.sql"
        )

        if not trigger_file.exists():
            self.stderr.write(self.style.ERROR(f"Trigger file not found: {trigger_file}"))
            return

        # Read SQL
        sql = trigger_file.read_text()

        # Execute SQL
        self.stdout.write("Applying immutability triggers...")
        with connection.cursor() as cursor:
            cursor.execute(sql)

        self.stdout.write(self.style.SUCCESS("Triggers applied successfully."))
