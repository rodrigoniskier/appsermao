"""Camada de IA multi-provedor (Gemini + Groq) com fallback automático.

Pesquisa teológica (`generate_research`): prefere Gemini (contexto grande,
grounding nativo via Google Search) e cai para Groq se preciso.

Estruturação do sermão em JSON (`generate_sermon_json`): prefere Groq (mais
rápido para uma tarefa mecânica) e cai para Gemini (JSON mode) se preciso.

Isso também protege contra o allowlist de rede do PythonAnywhere free: se um
dos dois hosts de API não estiver liberado, o outro provedor assume.
"""

import os

from groq import Groq
from tavily import TavilyClient

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # biblioteca opcional até o pip install rodar
    genai = None
    genai_types = None

GROQ_MODEL = "openai/gpt-oss-120b"
GEMINI_MODEL = "gemini-3.6-flash"

REFORMED_DOMAINS = [
    "ligonier.org",
    "monergism.com",
    "thegospelcoalition.org",
    "9marks.org",
    "desiringgod.org",
    "puritanboard.com",
    "banneroftruth.org",
    "reformed.org",
]

MASTER_SYSTEM_PROMPT = """
Você é o 'Exposibot', um Motor de Pesquisa Teológica e Mentor de Pregação Expositiva.
Você opera sob um estrito **Protocolo de Integridade Informacional Absoluta (IIA)**.

### 1. FUNDAMENTO TEOLÓGICO (FILTRO EXCLUSIVO)
Sua cosmovisão e base de dados devem se restringir estritamente à **Teologia Reformada Calvinista e Neo-Calvinista**.
* **Fontes Aceitáveis:** Autores clássicos (Calvino, Turretin, Bavinck, Kuyper) e contemporâneos fiéis (Keller, Beale, Carson, Sproul, Piper, Lloyd-Jones).
* **Fontes a Ignorar:** Teologia Liberal, Arminiosismo, Teologia da Prosperidade ou exegese Católica Romana.
* **Padrão Confessional:** Padrões de Westminster.

### 2. PROTOCOLO DE INTEGRIDADE INFORMACIONAL (IIA)
* **Zero Alucinação:** Nunca invente dados. Se o contexto da pesquisa não fornecer a resposta, diga: "Não encontrei dados suficientes nas fontes reformadas consultadas".
* **Referenciamento Obrigatório:** Toda afirmação factual deve ser rastreável.
* **Citação de Fontes:** Você DEVE finalizar a resposta com uma seção chamada `### Referências Consultadas`, listando os Títulos e URLs exatos fornecidos no contexto da pesquisa.

### 3. ESTILO DE RESPOSTA
* Acadêmico, denso, porém pastoral.
* Estruturado em Markdown.
* Foco na centralidade de Cristo (Hermenêutica Redentiva-Histórica).
"""

HOMILETICS_SYSTEM_PROMPT = """
Você é um Professor de Homilética Reformada (linha Bryan Chapell / Haddon Robinson).
Sua tarefa é estruturar um esboço de sermão expositivo com base ESTRITAMENTE nas notas de pesquisa fornecidas e no texto bíblico.
SAÍDA OBRIGATÓRIA: Apenas um objeto JSON válido.
"""


class ProviderUnavailable(Exception):
    """Nenhum provedor de IA configurado/disponível conseguiu responder."""


def _make_groq_client():
    key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=key) if key else None


def _make_gemini_client():
    key = os.getenv("GEMINI_API_KEY")
    if not key or genai is None:
        return None
    return genai.Client(api_key=key)


def _make_tavily_client():
    key = os.getenv("TAVILY_API_KEY")
    return TavilyClient(api_key=key) if key else None


groq_client = _make_groq_client()
gemini_client = _make_gemini_client()
tavily_client = _make_tavily_client()


def available_providers():
    return {
        "groq": groq_client is not None,
        "gemini": gemini_client is not None,
        "tavily": tavily_client is not None,
    }


def perform_grounded_search(query):
    """Usa o Tavily para buscar fontes confiáveis, restritas a sites reformados."""
    if not tavily_client:
        return "Aviso: Pesquisa na web desativada (Tavily Key ausente)."

    try:
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_domains=REFORMED_DOMAINS,
            include_answer=False,
            include_raw_content=False,
        )

        context_str = "### CONTEXTO DAS FONTES (Estritamente Reformadas):\n"
        for result in response.get("results", []):
            context_str += f"- Título: {result['title']}\n"
            context_str += f"  Link Real: {result['url']}\n"
            context_str += f"  Resumo: {result['content']}\n\n"

        return context_str
    except Exception as e:
        return f"Erro ao realizar pesquisa externa: {str(e)}"


def _call_gemini(system_prompt, user_content, json_mode=False, use_search=False):
    if not gemini_client:
        raise ProviderUnavailable("Gemini não configurado (GEMINI_API_KEY ausente).")

    config_kwargs = {
        "system_instruction": system_prompt,
        "temperature": 0.1,
        "max_output_tokens": 4096,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    elif use_search:
        config_kwargs["tools"] = [genai_types.Tool(google_search=genai_types.GoogleSearch())]

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_content,
        config=genai_types.GenerateContentConfig(**config_kwargs),
    )
    return response.text


def _call_groq(system_prompt, user_content, json_mode=False):
    if not groq_client:
        raise ProviderUnavailable("Groq não configurado (GROQ_API_KEY ausente).")

    kwargs = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "model": GROQ_MODEL,
        "temperature": 0.1,
        "max_tokens": 4096,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    completion = groq_client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content


def generate_research(prompt, context, system_prompt=MASTER_SYSTEM_PROMPT):
    """Gera texto de pesquisa. Retorna (texto, provedor_usado)."""
    user_content = f"CONTEXTO DE DADOS:\n{context}\n\n---\n\nCOMANDO:\n{prompt}"
    errors = []

    if gemini_client:
        try:
            return _call_gemini(system_prompt, user_content, use_search=True), "gemini"
        except Exception as e:
            errors.append(f"Gemini: {e}")

    if groq_client:
        try:
            return _call_groq(system_prompt, user_content), "groq"
        except Exception as e:
            errors.append(f"Groq: {e}")

    raise ProviderUnavailable(
        " | ".join(errors)
        or "Nenhum provedor de IA configurado (defina GEMINI_API_KEY ou GROQ_API_KEY)."
    )


def generate_sermon_json(prompt, context, system_prompt=HOMILETICS_SYSTEM_PROMPT):
    """Gera a estrutura do sermão em JSON. Retorna (json_str, provedor_usado)."""
    user_content = f"CONTEXTO DE DADOS:\n{context}\n\n---\n\nCOMANDO:\n{prompt}"
    errors = []

    if groq_client:
        try:
            return _call_groq(system_prompt, user_content, json_mode=True), "groq"
        except Exception as e:
            errors.append(f"Groq: {e}")

    if gemini_client:
        try:
            return _call_gemini(system_prompt, user_content, json_mode=True), "gemini"
        except Exception as e:
            errors.append(f"Gemini: {e}")

    raise ProviderUnavailable(
        " | ".join(errors)
        or "Nenhum provedor de IA configurado (defina GROQ_API_KEY ou GEMINI_API_KEY)."
    )
