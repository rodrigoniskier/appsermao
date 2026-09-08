"""Orquestração moderna de IA com busca única e saída estruturada."""

import logging
import re

from exposibot import ai_providers
from exposibot.schemas import SermonOutline
from exposibot.source_policy import SOURCE_TIERS

logger = logging.getLogger(__name__)

GROQ_CONTEXT_MAX_CHARS = 9000
GROQ_CONTEXT_RETRY_MAX_CHARS = 4500
GROQ_MAX_OUTPUT_TOKENS = 2400
GROQ_RETRY_MAX_OUTPUT_TOKENS = 1800

PTBR_OUTPUT_RULE = """
REGRA DE IDIOMA OBRIGATÓRIA: todo conteúdo textual destinado aos campos do esboço deve ser escrito
em português brasileiro (pt-BR). Mesmo quando as notas ou fontes estiverem em inglês, traduza e
sintetize o conteúdo para pt-BR. Não preencha ICT, tese, FCD, propósitos, introdução, títulos dos
pontos, explicações, ilustrações, aplicações, transições, conexão cristocêntrica ou conclusão em
inglês. Somente nomes próprios, termos técnicos originais indispensáveis e títulos bibliográficos
podem permanecer no idioma original, quando necessário.
""".strip()

GROQ_COMPACT_HOMILETICS_PROMPT = f"""
Você é um assistente de homilética reformada responsável por estruturar um sermão expositivo.
Use somente o texto bíblico indicado e as notas fornecidas. Não invente fatos, fontes, citações,
etimologias ou detalhes históricos. Preserve o sentido histórico-gramatical-literário da passagem.
Identifique ICT, tese, FCD, propósito redentivo, propósito básico e específico. Organize de 2 a 4
pontos conforme o fluxo real do texto. Cada ponto precisa ter texto-base, explicação, ilustração,
aplicação e transição. A conexão com Cristo deve ser exegética e canonicamente legítima, sem
alegorização ou moralismo. A conclusão deve conduzir à fé, arrependimento, consolo, esperança ou
obediência em resposta à graça.

{PTBR_OUTPUT_RULE}

Retorne somente JSON válido no schema solicitado.
""".strip()


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


def _tavily_tiered_context(query):
    client = ai_providers.tavily_client
    if not client:
        return "Aviso: pesquisa Tavily indisponível; responda apenas com o que estiver seguro no contexto."

    results = []
    seen_urls = set()
    for tier_name, domains in SOURCE_TIERS.items():
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_domains=domains,
            include_answer=False,
            include_raw_content=False,
        )
        for item in response.get("results", []):
            url = item.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(
                {
                    "tier": tier_name,
                    "title": item.get("title", "Sem título"),
                    "url": url,
                    "content": item.get("content", ""),
                }
            )
        if len(results) >= 5:
            break

    if not results:
        return "Nenhuma fonte adequada foi localizada nas camadas de evidência configuradas."

    lines = ["### CONTEXTO DAS FONTES — ordem de evidência"]
    for item in results[:7]:
        lines.extend(
            [
                f"- Camada: {item['tier']}",
                f"  Título: {item['title']}",
                f"  Link real: {item['url']}",
                f"  Resumo: {item['content']}",
                "",
            ]
        )
    return "\n".join(lines)


def _clip_section(section, budget):
    section = section.strip()
    if len(section) <= budget:
        return section
    if budget <= 0:
        return ""
    if budget < 240:
        return section[:budget]

    marker = "\n… [nota compactada para o fallback] …\n"
    available = max(0, budget - len(marker))
    head_size = int(available * 0.72)
    tail_size = available - head_size
    return section[:head_size].rstrip() + marker + section[-tail_size:].lstrip()


def compact_research_notes(context, max_chars=GROQ_CONTEXT_MAX_CHARS):
    """Compacta notas longas sem eliminar lentes/categorias inteiras."""
    text = re.sub(r"\n{3,}", "\n\n", (context or "").strip())
    if len(text) <= max_chars:
        return text

    sections = [
        item.strip()
        for item in re.split(r"(?=^\[[^\]\n]{1,120}\]\s*$)", text, flags=re.MULTILINE)
        if item.strip()
    ]
    if len(sections) <= 1:
        return _clip_section(text, max_chars)

    separator_cost = 2 * (len(sections) - 1)
    usable = max(0, max_chars - separator_cost)
    base_budget, remainder = divmod(usable, len(sections))
    pieces = []
    for index, section in enumerate(sections):
        budget = base_budget + (1 if index < remainder else 0)
        pieces.append(_clip_section(section, budget))
    return "\n\n".join(pieces)


