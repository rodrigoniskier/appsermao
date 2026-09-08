"""Orquestração de IA com busca única por caminho de execução.

Gemini usa grounding nativo do Google Search. Tavily só é consultado quando a
pesquisa precisa cair para Groq, evitando duas buscas externas para a mesma
análise em condições normais.
"""

from exposibot import ai_providers


def generate_research(prompt, search_query):
    errors = []

    if ai_providers.gemini_client:
        try:
            user_content = (
                "Use o Google Search grounding para localizar fontes adequadas ao comando. "
                "Liste apenas URLs realmente consultadas.\n\nCOMANDO:\n" + prompt
            )
            return (
                ai_providers._call_gemini(
                    ai_providers.MASTER_SYSTEM_PROMPT,
                    user_content,
                    use_search=True,
                ),
                "gemini",
            )
        except Exception as exc:  # falha de rede/API deve cair para o segundo provedor
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
    return ai_providers.generate_sermon_json(prompt, context)
