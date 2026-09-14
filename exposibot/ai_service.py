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

ANALYSIS_PROSE_RULE = """
FORMATO OBRIGATÓRIO PARA A ÁREA "RESULTADO DA ANÁLISE": escreva o conteúdo em prosa contínua,
com frases completas e parágrafos bem desenvolvidos. Títulos e subtítulos em Markdown são permitidos
para organizar a leitura, mas o conteúdo de cada seção deve permanecer em parágrafos corridos.
NUNCA use tabelas Markdown, tabelas HTML, quadros, colunas, matrizes comparativas ou qualquer
representação tabular. NUNCA use listas com marcadores ou listas numeradas no corpo da análise.
Quando precisar comparar autores, hipóteses, termos, posições ou evidências, faça a comparação em
parágrafos explicativos. Na seção "### Referências Consultadas", apresente cada referência como um
parágrafo independente no formato "Título — URL", sem bullets, numeração ou tabela.
""".strip()

SERMON_SYNTHESIS_RULE = """
REGRA DE BASE E INFERÊNCIA HOMILÉTICA:
As notas de pesquisa são o único corpus evidenciário. Não introduza nenhuma premissa factual, lexical,
histórica, arqueológica, canônica, doutrinária ou bibliográfica que não esteja sustentada nelas.

Entretanto, NÃO confunda "usar exclusivamente as notas" com "copiar apenas frases que já estejam prontas".
Você deve realizar a síntese homilética necessária: formular ICT, FCD, provisão redentiva, tese, propósitos,
estrutura e aplicações como inferências logicamente derivadas das notas. Essas inferências não podem depender
de informação externa nem contrariar qualificações, debates ou limites registrados na pesquisa.

A sequência obrigatória de raciocínio é: exegese e fluxo do texto -> ideia exegética (assunto + asserção) ->
contexto canônico/histórico-redentivo -> FCD -> provisão da graça -> caminho legítimo a Cristo -> aplicações
-> proposição e propósitos -> estrutura expositiva -> introdução/transições/conclusão -> auditoria crítica.

No campo ict, deixe reconhecíveis o ASSUNTO e a ASSERÇÃO. No campo proposito_redentivo, expresse a relação
entre a necessidade humana e a provisão da graça. No campo conexao_cristocentrica, explique o caminho canônico
legítimo a Cristo, sem alegoria ou apêndice artificial. Nas aplicações, derive consequências do texto, do FCD
e da graça; considere dever, caráter, objetivos/vocação e discernimento, sem acrescentar novos fatos.

Se uma conexão, ilustração ou detalhe não puder ser sustentado pelas notas, deixe o campo vazio ou seja
explicitamente sóbrio. Nunca invente história, citação, estatística, referência bíblica, significado lexical
ou fato histórico para completar o esboço.
""".strip()

GROQ_COMPACT_HOMILETICS_PROMPT = f"""
Você é um tutor de homilética reformada cristocêntrica. Estruture um sermão expositivo usando as notas
fornecidas como ÚNICO corpus evidenciário. A referência bíblica identifica a passagem, mas não é uma fonte
adicional nesta chamada. Não consulte fontes externas, não recupere o texto bíblico por conta própria e não
complete lacunas com memória ou conhecimento geral.

Use esta sequência: 1) sintetize a exegese e o fluxo do texto; 2) formule a ideia exegética em assunto +
asserção; 3) situe a passagem no contexto canônico/histórico-redentivo somente conforme as notas; 4)
identifique o FCD; 5) identifique a provisão da graça; 6) determine o caminho legítimo a Cristo; 7) derive
aplicações; 8) formule tese e propósitos; 9) organize 2 a 4 movimentos expositivos apenas se o fluxo textual
os sustentar; 10) desenvolva introdução, transições e conclusão; 11) audite eisegese, moralismo, alegoria,
saltos canônicos e fatos não sustentados.

É permitido produzir inferências homiléticas necessárias a partir das notas; não é permitido acrescentar
novas premissas factuais. A aplicação deve nascer do texto, do FCD e da graça e pode considerar dever,
caráter, objetivos/vocação e discernimento. A conexão cristocêntrica deve ser exegética e canonicamente
legítima segundo as notas, nunca uma menção decorativa a Jesus. Se as notas não sustentarem uma ilustração
ou detalhe, deixe o campo vazio em vez de inventar.

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
                "Esta é uma pesquisa teológica autônoma: investigue a pergunta em si e não a converta em esboço, aplicação ou orientação homilética. "
                "Siga a ordem metodológica histórico-gramatical-literária -> canônica/bíblico-teológica -> sistemática somente quando a lente solicitada exigir. "
                "Use Google Search e priorize nesta ordem: texto e fontes primárias/técnicas pertinentes; fontes acadêmicas e confessionais; instituições reformadas reconhecidas; "
                "material pastoral apenas como apoio secundário, nunca como substituto da evidência. Não trate fóruns como evidência-base. "
                "Diferencie fato documentado, interpretação, inferência, hipótese, consenso, controvérsia e síntese teológica. "
                "Liste somente URLs realmente consultadas. Responda em português brasileiro, preservando no "
                "idioma original apenas nomes próprios, termos técnicos indispensáveis e títulos de fontes.\n\n"
                f"{ANALYSIS_PROSE_RULE}\n\n"
                f"COMANDO:\n{prompt}"
            )
            return (
                _gemini_interaction(
                    prompt=user_content,
                    system_instruction=ai_providers.RESEARCH_SYSTEM_PROMPT,
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
                f"CONTEXTO DE DADOS:\n{context}\n\n---\n\n"
                "Esta é pesquisa autônoma. Não gere sermão, FCD, tese, aplicação ou estrutura homilética. "
                "Diferencie evidência, interpretação, inferência, hipótese e síntese.\n\n"
                f"{ANALYSIS_PROSE_RULE}\n\n"
                f"COMANDO:\n{prompt}\n\nResponda em português brasileiro."
            )
            return (
                ai_providers._call_groq(ai_providers.RESEARCH_SYSTEM_PROMPT, user_content),
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
        f"CONTEXTO DE DADOS:\n{compact_context}\n\n---\n\nCOMANDO:\n{prompt}\n\n"
        f"{SERMON_SYNTHESIS_RULE}\n\n{PTBR_OUTPUT_RULE}"
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
        f"CONTEXTO DE DADOS:\n{context}\n\n---\n\nCOMANDO:\n{prompt}\n\n"
        f"{SERMON_SYNTHESIS_RULE}\n\n{PTBR_OUTPUT_RULE}"
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