def generate_research(prompt, search_query):
    errors = []

    if ai_providers.gemini_client:
        try:
            user_content = (
                f"Consulta de apoio: {search_query}\n\n"
                "Use Google Search e priorize nesta ordem: fontes primárias/confessionais e acadêmicas; "
                "instituições reformadas reconhecidas; material pastoral. Não trate fóruns como evidência-base. "
                "Liste somente URLs realmente consultadas. Responda em português brasileiro, preservando no "
                "idioma original apenas nomes próprios, termos técnicos indispensáveis e títulos de fontes.\n\n"
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
        try:
            context = _tavily_tiered_context(search_query)
            user_content = (
                f"CONTEXTO DE DADOS:\n{context}\n\n---\n\nCOMANDO:\n{prompt}\n\n"
                "Responda em português brasileiro."
            )
            return (
                ai_providers._call_groq(ai_providers.MASTER_SYSTEM_PROMPT, user_content),
                "groq",
            )
        except Exception as exc:
            errors.append(f"Groq: {exc}")

    if errors:
        logger.warning("Falha dos provedores na pesquisa: %s", " | ".join(errors))
    raise ai_providers.ProviderUnavailable(
        "Não foi possível concluir a pesquisa com os provedores configurados. Tente novamente em instantes."
    )


def _groq_sermon_completion(prompt, context, *, max_chars, max_tokens):
    compact_context = compact_research_notes(context, max_chars=max_chars)
    user_content = (
        f"CONTEXTO DE DADOS:\n{compact_context}\n\n---\n\nCOMANDO:\n{prompt}\n\n{PTBR_OUTPUT_RULE}"
    )
    schema = SermonOutline.model_json_schema()
    completion = ai_providers.groq_client.chat.completions.create(
        model=ai_providers.GROQ_MODEL,
        messages=[
            {"role": "system", "content": GROQ_COMPACT_HOMILETICS_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sermon_outline",
                "strict": False,
                "schema": schema,
            },
        },
    )
    return completion.choices[0].message.content


def _is_request_too_large(exc):
    message = str(exc).lower()
    return "413" in message or "request too large" in message or "requested" in message and "tpm" in message


def generate_sermon_json(prompt, context):
    """Gera o esboço usando Gemini primeiro e Groq como fallback compacto."""
    errors = []
    schema = SermonOutline.model_json_schema()
    full_user_content = (
        f"CONTEXTO DE DADOS:\n{context}\n\n---\n\nCOMANDO:\n{prompt}\n\n{PTBR_OUTPUT_RULE}"
    )
    gemini_system_prompt = f"{ai_providers.HOMILETICS_SYSTEM_PROMPT}\n\n{PTBR_OUTPUT_RULE}"

    if ai_providers.gemini_client:
        try:
            return (
                _gemini_interaction(
                    prompt=full_user_content,
                    system_instruction=gemini_system_prompt,
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

    if ai_providers.groq_client:
        try:
            return (
                _groq_sermon_completion(
                    prompt,
                    context,
                    max_chars=GROQ_CONTEXT_MAX_CHARS,
                    max_tokens=GROQ_MAX_OUTPUT_TOKENS,
                ),
                "groq",
            )
        except Exception as exc:
            errors.append(f"Groq: {exc}")
            if _is_request_too_large(exc):
                try:
                    return (
                        _groq_sermon_completion(
                            prompt,
                            context,
                            max_chars=GROQ_CONTEXT_RETRY_MAX_CHARS,
                            max_tokens=GROQ_RETRY_MAX_OUTPUT_TOKENS,
                        ),
                        "groq",
                    )
                except Exception as retry_exc:
                    errors.append(f"Groq retry compacto: {retry_exc}")

    if errors:
        logger.warning("Falha dos provedores ao gerar esboço: %s", " | ".join(errors))
    raise ai_providers.ProviderUnavailable(
        "Não foi possível gerar o esboço agora. O provedor principal falhou e o fallback também não conseguiu processar as notas. Tente novamente em instantes."
    )
