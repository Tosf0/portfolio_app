"""
Mermaid Client — generates and validates Mermaid flowchart diagrams via LLM.

Two-step process:
1. Generate Mermaid code from app integration data
2. Validate & fix syntax via second LLM call
"""

import json
import logging
import re

from django.conf import settings

from apps.app_catalog.models import Application, Integration

logger = logging.getLogger(__name__)

GENERATE_PROMPT = (
    "Vygeneruj Mermaid flowchart diagram pro aplikaci \"{name}\".\n"
    "Zobraz cílovou aplikaci uprostřed ve zvýrazněném stylu.\n"
    "Vlevo zobraz inbound integrace (šipky směrem k aplikaci).\n"
    "Vpravo zobraz outbound integrace (šipky od aplikace).\n"
    "Použij syntaxi `flowchart LR`.\n"
    "U každé šipky uveď protokol jako label.\n"
    "Vrať POUZE validní Mermaid kód, nic jiného — žádný markdown, žádné vysvětlení."
)

VALIDATE_PROMPT = (
    "Zkontroluj následující Mermaid kód. "
    "Oprav případné syntaktické chyby (chybějící závorky, neplatné znaky v ID, špatné šipky). "
    "Vrať POUZE opravený Mermaid kód, nic jiného — žádný markdown, žádné vysvětlení.\n\n"
)


def _get_provider_info():
    """Return (provider, model) tuple."""
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    if provider == 'anthropic':
        model = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
    else:
        model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
    return provider, model


def _serialize_integrations(app):
    """Serialize app's integrations into a compact context string."""
    # Integrations where this app is the source (outbound)
    outbound = Integration.objects.filter(
        source_application=app
    ).select_related('target_application')

    # Integrations where this app is the target (inbound)
    inbound = Integration.objects.filter(
        target_application=app
    ).select_related('source_application')

    data = {
        'application': app.name,
        'inbound': [
            {
                'from': i.source_application.name,
                'protocol': i.protocol,
                'type': i.get_integration_type_display(),
            }
            for i in inbound
        ],
        'outbound': [
            {
                'to': (i.target_application.name if i.target_application
                       else i.external_target or 'External'),
                'protocol': i.protocol,
                'type': i.get_integration_type_display(),
            }
            for i in outbound
        ],
    }

    return json.dumps(data, ensure_ascii=False)


def _call_llm(prompt, system_msg="You are a Mermaid diagram expert."):
    """Call LLM and return the full response text."""
    provider, model = _get_provider_info()

    if provider == 'anthropic':
        return _call_anthropic(prompt, model, system_msg)
    else:
        return _call_openai(prompt, model, system_msg)


def _call_openai(prompt, model, system_msg):
    """Call OpenAI API."""
    from openai import OpenAI

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def _call_anthropic(prompt, model, system_msg):
    """Call Anthropic API."""
    from anthropic import Anthropic

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set.")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        system=system_msg,
        temperature=0.2,
    )
    return response.content[0].text


def _extract_mermaid_code(text):
    """Extract pure Mermaid code from LLM response (strip markdown fences)."""
    # Remove ```mermaid ... ``` wrapper if present
    match = re.search(r'```(?:mermaid)?\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def generate_diagram(app_id):
    """
    Generate a Mermaid diagram for an application's integration landscape.

    Returns:
        dict: { "mermaid_code": str, "provider": str }
    """
    app = Application.objects.get(pk=app_id)
    integration_context = _serialize_integrations(app)
    provider, model = _get_provider_info()
    provider_label = f"{provider.title()} ({model})"

    # Step 1: Generate Mermaid code
    generate_prompt = (
        GENERATE_PROMPT.format(name=app.name) +
        f"\n\n--- INTEGRATION DATA ---\n{integration_context}"
    )

    logger.info("Mermaid gen step 1: generating for app=%s", app.name)
    raw_code = _call_llm(generate_prompt)
    mermaid_code = _extract_mermaid_code(raw_code)

    # Step 2: Validate & fix
    validate_prompt = VALIDATE_PROMPT + mermaid_code

    logger.info("Mermaid gen step 2: validating syntax")
    validated_code = _call_llm(validate_prompt)
    final_code = _extract_mermaid_code(validated_code)

    logger.info("Mermaid gen complete for app=%s", app.name)

    return {
        'mermaid_code': final_code,
        'provider': provider_label,
    }
