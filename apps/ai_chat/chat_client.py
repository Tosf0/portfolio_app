"""
Chat Client — streaming LLM chat for Q&A about portfolio data.

Reuses AI provider/model settings from settings.py.
Includes previous Q&A as context (1-turn memory).
"""

import json
import logging

from django.conf import settings

from .data_context import get_relevant_context
from .models import ChatMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Jsi odborný analytik IT portfolia banky. "
    "Odpovídej POUZE na základě dat poskytnutých níže. "
    "Pokud informaci v datech nemáš, řekni to. "
    "Odpovídej stručně, strukturovaně a v češtině."
)


def _get_provider_info():
    """Return (provider, model, label)."""
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    if provider == 'anthropic':
        model = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
    else:
        model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
    return provider, model, f'{provider.title()} ({model})'


def _build_messages(question, data_context, previous_qa):
    """Build the message history for the LLM."""
    messages = []

    # Include previous Q&A as context (1-turn memory)
    if previous_qa:
        messages.append({"role": "user", "content": previous_qa.question})
        messages.append({"role": "assistant", "content": previous_qa.answer})

    # Current question with data context
    user_message = (
        f"{question}\n\n"
        f"--- PORTFOLIO DATA ---\n{data_context}"
    )
    messages.append({"role": "user", "content": user_message})

    return messages


def stream_chat(question):
    """
    Generator that streams LLM response chunks for a chat question.

    Yields:
        str: text chunks. First yield is JSON metadata.
    """
    provider, model, label = _get_provider_info()

    # Get relevant data subset
    data_context = get_relevant_context(question)

    # Get previous Q&A for context
    previous_qa = ChatMessage.get_last()

    messages = _build_messages(question, data_context, previous_qa)

    logger.info("Chat stream: provider=%s, question='%s...'", provider, question[:50])

    # Yield metadata
    yield json.dumps({'provider_label': label}) + '\n'

    if provider == 'anthropic':
        yield from _stream_anthropic(messages, model)
    else:
        yield from _stream_openai(messages, model)


def _stream_openai(messages, model):
    """Stream from OpenAI."""
    from openai import OpenAI

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Please add it to your .env file.")

    client = OpenAI(api_key=api_key)
    all_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    stream = client.chat.completions.create(
        model=model,
        messages=all_messages,
        temperature=0.3,
        max_tokens=2048,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


def _stream_anthropic(messages, model):
    """Stream from Anthropic."""
    from anthropic import Anthropic

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Please add it to your .env file.")

    client = Anthropic(api_key=api_key)

    with client.messages.stream(
        model=model,
        max_tokens=2048,
        messages=messages,
        system=SYSTEM_PROMPT,
        temperature=0.3,
    ) as stream:
        for text in stream.text_stream:
            yield text
