import json
import re

import markdown as md
from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required

from exposibot import ai_providers, bible
from exposibot.extensions import db
from exposibot.models import Sermon

bp = Blueprint("api", __name__, url_prefix="/api")

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
    "Foco Cristocêntrico": "christ centered exposition {ref} keller chapell",
    "Exegese (BHS/UBS5)": "exegesis greek hebrew syntax {ref} technical commentary",
}

PROMPTS = {
    "Dados Geográficos": "Atue como Arqueólogo. Detalhe localização, topografia, clima e teologia do lugar.",
    "Perfil Biográfico": "Faça o perfil biográfico, etimologia e papel na redenção dos personagens.",
    "Contexto Histórico": "Detalhe autoria, data, destinatários e propósito (visão conservadora/reformada).",
    "Contexto Canônico": "Situe no cânon, conexões pactuais e referências cruzadas.",
    "Estilo Literário": "Analise gênero, estrutura (quiasmo?), figuras de linguagem e tom.",
    "Contexto Político": "Analise estruturas de poder e tensões políticas da época.",
    "Sócio-Cultural": "Explique costumes, leis sociais e impedimentos de leitura.",
    "Contexto Filosófico": "Identifique cosmovisões em choque e vocabulário filosófico.",
    "Teologia Sistemática": "Categorize sistematicamente e conecte com a Confissão de Fé de Westminster.",
    "Foco Cristocêntrico": "Aplique hermenêutica redentiva-histórica para pregar Cristo.",
    "Exegese (BHS/UBS5)": "Faça exegese técnica (original, morfologia, sintaxe). Use transliteração.",
}


def _get_owned_sermon(sermon_id):
    sermon = db.session.get(Sermon, sermon_id)
    if not sermon or sermon.user_id != current_user.id:
        abort(404)
    return sermon


@bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    data = request.get_json(silent=True) or {}
    texto = (data.get("texto") or "").strip()
    tipo = data.get("tipo")

    if not texto:
        return jsonify({"error": "A referência bíblica está vazia."}), 400

    search_template = SEARCH_QUERIES.get(tipo, "{ref} reformed theology calvinist commentary")
    search_context = ai_providers.perform_grounded_search(search_template.format(ref=texto))

    base_prompt = f"Com base na referência '{texto}' e ESTRITAMENTE no contexto fornecido:"
    instruction = PROMPTS.get(tipo)
    user_instruction = f"{base_prompt} {instruction}" if instruction else f"{base_prompt} Analise teologicamente: {texto}"
    user_instruction += "\n\nIMPORTANTE: Finalize com a lista '### Referências Consultadas' contendo os links reais fornecidos no contexto."

    try:
        markdown_text, provider = ai_providers.generate_research(user_instruction, search_context)
    except ai_providers.ProviderUnavailable as e:
        return jsonify({"error": str(e)}), 503

    return jsonify({
        "html": md.markdown(markdown_text),
        "markdown": markdown_text,
        "provider": provider,
    })


@bp.route("/suggest_sermon", methods=["POST"])
@login_required
def suggest_sermon():
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    reference = data.get("reference", "")

    prompt = f"""
    Com base EXCLUSIVAMENTE nas notas de pesquisa fornecidas e no texto de {reference}, crie um esboço de sermão expositivo completo.

    O sermão deve ser Cristocêntrico e seguir a estrutura homilética padrão.

    Retorne APENAS um JSON com esta estrutura exata:
    {{
        "ict": "Ideia Central do Texto (uma frase)",
        "tese": "A verdade atemporal para hoje",
        "proposito_basico": "Doutrinário, Evangelístico, Consolação, Ético ou Consagração",
        "proposito_especifico": "O que a igreja deve fazer/sentir?",
        "intro": "Texto da introdução (gancho + transição)",
        "topicos": [
            {{"titulo": "Título do Tópico 1", "explicacao": "...", "ilustracao": "...", "aplicacao": "..."}},
            {{"titulo": "Título do Tópico 2", "explicacao": "...", "ilustracao": "...", "aplicacao": "..."}}
        ],
        "conclusao": "Texto da conclusão e apelo"
    }}
    """

    try:
        json_str, provider = ai_providers.generate_sermon_json(prompt, notes)
    except ai_providers.ProviderUnavailable as e:
        return jsonify({"error": str(e)}), 503

    try:
        sermon_data = json.loads(json_str)
    except json.JSONDecodeError:
        clean = re.sub(r"```json\s*|\s*```", "", json_str)
        try:
            sermon_data = json.loads(clean)
        except json.JSONDecodeError:
            return jsonify({"error": "A IA retornou um formato inesperado. Tente novamente."}), 502

    sermon_data["_provider"] = provider
    return jsonify(sermon_data)


@bp.route("/sermons/<int:sermon_id>", methods=["PATCH"])
@login_required
def update_sermon(sermon_id):
    sermon = _get_owned_sermon(sermon_id)
    data = request.get_json(silent=True) or {}

    if "reference" in data:
        sermon.reference = (data["reference"] or "").strip()
    if "research_notes" in data and isinstance(data["research_notes"], list):
        sermon.research_notes = data["research_notes"]
    if "outline" in data and isinstance(data["outline"], dict):
        sermon.outline = data["outline"]
        sermon.status = "outline" if data["outline"].get("topicos") else sermon.status

    db.session.commit()
    return jsonify({"ok": True, "updated_at": sermon.updated_at.isoformat()})


@bp.route("/passage")
@login_required
def passage():
    ref = request.args.get("ref", "")
    result = bible.fetch_passage(ref)
    return jsonify(result or {})
