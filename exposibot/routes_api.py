import json
import os
import re

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required
from pydantic import ValidationError

from exposibot import ai_providers, bible
from exposibot.extensions import db, limiter
from exposibot.models import Sermon
from exposibot.schemas import SermonOutline
from exposibot.security import render_markdown

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_REFERENCE_LENGTH = 500
MAX_NOTES_LENGTH = 50000
MAX_RESEARCH_ITEMS = 50

# Modelo estável atual, mas configurável sem alterar código.
ai_providers.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

SEARCH_QUERIES = {
    "Dados Geográficos": "geography archaeology location {ref} biblical scholar commentary",
    "Perfil Biográfico": "biography characters {ref} redemptive history reformed",
    "Contexto Histórico": "historical context authorship date {ref} conservative commentary carson moo",
    "Contexto Canônico": "biblical theology canon connections {ref} beale vos",
    "Estilo Literário": "literary genre structure chiasm {ref} analysis",
    "Contexto Político": "political context roman empire {ref} historical background",
    "Sócio-Cultural": "social cultural customs {ref} ancient near east background",
    "Contexto Filosófico": "philosophical background heresy {ref} biblical worldview",
    "Teologia Sistemática": "systematic theology doctrines {ref} westminster confession berkhof",
    "Foco Cristocêntrico": "christ centered exposition redemptive historical {ref} chapell biblical theology",
    "Exegese (BHS/UBS5)": "exegesis greek hebrew syntax semantics {ref} technical commentary",
}

PROMPTS = {
    "Dados Geográficos": "Atue como arqueólogo bíblico. Detalhe localização, topografia, clima e relevância interpretativa do lugar, sem transformar geografia em alegoria.",
    "Perfil Biográfico": "Faça o perfil biográfico e o papel dos personagens na história da redenção. Só forneça etimologia quando houver base confiável nas fontes.",
    "Contexto Histórico": "Detalhe autoria, data, destinatários, ocasião e propósito segundo leitura conservadora/reformada, distinguindo consenso, hipótese e controvérsia.",
    "Contexto Canônico": "Situe a passagem no cânon e na história da redenção. Mostre conexões pactuais e referências cruzadas legítimas, sem textos-prova artificiais.",
    "Estilo Literário": "Analise gênero, estrutura, progressão do argumento, repetições e figuras de linguagem. Só proponha quiasmo quando a estrutura realmente o sustentar.",
    "Contexto Político": "Analise estruturas de poder e tensões políticas relevantes para o sentido da passagem, evitando anacronismos.",
    "Sócio-Cultural": "Explique costumes, convenções sociais, práticas e pressupostos culturais necessários para compreender a passagem.",
    "Contexto Filosófico": "Identifique cosmovisões e pressupostos em conflito quando forem demonstráveis no texto e no contexto histórico.",
    "Teologia Sistemática": "Extraia primeiro a teologia do texto e depois mostre sua continuidade com a teologia reformada e os Padrões de Westminster, evitando impor categorias sistemáticas ao texto.",
    "Foco Cristocêntrico": "Identifique o Foco da Condição Decaída e mostre como a passagem se conecta legitimamente a Cristo por promessa-cumprimento, tipologia responsável, aliança, tema bíblico-teológico, necessidade humana ou ação redentora de Deus. Evite moralismo e alegorização.",
    "Exegese (BHS/UBS5)": "Faça exegese técnica do texto original, incluindo morfologia, sintaxe e semântica apenas onde alterem ou aprofundem a interpretação. Não use transliteração por rotina.",
}


def _get_owned_sermon(sermon_id):
    sermon = db.session.get(Sermon, sermon_id)
    if not sermon or sermon.user_id != current_user.id:
        abort(404)
    return sermon


def _research_notes_size(notes):
    if not isinstance(notes, list) or len(notes) > MAX_RESEARCH_ITEMS:
        return None
    total = 0
    for note in notes:
        if not isinstance(note, dict):
            return None
        tipo = note.get("tipo", "")
        markdown = note.get("markdown", "")
        if not isinstance(tipo, str) or not isinstance(markdown, str):
            return None
        total += len(tipo) + len(markdown)
    return total


