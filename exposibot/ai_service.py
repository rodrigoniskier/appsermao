"""Orquestração moderna de IA com busca única e saída estruturada."""

from exposibot import ai_providers
from exposibot.schemas import SermonOutline


def _gemini_interaction(*, prompt, system_instruction, tools=None, response_format=None):
    client = ai_providers.gemini_client
    if not client:
        raise ai_providers.ProviderUnavailable("Gemini não configurado.")

    kwargs = {
        "model": ai_providers.GEMINI_MODEL,
        "input": prompt,
        "system_instruction": system_instruction,
        "generation_config": {"temperature": 0.1},
        "store": False,
    }
    if tools:
        kwargs["tools"] = tools
    if response_format:
        kwargs["response_format"] = response_format

    interaction = client.interactions.create(**kwargs)
    return interaction.output_text


def generate_research(prompt, search_query):
    errors = []

    if ai_providers.gemini_client:
        try:
            user_content = (
                f"Consulta de apoio: {search_query}\n\n"
                "Use Google Search para localizar fontes adequadas. Liste somente URLs realmente consultadas.\n\n"
                f"COMANDO:\n{prompt}"
            )
            return (
                _gemini_interaction(
                    prompt=user_content,
                    system_instruction=ai_providers.MASTER_SYSTEM_PROMPT,
                    tools=[{"type": "google_search"}],
                ),
                "gemini",
            )
        except Exception as exc:
            errors.append(f"Gemini: {exc}")

    if ai_providers.groq_client:
        context = ai_providers.perform_grounded_search(search_query)
        try:
            user_content = f"CONTEXTO DE DADOS:\n{context}\n\n---\n\nCOMANDO:\n{prompt}"
            return (
                ai_providers._call_groq(ai_providers.MASTER_SYSTEM_PROMPT, user_content),
                "groq",
            )
        except Exception as exc:
            errors.append(f"Groq: {exc}")

    raise ai_providers.ProviderUnavailable(
        " | ".join(errors)
        or "Nenhum provedor de IA configurado (defina GEMINI_API_KEY ou GROQ_API_KEY)."
    )


def generate_sermon_json(prompt, context):
    user_content = f"CONTEXTO DE DADOS:\n{context}\n\n---\n\nCOMANDO:\n{prompt}"
    errors = []
    schema = SermonOutline.model_json_schema()

    if ai_providers.groq_client:
        try:
            completion = ai_providers.groq_client.chat.completions.create(
                model=ai_providers.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": ai_providers.HOMILETICS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                max_tokens=4096,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "sermon_outline",
                        "strict": False,
                        "schema": schema,
                    },
                },
            )
            return completion.choices[0].message.content, "groq"
        except Exception as exc:
            errors.append(f"Groq: {exc}")

    if ai_providers.gemini_client:
        try:
            return (
                _gemini_interaction(
                    prompt=user_content,
                    system_instruction=ai_providers.HOMILETICS_SYSTEM_PROMPT,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": schema,
                    },
                ),
                "gemini",
            )
        except Exception as exc:
            errors.append(f"Gemini: {exc}")

    raise ai_providers.ProviderUnavailable(
        " | ".join(errors)
        or "Nenhum provedor de IA configurado (defina GROQ_API_KEY ou GEMINI_API_KEY)."
    )
