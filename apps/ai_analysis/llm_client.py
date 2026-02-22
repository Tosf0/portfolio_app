"""
LLM Client — abstrakce nad OpenAI a Anthropic API.

Provider se volí přes settings.AI_PROVIDER ("openai" / "anthropic").
API klíče se čtou z settings (naplněné z .env).
"""

import json
import logging

from django.conf import settings

from apps.app_catalog.models import Application, Integration

logger = logging.getLogger(__name__)

# ── Fixed analysis prompt ──

ANALYSIS_PROMPT = (
    "Analyzuj následující bankovní aplikace a jejich integrační toky. "
    "Identifikuj:\n"
    "1. Top 5 aplikací k refaktoringu a proč\n"
    "2. Hlavní rizika portfolia\n"
    "3. Oblasti s největším technologickým dluhem\n"
    "4. Doporučení pro zlepšení\n\n"
    "Odpověz stručně a strukturovaně v češtině. "
    "Používej krátké odrážky, vynech zbytečné úvody a vysvětlování."
)

MAX_TOKENS = 2048
TEMPERATURE = 0.3
STREAMING = True


def _serialize_portfolio_data():
    """Serialize only the essential fields for LLM analysis."""
    apps = Application.objects.select_related('technology').all()

    data = []
    for app in apps:
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
            entry['stack'] = app.technology.stack

        data.append(entry)

    # Simplified integration summary
    integrations = Integration.objects.select_related(
        'source_application', 'target_application'
    ).all()

    intg_data = [
        {
            'source': i.source_application.name,
            'target': (i.target_application.name if i.target_application
                       else i.external_target or 'External'),
            'type': i.get_integration_type_display(),
            'protocol': i.protocol,
        }
        for i in integrations
    ]

    return json.dumps(
        {'applications': data, 'integrations': intg_data},
        ensure_ascii=False,
    )


def _build_full_prompt():
    """Build the full prompt with data context."""
    context_data = _serialize_portfolio_data()
    return f"{ANALYSIS_PROMPT}\n\n--- DATA ---\n{context_data}"


def _get_provider_info():
    """Return (provider, model, label) tuple."""
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    if provider == 'anthropic':
        model = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
    else:
        model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
    label = f'{provider.title()} ({model})'
    return provider, model, label


def stream_analyze():
    """
    Generator that yields text chunks from the LLM as they arrive.

    Yields:
        str: text chunks of the response.

    The first yield is a special JSON metadata line: {"provider": "...", "model": "..."}
    """
    provider, model, label = _get_provider_info()
    full_prompt = _build_full_prompt()

    logger.info("Starting streaming AI analysis: provider=%s model=%s", provider, model)

    # Yield metadata as the first chunk
    yield json.dumps({'provider_label': label}) + '\n'

    if provider == 'anthropic':
        yield from _stream_anthropic(full_prompt, model)
    else:
        yield from _stream_openai(full_prompt, model)


def _stream_openai(full_prompt, model):
    """Stream from OpenAI API."""
    from openai import OpenAI

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Please add it to your .env file.")

    client = OpenAI(api_key=api_key)
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert IT portfolio analyst for a bank."},
            {"role": "user", "content": full_prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        stream=STREAMING,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


def _stream_anthropic(full_prompt, model):
    """Stream from Anthropic API."""
    from anthropic import Anthropic

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Please add it to your .env file.")

    client = Anthropic(api_key=api_key)

    with client.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "user", "content": full_prompt},
        ],
        system="You are an expert IT portfolio analyst for a bank.",
        temperature=TEMPERATURE,
    ) as stream:
        for text in stream.text_stream:
            yield text


def analyze():
    """
    Non-streaming fallback. Returns (result_text, provider_label).
    """
    provider, model, label = _get_provider_info()
    full_prompt = _build_full_prompt()

    logger.info("Starting AI analysis: provider=%s model=%s", provider, model)

    if provider == 'anthropic':
        chunks = list(_stream_anthropic(full_prompt, model))
    else:
        chunks = list(_stream_openai(full_prompt, model))

    return ''.join(chunks), label
