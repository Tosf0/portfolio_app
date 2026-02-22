import json
import logging
import traceback

from django.conf import settings
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import chat_client
from .models import ChatMessage

logger = logging.getLogger(__name__)


def chat_page(request):
    """Chat page — shows input and previous Q&A."""
    last_message = ChatMessage.get_last()
    context = {
        'provider': getattr(settings, 'AI_PROVIDER', 'openai'),
        'last_message': last_message,
    }
    return render(request, 'ai_chat/chat.html', context)


@require_POST
@csrf_exempt
def chat_stream(request):
    """SSE endpoint — streams chat response and saves Q&A to DB."""
    try:
        body = json.loads(request.body)
        question = body.get('question', '').strip()
    except (json.JSONDecodeError, AttributeError):
        question = ''

    if not question:
        return StreamingHttpResponse(
            iter([f"data: {json.dumps({'error': 'Please enter a question.'})}\n\n"]),
            content_type='text/event-stream',
        )

    def event_stream():
        answer_chunks = []
        try:
            for chunk in chat_client.stream_chat(question):
                answer_chunks.append(chunk)
                yield f"data: {json.dumps({'text': chunk})}\n\n"

            # Save Q&A to DB (skip metadata chunk)
            full_answer = ''.join(answer_chunks[1:])  # first chunk is metadata
            ChatMessage.save_qa(question, full_answer)

            yield f"data: {json.dumps({'done': True})}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            logger.error("Chat stream failed: %s\n%s", e, traceback.format_exc())
            yield f"data: {json.dumps({'error': f'Chat failed: {e}'})}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
