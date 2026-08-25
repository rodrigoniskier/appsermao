import json
import re

import markdown as md
from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required
from markupsafe import escape

from exposibot import ai_providers, bible
from exposibot.extensions import db
from exposibot.models import Sermon

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_REFERENCE_LENGTH = 500
MAX_NOTES_LENGTH = 50000

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
    "Foco Cristocêntrico": "christ centered exposition redemptive historical {ref} chapell keller biblical theology",
    "Exegese (BHS/UBS5)": "exegesis greek hebrew syntax semantics {ref} technical commentary",
}

PROMPTS = {
    "Dados Geográficos": "Atue como arqueólogo bíblico. Detalhe localização, topografia, clima e relevância interpretativa do lugar, sem transformar geografia em alegoria.",
    "Perfil Biográfico": "Faça o perfil biográfico e o papel dos personagens na história da redenção. Só forneça etimologia quando houver base confiável nas fontes.",
    "Contexto Histórico": "Detalhe autoria, data, destinatários, ocasião e propósito segundo leitura conservadora/reformada, distinguindo consenso, hipótese e controvérsia.",
    "Contexto Canônico": "Situe a passagem no cânon e na história da redenção. Mostre conexões pactuais e referências cruzadas legítimas, sem textos-prova artificiais.",
    "Estilo Literário": "Analise gênero, estrutura, progressão do argumento, repetições e figuras de linguagem. Só proponha quiasmo quando a estrutura realmente o sustentar.",
    "Contexto Político": "Analise estruturas de poder e tensões políticas relevantes para o sentido da passagem, evitando anacronismos.",
    "Sócio-Cultural": "Explique costumes, convenções sociais, práticas e pressupostos culturais que sejam necessários para compreender a passagem.",
    "Contexto Filosófico": "Identifique cosmovisões e pressupostos em conflito quando forem demonstráveis no texto e no contexto histórico.",
    "Teologia Sistemática": "Extraia primeiro a teologia do texto e depois mostre sua continuidade com a teologia reformada e os Padrões de Westminster, evitando impor categorias sistemáticas ao texto.",
    "Foco Cristocêntrico": "Identifique o Foco da Condição Decaída e mostre como a passagem se conecta legitimamente a Cristo por promessa-cumprimento, tipologia responsável, aliança, tema bíblico-teológico, necessidade humana ou ação redentora de Deus. Evite moralismo, alegorização e a inserção artificial de Jesus no final.",
    "Exegese (BHS/UBS5)": "Faça exegese técnica do texto original, incluindo morfologia, sintaxe e semântica apenas onde alterem ou aprofundem a interpretação. Não use transliteração por rotina; use-a somente quando ajudar o leitor a compreender o argumento.",
}


def _get_owned_sermon(sermon_id):
    sermon = db.session.get(Sermon, sermon_id)
    if not sermon or sermon.user_id != current_user.id:
        abort(404)
    return sermon


def _safe_markdown_html(text):
    """Converte Markdown sem permitir HTML executável vindo do modelo."""
    return md.markdown(str(escape(text or "")))


@bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    data = request.get_json(silent=True) or {}
    texto = (data.get("texto") or "").strip()
    tipo = data.get("tipo")

    if not texto:
        return jsonify({"error": "A referência bíblica está vazia."}), 400
    if len(texto) > MAX_REFERENCE_LENGTH:
        return jsonify({"error": "A referência ou instrução está longa demais."}), 400

    search_template = SEARCH_QUERIES.get(tipo, "{ref} reformed theology calvinist commentary")
    search_context = ai_providers.perform_grounded_search(search_template.format(ref=texto))

    base_prompt = f"Com base na referência '{texto}' e ESTRITAMENTE no contexto fornecido:"
    instruction = PROMPTS.get(tipo)
    user_instruction = f"{base_prompt} {instruction}" if instruction else f"{base_prompt} Analise teologicamente: {texto}"
    user_instruction += (
        "\n\nA análise deve servir à preparação expositiva: preserve o sentido do texto, "
        "diferencie dado de inferência e, quando pertinente, indique a relevância homilética sem saltar diretamente para a aplicação. "
        "Finalize com a lista '### Referências Consultadas' contendo somente os links reais fornecidos no contexto."
    )

    try:
        markdown_text, provider = ai_providers.generate_research(user_instruction, search_context)
    except ai_providers.ProviderUnavailable as e:
        return jsonify({"error": str(e)}), 503

    return jsonify({
        "html": _safe_markdown_html(markdown_text),
        "markdown": markdown_text,
        "provider": provider,
    })


@bp.route("/suggest_sermon", methods=["POST"])
@login_required
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

Retorne APENAS um JSON com esta estrutura exata:
{{
    "ict": "Ideia Central do Texto: uma frase que expresse o que o autor comunicou aos primeiros destinatários",
    "tese": "A mesma verdade, contextualizada em uma frase clara e memorável para os ouvintes atuais",
    "fcd": "Foco da Condição Decaída: pecado, fraqueza, sofrimento, idolatria, medo ou necessidade humana revelada pelo próprio texto",
    "proposito_redentivo": "Como a graça e a ação redentora de Deus respondem à condição caída e conduzem legitimamente a Cristo",
    "proposito_basico": "Evangelístico, Devocional, Missionário/Consagratório, Pastoral/Consolador, Ético ou Doutrinário",
    "proposito_especifico": "Resposta concreta que se espera dos ouvintes à luz do texto e da graça",
    "intro": "Introdução que exponha uma necessidade ou tensão real e conduza naturalmente ao tema e à tese",
    "topicos": [
        {{
            "titulo": "Frase completa que nasce do movimento do texto",
            "texto_base": "Verso(s) ou parte da perícope que sustenta(m) o ponto",
            "explicacao": "Elucidação expositiva: sentido do texto, contexto e, quando útil, dados gramaticais/sintáticos traduzidos para linguagem congregacional",
            "ilustracao": "Ilustração bíblica, histórica real, cotidiana ou amplamente conhecida; se não houver uma ilustração segura, use uma analogia explicitamente apresentada como analogia",
            "aplicacao": "Aplicação derivada do propósito do texto, contemplando quando pertinente o quê, onde, por quê e como; dever, caráter, objetivos e discernimento; crentes e descrentes; sempre fundamentada na graça",
            "transicao": "Frase breve que retoma o ponto e conduz ao próximo movimento do texto"
        }}
    ],
    "conexao_cristocentrica": "Síntese explícita da conexão legítima entre a passagem e Cristo, sem alegorização nem apêndice artificial",
    "conclusao": "Conclusão concisa que retome a tese, conduza à resposta adequada e termine na graça, fé, arrependimento, consolo, esperança e/ou obediência em Cristo conforme o texto"
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
        reference = (data["reference"] or "").strip()
        if len(reference) > MAX_REFERENCE_LENGTH:
            return jsonify({"error": "A referência bíblica está longa demais."}), 400
        sermon.reference = reference
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
    if len(ref) > MAX_REFERENCE_LENGTH:
        return jsonify({"error": "A referência bíblica está longa demais."}), 400
    result = bible.fetch_passage(ref)
    return jsonify(result or {})
