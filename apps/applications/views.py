from django.shortcuts import render, get_object_or_404

from apps.app_catalog.models import Application


def app_list(request):
    """List of all applications with search and filter."""
    applications = Application.objects.select_related(
        'ownership', 'technology'
    ).prefetch_related('environments').all()

    # Optional filtering
    app_type = request.GET.get('type')
    criticality = request.GET.get('criticality')
    status = request.GET.get('status')
    domain = request.GET.get('domain')
    search = request.GET.get('q', '').strip()

    if app_type:
        applications = applications.filter(type=app_type)
    if criticality:
        applications = applications.filter(criticality=criticality)
    if status:
        applications = applications.filter(lifecycle_status=status)
    if domain:
        applications = applications.filter(domain=domain)
    if search:
        applications = applications.filter(name__icontains=search)

    # Get unique domains for filter dropdown
    domains = (
        Application.objects.values_list('domain', flat=True)
        .distinct()
        .order_by('domain')
    )

    context = {
        'applications': applications,
        'domains': domains,
        'current_type': app_type or '',
        'current_criticality': criticality or '',
        'current_status': status or '',
        'current_domain': domain or '',
        'current_search': search,
        'total_count': applications.count(),
    }

    return render(request, 'applications/app_list.html', context)


def app_detail(request, pk):
    """Detail view for a single application."""
    app = get_object_or_404(
        Application.objects.select_related('ownership', 'technology')
        .prefetch_related('environments', 'integrations_as_source', 'integrations_as_target'),
        pk=pk,
    )

    context = {
        'app': app,
    }

    return render(request, 'applications/app_detail.html', context)
