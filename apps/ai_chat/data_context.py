"""
Data Context — intelligent subset selection for chat queries.

Parses the user's question, matches against app names, domains, and stacks,
and returns only the relevant data subset for the LLM.
"""

import json
import re

from apps.app_catalog.models import Application, Integration


def _normalize(text):
    """Lowercase and strip diacritics-safe."""
    return text.lower().strip()


def _extract_keywords(question):
    """Extract meaningful keywords from the user's question."""
    stop_words = {
        'a', 'the', 'is', 'are', 'to', 'for', 'of', 'in', 'on', 'and', 'or',
        'jak', 'jake', 'jaké', 'jaký', 'jaká', 'jaky', 'co', 'kde', 'proč', 'proc',
        'kdo', 'který', 'která', 'které', 'ktery', 'ktera', 'ktere',
        'je', 'jsou', 'má', 'mají', 'ma', 'maji', 'se', 'si', 've', 'na',
        'do', 'za', 'od', 'po', 'při', 'pri', 'před', 'pred', 'mezi', 's', 'z', 'o', 'u',
        'mi', 'mě', 'me', 'řekni', 'rekni', 'popiš', 'popis', 'vysvětli', 'vysvetli',
        'ukaž', 'ukaz', 'najdi', 'existuji', 'existují', 'existuje', 'mají', 'maji',
        'kolik', 'jaky', 'jake', 'všechny', 'vsechny', 'celkem', 'dej', 'vypis',
        'aplikace', 'aplikaci', 'aplikací', 'aplikacich', 'app', 'apps', 'application',
        'integrace', 'integraci', 'integracích', 'integracich',
    }
    words = re.findall(r'\w+', _normalize(question))
    return [w for w in words if w not in stop_words and len(w) > 2]


def get_relevant_context(question):
    """
    Build a context string with only the relevant subset of portfolio data.

    Strategy:
    1. Extract keywords from question
    2. Match against app names, domains, tech stacks, owners
    3. If matches found → return those apps + their integrations
    4. If no matches → return a compact summary of all apps
    5. If question is about integrations → always include integration data
    """
    keywords = _extract_keywords(question)
    q_lower = _normalize(question)

    # Detect if the question is about integrations
    integration_keywords = {'integrac', 'integration', 'propoj', 'tok', 'flow', 'api', 'protocol'}
    asks_about_integrations = any(ik in q_lower for ik in integration_keywords)

    apps = Application.objects.select_related('ownership', 'technology').all()

    # Try to find matching apps (only keywords with 4+ chars to avoid false positives)
    strong_keywords = [kw for kw in keywords if len(kw) >= 4]
    matched_apps = []
    for app in apps:
        searchable = _normalize(
            f"{app.name} {app.domain} {app.id} "
            f"{getattr(app.technology, 'stack', '') if hasattr(app, 'technology') and app.technology else ''} "
            f"{app.tech_debt or ''}"
        )
        if any(kw in searchable for kw in strong_keywords):
            matched_apps.append(app)

    # Check for domain/category queries
    if not matched_apps:
        all_domains = set(a.domain for a in apps)
        for domain in all_domains:
            if _normalize(domain) in q_lower or any(kw in _normalize(domain) for kw in strong_keywords):
                matched_apps.extend(a for a in apps if a.domain == domain)

    # If no specific app match → full summary with all integrations
    if not matched_apps:
        return _build_summary(apps, include_integrations=True)

    return _build_detail(matched_apps, include_all_integrations=asks_about_integrations)


def _serialize_app(app):
    """Serialize a single app to a compact dict."""
    entry = {
        'name': app.name,
        'type': app.get_type_display(),
        'domain': app.domain,
        'criticality': app.get_criticality_display(),
        'status': app.get_lifecycle_status_display(),
    }

    if app.tech_debt:
        entry['tech_debt'] = app.tech_debt
        entry['severity'] = app.get_tech_debt_severity_display()

    if hasattr(app, 'technology') and app.technology:
        t = app.technology
        entry['stack'] = t.stack
        if t.database:
            entry['database'] = t.database

    if hasattr(app, 'ownership') and app.ownership:
        entry['business_owner'] = app.ownership.business_owner
        entry['it_owner'] = app.ownership.it_owner

    return entry


def _build_detail(matched_apps, include_all_integrations=False):
    """Build detailed context for matched apps."""
    app_ids = [a.id for a in matched_apps]
    data = [_serialize_app(a) for a in matched_apps]

    # Get integrations — all or just related to matched apps
    if include_all_integrations:
        integrations = Integration.objects.select_related(
            'source_application', 'target_application'
        ).all()
    else:
        integrations = Integration.objects.filter(
            source_application_id__in=app_ids
        ).select_related('source_application', 'target_application') | \
            Integration.objects.filter(
            target_application_id__in=app_ids
        ).select_related('source_application', 'target_application')

    intg_data = [
        {
            'source': i.source_application.name,
            'target': (i.target_application.name if i.target_application
                       else i.external_target or 'External'),
            'type': i.get_integration_type_display(),
            'protocol': i.protocol,
            'direction': i.get_direction_display(),
            'avg_daily_volume': i.avg_daily_volume,
            'data_sensitivity': i.get_data_sensitivity_display(),
        }
        for i in integrations.distinct()
    ]

    return json.dumps(
        {'matched_applications': data, 'related_integrations': intg_data},
        ensure_ascii=False,
    )


def _build_summary(apps, include_integrations=False):
    """Build a compact summary of the entire portfolio."""
    summary = {
        'total_apps': len(apps),
        'domains': {},
        'apps_with_tech_debt': [],
    }

    for app in apps:
        domain = app.domain
        if domain not in summary['domains']:
            summary['domains'][domain] = []
        summary['domains'][domain].append({
            'name': app.name,
            'type': app.get_type_display(),
            'criticality': app.get_criticality_display(),
            'status': app.get_lifecycle_status_display(),
            'stack': getattr(app.technology, 'stack', '-') if hasattr(app, 'technology') and app.technology else '-',
        })

        if app.tech_debt:
            summary['apps_with_tech_debt'].append({
                'name': app.name,
                'severity': app.get_tech_debt_severity_display(),
                'description': app.tech_debt,
            })

    if include_integrations:
        integrations = Integration.objects.select_related(
            'source_application', 'target_application'
        ).all()
        summary['integrations'] = [
            {
                'source': i.source_application.name,
                'target': (i.target_application.name if i.target_application
                           else i.external_target or 'External'),
                'type': i.get_integration_type_display(),
                'protocol': i.protocol,
                'direction': i.get_direction_display(),
                'avg_daily_volume': i.avg_daily_volume,
                'data_sensitivity': i.get_data_sensitivity_display(),
            }
            for i in integrations
        ]

    return json.dumps(summary, ensure_ascii=False)
