"""
Management command for seeding data from a JSON file into the database via Django ORM.

Validation:
    - Required fields: checks for presence, None, empty string, "null" literal
    - Allowed values (enum): checks against a list of permitted values
    - Data type: inferred from Django model (CharField -> str, IntegerField -> int, ...)

Usage:
    python manage.py seed_catalog
    python manage.py seed_catalog --file path/to/custom.json -> custom json file
    python manage.py seed_catalog --flush -> flushes data before seeding
    python manage.py seed_catalog --dry-run -> dry run, only validation, no data seeding
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.app_catalog.models import (   
    Application,
    Environment,
    Integration,
    Ownership,
    Technology,
)


# ============================================================
# Default path to JSON fixture
# ============================================================

DEFAULT_FIXTURE = Path(__file__).resolve().parent.parent.parent / "resources" / "applications.json"


# ============================================================
# Table configuration and validation rules
#
# Field format:
#   "json_field": {
#       "to":       "model_field_name",         # mapping to Django model field
#       "required": True / False,               # required field
#       "enum":     ["val1", "val2", ...],      # allowed values (optional)
#   }
#
# If "required": True, the validator checks:
#   - field exists in the record
#   - value is not None
#   - value is not an empty string ""
#   - value is not the literal string "null"
# ============================================================

TABLE_CONFIG = [
    (
        "applications",
        Application,
        {
            "id":                        {"to": "id",                        "required": True},
            "name":                      {"to": "name",                      "required": True},
            "type":                      {"to": "type",                      "required": True,  "enum": ["core", "satellite"]},
            "domain":                    {"to": "domain",                    "required": True},
            "description":               {"to": "description",               "required": False},
            "criticality":               {"to": "criticality",               "required": True,  "enum": ["mission_critical", "business_critical", "business_operational", "administrative"]},
            "lifecycle_status":          {"to": "lifecycle_status",          "required": True,  "enum": ["development", "production", "phase_out", "decommissioned"]},
            "go_live_date":              {"to": "go_live_date",              "required": False},
            "planned_decommission_date": {"to": "planned_decommission_date", "required": False},
            "capabilities":              {"to": "capabilities",              "required": False},
            "tech_debt":                 {"to": "tech_debt",                 "required": False},
            "tech_debt_severity":        {"to": "tech_debt_severity",        "required": False, "enum": ["critical", "high", "medium", "low"]},
        },
    ),
    (
        "ownerships",
        Ownership,
        {
            "id":                        {"to": "id",                        "required": True},
            "application_id":            {"to": "application_id",            "required": True},
            "business_owner":            {"to": "business_owner",            "required": True},
            "business_owner_department": {"to": "business_owner_department", "required": True},
            "it_owner":                  {"to": "it_owner",                  "required": True},
            "it_owner_team":             {"to": "it_owner_team",             "required": True},
            "vendor":                    {"to": "vendor",                    "required": False},
        },
    ),
    (
        "environments",
        Environment,
        {
            "id":             {"to": "id",             "required": True},
            "application_id": {"to": "application_id", "required": True},
            "env_type":       {"to": "env_type",       "required": True,  "enum": ["DEV", "UAT", "PROD"]},
            "region":         {"to": "region",         "required": True},
            "hosting":        {"to": "hosting",        "required": True,  "enum": ["on-prem", "cloud"]},
            "datacenter":     {"to": "datacenter",     "required": False},
        },
    ),
    (
        "technologies",
        Technology,
        {
            "id":             {"to": "id",             "required": True},
            "application_id": {"to": "application_id", "required": True},
            "stack":          {"to": "stack",           "required": True},
            "database":       {"to": "database",        "required": False},
            "runtime":        {"to": "runtime",         "required": False},
            "vendor_product": {"to": "vendor_product",  "required": False},
        },
    ),
    (
        "integrations",
        Integration,
        {
            "id":                     {"to": "id",                     "required": True},
            "source_application_id":  {"to": "source_application_id",  "required": True},
            "target_application_id":  {"to": "target_application_id",  "required": False},
            "integration_type":       {"to": "integration_type",       "required": True,  "enum": ["API", "message", "file"]},
            "protocol":               {"to": "protocol",               "required": True},
            "direction":              {"to": "direction",              "required": True,  "enum": ["source_to_target", "target_to_source", "bidirectional"]},
            "avg_daily_volume":       {"to": "avg_daily_volume",       "required": False},
            "data_sensitivity":       {"to": "data_sensitivity",       "required": True,  "enum": ["public", "internal", "confidential", "strictly_confidential"]},
            "description":            {"to": "description",            "required": False},
            "external_target":        {"to": "external_target",        "required": False},
        },
    ),
]


# ============================================================
# Values considered empty for required fields
# ============================================================

EMPTY_VALUES = {None, "", "null", "NULL", "None", "none"}


class Command(BaseCommand):
    help = "Seeds the database with data from a JSON file (application catalog)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=str(DEFAULT_FIXTURE),
            help=f"Path to JSON file (default: {DEFAULT_FIXTURE})",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing data before import",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validation only - no data will be written to the database",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        flush = options["flush"]
        dry_run = options["dry_run"]

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"\n  Source: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # --- Validation ---
        errors = self._validate(data)

        if errors:
            self.stderr.write(self.style.ERROR(f"\n  VALIDATION FAILED: {len(errors)} error(s)\n"))
            for err in errors:
                self.stderr.write(self.style.ERROR(f"  {err}"))
            raise CommandError("Data is not valid, import aborted.")

        self.stdout.write(self.style.SUCCESS("  Validation OK"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n  --dry-run: no data was written\n"))
            return

        # --- Import ---
        try:
            with transaction.atomic():
                if flush:
                    self._flush()
                counts = self._import(data)

        except Exception as e:
            raise CommandError(f"Import failed: {e}")

        # --- Summary ---
        self.stdout.write(f"\n  {'─' * 40}")
        self.stdout.write(f"  {'Table':<20} {'Records':>8}")
        self.stdout.write(f"  {'─' * 40}")
        for table_name, count in counts.items():
            self.stdout.write(f"  {table_name:<20} {count:>8}")
        self.stdout.write(f"  {'─' * 40}")
        total = sum(counts.values())
        self.stdout.write(self.style.SUCCESS(f"\n  Import completed: {total} records\n"))

    # ────────────────────────────────────────
    # Validation
    # ────────────────────────────────────────

    def _validate(self, data: dict) -> list[str]:
        """Validates JSON data against TABLE_CONFIG rules and Django models."""
        errors = []

        for json_key, model, field_config in TABLE_CONFIG:
            records = data.get(json_key, [])

            if not records:
                errors.append(f"[{json_key}] No records found")
                continue

            model_fields = {
                f.name: f for f in model._meta.get_fields() if hasattr(f, "column")
            }

            for idx, record in enumerate(records):
                record_id = record.get("id", f"index={idx}")
                ref = f"[{json_key}:{record_id}]"

                for json_field, rules in field_config.items():
                    model_field_name = rules["to"]
                    required = rules.get("required", False)
                    allowed = rules.get("enum")
                    value = record.get(json_field)

                    # 1. Required check - field is missing
                    if required and json_field not in record:
                        errors.append(f"{ref}.{json_field}: required field is missing from record")
                        continue

                    # 2. Required check - empty value
                    if required and value in EMPTY_VALUES:
                        errors.append(
                            f"{ref}.{json_field}: required field contains an empty value "
                            f"({repr(value)})"
                        )
                        continue

                    # 3. Required check - whitespace-only string
                    if required and isinstance(value, str) and not value.strip():
                        errors.append(
                            f"{ref}.{json_field}: required field contains only whitespace"
                        )
                        continue

                    # Optional field with None/missing - skip further checks
                    if value is None or json_field not in record:
                        continue

                    # 4. Enum check
                    if allowed and value not in allowed:
                        errors.append(
                            f"{ref}.{json_field}: value '{value}' "
                            f"is not in allowed values: {allowed}"
                        )

                    # 5. Type check (from Django model)
                    field_obj = model_fields.get(model_field_name)
                    if field_obj:
                        self._check_type(ref, json_field, value, field_obj, errors)

        return errors

    def _check_type(self, ref: str, field_name: str, value, field_obj, errors: list):
        """Checks value type against the Django model field type."""
        from django.db import models as m

        type_checks = {
            m.CharField: str,
            m.TextField: str,
            m.IntegerField: int,
            m.FloatField: (int, float),
            m.BooleanField: bool,
            m.DateField: str,
            m.JSONField: (list, dict),
        }

        for field_class, expected_type in type_checks.items():
            if isinstance(field_obj, field_class):
                if not isinstance(value, expected_type):
                    actual = type(value).__name__
                    expected = (
                        expected_type.__name__
                        if isinstance(expected_type, type)
                        else str(expected_type)
                    )
                    errors.append(
                        f"{ref}.{field_name}: expected type '{expected}', "
                        f"but found '{actual}' (value: {repr(value)[:50]})"
                    )
                break

    # ────────────────────────────────────────
    # Flush
    # ────────────────────────────────────────

    def _flush(self):
        """Deletes data in reverse order (due to FK constraints)."""
        self.stdout.write("  Deleting existing data...")
        for json_key, model, _ in reversed(TABLE_CONFIG):
            count, _ = model.objects.all().delete()
            if count:
                self.stdout.write(f"    {json_key}: deleted {count}")

    # ────────────────────────────────────────
    # Import
    # ────────────────────────────────────────

    def _import(self, data: dict) -> dict:
        """Imports data via ORM. Returns dict {table_name: count}."""
        counts = {}

        for json_key, model, field_config in TABLE_CONFIG:
            records = data.get(json_key, [])
            objects = []

            for record in records:
                kwargs = {}
                for json_field, rules in field_config.items():
                    kwargs[rules["to"]] = record.get(json_field)
                objects.append(model(**kwargs))

            model.objects.bulk_create(objects)
            counts[json_key] = len(objects)
            self.stdout.write(f"  OK  {json_key}: {len(objects)} records")

        return counts