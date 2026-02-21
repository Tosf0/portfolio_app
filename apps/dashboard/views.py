from django.shortcuts import render
from django.db.models import Count, Case, When, IntegerField

from apps.app_catalog.models import Application, Environment, Integration


def index(request):
    """Dashboard homepage – KPI cards and summary charts."""

    apps = Application.objects.all()
    total_apps = apps.count()

    # Type breakdown
    core_count = apps.filter(type="core").count()
    satellite_count = apps.filter(type="satellite").count()
    core_pct = round(core_count / total_apps * 100) if total_apps else 0
    satellite_pct = 100 - core_pct if total_apps else 0

    # Lifecycle status
    production_count = apps.filter(lifecycle_status="production").count()
    production_pct = round(production_count / total_apps * 100) if total_apps else 0

    # Criticality
    mission_critical_count = apps.filter(criticality="mission_critical").count()
    mission_critical_pct = round(mission_critical_count / total_apps * 100) if total_apps else 0

    # Tech debt
    tech_debt_apps = (
        apps.filter(tech_debt__isnull=False)
        .exclude(tech_debt="")
        .annotate(
            severity_order=Case(
                When(tech_debt_severity="critical", then=0),
                When(tech_debt_severity="high", then=1),
                When(tech_debt_severity="medium", then=2),
                When(tech_debt_severity="low", then=3),
                default=4,
                output_field=IntegerField(),
            )
        )
        .order_by("severity_order")
    )
    tech_debt_count = tech_debt_apps.count()
    tech_debt_critical = tech_debt_apps.filter(tech_debt_severity="critical").count()
    tech_debt_high = tech_debt_apps.filter(tech_debt_severity="high").count()

    # Integrations
    integrations = Integration.objects.all()
    total_integrations = integrations.count()
    api_integrations = integrations.filter(integration_type="API").count()
    msg_integrations = integrations.filter(integration_type="message").count()
    file_integrations = integrations.filter(integration_type="file").count()

    # Criticality bar chart data
    criticality_map = [
        ("Mission Critical", "mission_critical", "red"),
        ("Business Critical", "business_critical", "amber"),
        ("Business Operational", "business_operational", "blue"),
        ("Administrative", "administrative", "purple"),
    ]
    criticality_data = []
    for label, value, color in criticality_map:
        count = apps.filter(criticality=value).count()
        pct = round(count / total_apps * 100) if total_apps else 0
        criticality_data.append({"label": label, "count": count, "pct": pct, "color": color})

    # Lifecycle bar chart data
    lifecycle_map = [
        ("Production", "production", "green"),
        ("Development", "development", "blue"),
        ("Phase Out", "phase_out", "amber"),
        ("Decommissioned", "decommissioned", "red"),
    ]
    lifecycle_data = []
    for label, value, color in lifecycle_map:
        count = apps.filter(lifecycle_status=value).count()
        pct = round(count / total_apps * 100) if total_apps else 0
        lifecycle_data.append({"label": label, "count": count, "pct": pct, "color": color})

    # Domain distribution
    domain_counts = (
        apps.values("domain")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    max_domain_count = domain_counts[0]["count"] if domain_counts else 1
    domain_data = [
        {
            "domain": d["domain"].replace("_", " ").title(),
            "count": d["count"],
            "pct": round(d["count"] / max_domain_count * 100),
        }
        for d in domain_counts
    ]

    # Hosting distribution (from environments — unique apps per hosting type)
    envs = Environment.objects.all()
    total_envs = envs.count()
    cloud_count = envs.filter(hosting="cloud").count()
    onprem_count = envs.filter(hosting="on-prem").count()
    cloud_pct = round(cloud_count / total_envs * 100) if total_envs else 0
    onprem_pct = 100 - cloud_pct if total_envs else 0

    context = {
        "total_apps": total_apps,
        "core_count": core_count,
        "satellite_count": satellite_count,
        "core_pct": core_pct,
        "satellite_pct": satellite_pct,
        "production_count": production_count,
        "production_pct": production_pct,
        "mission_critical_count": mission_critical_count,
        "mission_critical_pct": mission_critical_pct,
        "tech_debt_count": tech_debt_count,
        "tech_debt_critical": tech_debt_critical,
        "tech_debt_high": tech_debt_high,
        "tech_debt_apps": tech_debt_apps,
        "total_integrations": total_integrations,
        "api_integrations": api_integrations,
        "msg_integrations": msg_integrations,
        "file_integrations": file_integrations,
        "criticality_data": criticality_data,
        "lifecycle_data": lifecycle_data,
        "domain_data": domain_data,
        "cloud_count": cloud_count,
        "onprem_count": onprem_count,
        "cloud_pct": cloud_pct,
        "onprem_pct": onprem_pct,
    }

    return render(request, "dashboard/index.html", context)