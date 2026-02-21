from django.db import models

class Application(models.Model):
    """Hlavní entita – core a satelitní bankovní aplikace."""

    class Type(models.TextChoices):
        CORE = "core", "Core"
        SATELLITE = "satellite", "Satellite"

    class Criticality(models.TextChoices):
        MISSION_CRITICAL = "mission_critical", "Mission Critical"
        BUSINESS_CRITICAL = "business_critical", "Business Critical"
        BUSINESS_OPERATIONAL = "business_operational", "Business Operational"
        ADMINISTRATIVE = "administrative", "Administrative"

    class LifecycleStatus(models.TextChoices):
        DEVELOPMENT = "development", "Development"
        PRODUCTION = "production", "Production"
        PHASE_OUT = "phase_out", "Phase Out"
        DECOMMISSIONED = "decommissioned", "Decommissioned"

    class TechDebtSeverity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=Type.choices)
    domain = models.CharField(max_length=50)
    description = models.TextField(blank=True, default="")
    criticality = models.CharField(max_length=30, choices=Criticality.choices)
    lifecycle_status = models.CharField(max_length=20, choices=LifecycleStatus.choices)
    go_live_date = models.DateField(null=True, blank=True)
    planned_decommission_date = models.DateField(null=True, blank=True)
    capabilities = models.JSONField(default=list, blank=True)
    tech_debt = models.TextField(null=True, blank=True)
    tech_debt_severity = models.CharField(
        max_length=10,
        choices=TechDebtSeverity.choices,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "applications"
        ordering = ["id"]

    def __str__(self):
        return f"{self.id} – {self.name}"


class Ownership(models.Model):
    """Vlastnictví aplikace – business/IT owner a vendor."""

    id = models.CharField(max_length=20, primary_key=True)
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="ownership",
    )
    business_owner = models.CharField(max_length=100)
    business_owner_department = models.CharField(max_length=100)
    it_owner = models.CharField(max_length=100)
    it_owner_team = models.CharField(max_length=100)
    vendor = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "ownerships"
        ordering = ["id"]

    def __str__(self):
        return f"{self.id} – {self.application_id}"


class Environment(models.Model):
    """Prostředí aplikace – DEV/UAT/PROD."""

    class EnvType(models.TextChoices):
        DEV = "DEV", "Development"
        UAT = "UAT", "User Acceptance Testing"
        PROD = "PROD", "Production"

    class Hosting(models.TextChoices):
        ON_PREM = "on-prem", "On-Premise"
        CLOUD = "cloud", "Cloud"

    id = models.CharField(max_length=20, primary_key=True)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="environments",
    )
    env_type = models.CharField(max_length=10, choices=EnvType.choices)
    region = models.CharField(max_length=50)
    hosting = models.CharField(max_length=10, choices=Hosting.choices)
    datacenter = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "environments"
        ordering = ["id"]

    def __str__(self):
        return f"{self.id} – {self.application_id} ({self.env_type})"


class Technology(models.Model):
    """Technologický stack aplikace."""

    id = models.CharField(max_length=20, primary_key=True)
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="technology",
    )
    stack = models.CharField(max_length=100)
    database = models.CharField(max_length=100, null=True, blank=True)
    runtime = models.CharField(max_length=100, null=True, blank=True)
    vendor_product = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "technologies"
        verbose_name_plural = "technologies"
        ordering = ["id"]

    def __str__(self):
        return f"{self.id} – {self.application_id}"


class Integration(models.Model):
    """Integrační toky mezi aplikacemi."""

    class IntegrationType(models.TextChoices):
        API = "API", "API"
        MESSAGE = "message", "Message"
        FILE = "file", "File"

    class Direction(models.TextChoices):
        SOURCE_TO_TARGET = "source_to_target", "Source → Target"
        TARGET_TO_SOURCE = "target_to_source", "Target → Source"
        BIDIRECTIONAL = "bidirectional", "Bidirectional"

    class DataSensitivity(models.TextChoices):
        PUBLIC = "public", "Public"
        INTERNAL = "internal", "Internal"
        CONFIDENTIAL = "confidential", "Confidential"
        STRICTLY_CONFIDENTIAL = "strictly_confidential", "Strictly Confidential"

    id = models.CharField(max_length=20, primary_key=True)
    source_application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="integrations_as_source",
    )
    target_application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        related_name="integrations_as_target",
        null=True,
        blank=True,
    )
    integration_type = models.CharField(max_length=10, choices=IntegrationType.choices)
    protocol = models.CharField(max_length=50)
    direction = models.CharField(max_length=20, choices=Direction.choices)
    avg_daily_volume = models.IntegerField(null=True, blank=True)
    data_sensitivity = models.CharField(max_length=25, choices=DataSensitivity.choices)
    description = models.TextField(blank=True, default="")
    external_target = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "integrations"
        ordering = ["id"]

    def __str__(self):
        target = self.target_application_id or self.external_target or "external"
        return f"{self.id} – {self.source_application_id} → {target}"