@bp.route("/analyze", methods=["POST"])
@login_required
@limiter.limit("12 per minute")
def analyze():
    data = request.get_json(silent=True) or {}
    texto = (data.get("texto") or "").strip()
    tipo = data.get("tipo")

    if not texto:
        return jsonify({"error": "A referência bíblica está vazia."}), 400
    if len(texto) > MAX_REFERENCE_LENGTH:
        return jsonify({"error": "A referência ou instrução está longa demais."}), 400
    if tipo not in PROMPTS:
        return jsonify({"error": "Tipo de análise inválido."}), 400

    # O Tavily é contexto de fallback/curadoria. O Gemini também pode usar
    # grounding nativo; a camada de provider decide qual caminho está disponível.
    search_template = SEARCH_QUERIES[tipo]
    search_context = ai_providers.perform_grounded_search(search_template.format(ref=texto))

    instruction = PROMPTS[tipo]
    user_instruction = (
        f"Com base na referência '{texto}' e ESTRITAMENTE no contexto fornecido: {instruction}"
        "\n\nA análise deve servir à preparação expositiva: preserve o sentido do texto, "
        "diferencie dado de inferência e, quando pertinente, indique relevância homilética sem saltar diretamente para a aplicação. "
        "Finalize com '### Referências Consultadas' contendo somente links reais fornecidos no contexto."
    )

    try:
        markdown_text, provider = ai_providers.generate_research(user_instruction, search_context)
    except ai_providers.ProviderUnavailable as exc:
        return jsonify({"error": str(exc)}), 503

    return jsonify(
        {
            "html": str(render_markdown(markdown_text)),
            "markdown": markdown_text,
            "provider": provider,
        }
    )


@bp.route("/suggest_sermon", methods=["POST"])
@login_required
@limiter.limit("6 per minute")
def suggest_sermon():
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    reference = (data.get("reference", "") or "").strip()

    if not isinstance(notes, str):
        return jsonify({"error": "As notas precisam estar em formato de texto."}), 400
    if len(notes) > MAX_NOTES_LENGTH:
        return jsonify({"error": "As notas excedem o limite permitido para uma única geração."}), 413
    if len(reference) > MAX_REFERENCE_LENGTH:
        return jsonify({"error": "A referência bíblica está longa demais."}), 400

    prompt = f"""
Com base EXCLUSIVAMENTE nas notas de pesquisa fornecidas e no texto de {reference}, crie um esboço de sermão expositivo completo.

O esboço deve nascer do fluxo da passagem e obedecer ao protocolo homilético do sistema. Não force três pontos se o texto pedir dois ou quatro. Não invente fatos ou ilustrações históricas.

Retorne APENAS JSON válido com os campos: ict, tese, fcd, proposito_redentivo, proposito_basico, proposito_especifico, intro, topicos, conexao_cristocentrica e conclusao. Cada tópico deve conter titulo, texto_base, explicacao, ilustracao, aplicacao e transicao.
"""

    try:
        json_str, provider = ai_providers.generate_sermon_json(prompt, notes)
    except ai_providers.ProviderUnavailable as exc:
        return jsonify({"error": str(exc)}), 503

    clean = re.sub(r"```json\s*|\s*```", "", json_str).strip()
    try:
        raw_data = json.loads(clean)
        sermon_data = SermonOutline.model_validate(raw_data).model_dump()
    except (json.JSONDecodeError, ValidationError, TypeError):
        return jsonify({"error": "A IA retornou uma estrutura inválida. Tente novamente."}), 502

    sermon_data["_provider"] = provider
    return jsonify(sermon_data)


@bp.route("/sermons/<int:sermon_id>", methods=["PATCH"])
@login_required
@limiter.limit("60 per minute")
def update_sermon(sermon_id):
    sermon = _get_owned_sermon(sermon_id)
    data = request.get_json(silent=True) or {}

    if "reference" in data:
        reference = (data["reference"] or "").strip()
        if len(reference) > MAX_REFERENCE_LENGTH:
            return jsonify({"error": "A referência bíblica está longa demais."}), 400
        sermon.reference = reference

    if "research_notes" in data:
        size = _research_notes_size(data["research_notes"])
        if size is None:
            return jsonify({"error": "Formato inválido para as notas de pesquisa."}), 400
        if size > MAX_NOTES_LENGTH:
            return jsonify({"error": "As notas de pesquisa excedem o limite permitido."}), 413
        sermon.research_notes = data["research_notes"]

    if "outline" in data:
        try:
            validated = SermonOutline.model_validate(data["outline"]).model_dump()
        except ValidationError:
            return jsonify({"error": "Estrutura do sermão inválida."}), 400
        sermon.outline = validated
        sermon.status = "outline" if validated.get("topicos") else sermon.status

    db.session.commit()
    return jsonify({"ok": True, "updated_at": sermon.updated_at.isoformat()})


@bp.route("/passage")
@login_required
@limiter.limit("60 per minute")
def passage():
    ref = request.args.get("ref", "").strip()
    if len(ref) > MAX_REFERENCE_LENGTH:
        return jsonify({"error": "A referência bíblica está longa demais."}), 400
    result = bible.fetch_passage(ref)
    return jsonify(result or {})
