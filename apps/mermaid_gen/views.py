import json
import logging
import traceback

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import mermaid_client

logger = logging.getLogger(__name__)


@require_POST
@csrf_exempt
def generate_mermaid(request, pk):
    """Generate Mermaid diagram for an application."""
    try:
        result = mermaid_client.generate_diagram(pk)
        return JsonResponse(result)
    except Exception as e:
        logger.error("Mermaid generation failed: %s\n%s", e, traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)
