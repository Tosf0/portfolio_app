import json
import logging
import traceback

from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import llm_client

logger = logging.getLogger(__name__)


def analysis_page(request):
    """AI Analysis page — shows prompt and streaming UI."""
    context = {
        'prompt': llm_client.ANALYSIS_PROMPT,
        'provider': getattr(settings, 'AI_PROVIDER', 'openai'),
    }
    return render(request, 'ai_analysis/analysis.html', context)


@require_POST
@csrf_exempt
def analysis_stream(request):
    """SSE endpoint — streams LLM response chunks."""
    def event_stream():
        try:
            for chunk in llm_client.stream_analyze():
                # SSE format: data: <text>\n\n
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            logger.error("AI stream failed: %s\n%s", e, traceback.format_exc())
            yield f"data: {json.dumps({'error': f'Analysis failed: {e}'})}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
