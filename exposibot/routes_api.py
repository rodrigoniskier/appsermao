import json
import os
import re

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required
from pydantic import ValidationError

from exposibot import ai_providers, ai_service, bible
from exposibot.extensions import db, limiter
from exposibot.models import Sermon
from exposibot.schemas import SermonOutline
from exposibot.security import render_markdown

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_REFERENCE_LENGTH = 500
MAX_NOTES_LENGTH = 50000
MAX_RESEARCH_ITEMS = 50

ai_providers.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

SEARCH_QUERIES = {
    "Dados Geográficos": "biblical geography archaeology topography climate historical geography {ref} academic commentary",
    "Perfil Biográfico": "biblical character biography identity relationships characterization {ref} academic commentary",
    "Contexto Histórico": "historical context authorship date audience occasion purpose {ref} conservative academic commentary",
    "Contexto Canônico": "canonical context biblical theology intertextuality covenant connections {ref} Beale Vos",
    "Estilo Literário": "literary genre structure rhetoric discourse analysis figures of speech {ref} academic commentary",
    "Contexto Político": "political institutions power conflicts empire historical context {ref} academic commentary",
    "Sócio-Cultural": "social cultural customs institutions honor shame family religion {ref} ancient near east academic",
    "Contexto Filosófico": "philosophical worldview intellectual context religious ideas {ref} biblical academic commentary",
    "Teologia Sistemática": "systematic theology doctrines biblical theology {ref} Westminster Berkhof academic",
    "Foco Cristocêntrico": "christology biblical theology redemptive history promise fulfillment {ref} Beale Carson Chapell",
    "Exegese (BHS/UBS5)": "Hebrew Greek exegesis morphology syntax semantics textual criticism {ref} technical commentary",
}

PROMPTS = {
    "Dados Geográficos": "Produza uma pesquisa geográfica da passagem. Examine localização, topografia, clima, rotas, arqueologia e demais dados espaciais relevantes, distinguindo evidência, reconstrução e hipótese. Explique como esses dados podem iluminar a interpretação sem alegorização.",
    "Perfil Biográfico": "Produza uma pesquisa biográfica e prosopográfica dos personagens envolvidos. Examine identidade, trajetória, relações, caracterização narrativa, papel histórico e dados disponíveis, distinguindo o que o texto afirma do que é reconstrução ou tradição posterior. Só trate etimologia quando houver base confiável.",
    "Contexto Histórico": "Produza uma pesquisa histórica sobre autoria, datação, destinatários, ocasião, ambiente, composição e propósito. Apresente o grau de consenso, as principais hipóteses, os argumentos de cada posição e as controvérsias relevantes dentro de uma leitura conservadora e reformada.",
    "Contexto Canônico": "Produza uma pesquisa de teologia bíblica e contexto canônico. Mapeie a posição da passagem no cânon, relações intertextuais, temas, alianças, promessas, padrões e desenvolvimentos na história da redenção. Diferencie alusões demonstráveis de possíveis ecos e evite textos-prova artificiais.",
    "Estilo Literário": "Produza uma análise literária rigorosa. Identifique gênero, forma, estrutura, unidade, progressão, vozes, repetições, inclusões, paralelismos, ironias, metáforas e demais recursos retóricos. Proponha quiasmo ou outras estruturas apenas quando houver evidência textual suficiente.",
    "Contexto Político": "Produza uma pesquisa sobre o contexto político da passagem. Analise instituições, autoridades, relações de poder, conflitos, impérios, leis e ideologias relevantes, evitando anacronismos e distinguindo dados históricos de inferências.",
    "Sócio-Cultural": "Produza uma pesquisa sociocultural. Explique costumes, instituições, relações familiares, convenções de honra e vergonha, práticas religiosas, econômicas e comunitárias e demais pressupostos culturais necessários à compreensão da passagem. Diferencie evidência, analogia e conjectura.",
    "Contexto Filosófico": "Produza uma pesquisa sobre os pressupostos filosóficos, religiosos e cosmovisionais relevantes. Identifique ideias em conflito, categorias de pensamento e questões de verdade, conhecimento, ética e realidade somente quando forem demonstráveis no texto ou no contexto histórico.",
    "Teologia Sistemática": "Produza uma pesquisa de teologia sistemática derivada primeiro da passagem e depois relacionada às doutrinas reformadas e aos Padrões de Westminster. Compare formulações, categorias, continuidades, tensões e limites sem impor uma doutrina ao texto nem reduzir a análise a uma aplicação pastoral.",
    "Foco Cristocêntrico": "Produza uma pesquisa cristológica e redentivo-histórica. Investigue as formas legítimas pelas quais a passagem se relaciona com Cristo, incluindo promessa e cumprimento, tipologia responsável, aliança, temas bíblico-teológicos e obra redentora de Deus. Distinga afirmação textual, desenvolvimento canônico e inferência teológica; rejeite alegorias e conexões artificiais.",
    "Exegese (BHS/UBS5)": "Produza uma exegese técnica do texto original. Examine crítica textual quando pertinente, morfologia, sintaxe, semântica, pragmática, variantes de tradução e relações discursivas somente na medida em que aprofundem a interpretação. Fundamente cada conclusão, reconheça alternativas relevantes e não use transliteração por rotina.",
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

    instruction = PROMPTS[tipo]
    user_instruction = (
        f"Analise a referência '{texto}': {instruction}"
        "\n\nEsta é uma pesquisa teológica autônoma, destinada a poder ser reutilizada em sermões, aulas, artigos, monografias ou outros trabalhos. "
        "Investigue profundamente a lente solicitada, desenvolvendo evidências, argumentos, qualificações, debates, limites e implicações interpretativas pertinentes. "
        "Não transforme a resposta em esboço de sermão, orientação ao pregador, aconselhamento pastoral ou aplicação congregacional. "
        "Não formule ICT, tese homilética, FCD, propósito, pontos, introdução, ilustrações, transições ou conclusão de sermão, salvo se explicitamente solicitado. "
        "Diferencie dado, interpretação, hipótese, consenso, controvérsia e inferência. "
        "Escreva em português brasileiro, preservando no idioma original apenas nomes próprios, termos técnicos indispensáveis e títulos de fontes. "
        "A resposta exibida em Resultado da Análise deve usar títulos somente quando ajudarem a investigação e desenvolver o conteúdo em parágrafos corridos. "
        "Não use tabelas, quadros, colunas, listas com marcadores ou listas numeradas; comparações devem ser explicadas em prosa. "
        "Finalize com '### Referências Consultadas' contendo somente links reais efetivamente consultados, cada referência em seu próprio parágrafo, sem lista ou tabela."
    )
    search_query = SEARCH_QUERIES[tipo].format(ref=texto)

    try:
        markdown_text, provider = ai_service.generate_research(user_instruction, search_query)
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
Com base EXCLUSIVAMENTE no conteúdo das notas de pesquisa fornecidas, crie um esboço de sermão expositivo completo.

A referência "{reference}" é apenas um identificador da passagem. Ela não é uma fonte adicional nesta chamada. Não consulte fontes externas, não recupere o texto bíblico por conta própria e não use memória, conhecimento geral ou qualquer informação que não esteja contida nas notas de pesquisa.

O esboço deve ser uma síntese fiel e rastreável das notas. Não acrescente novas interpretações, fatos, conexões canônicas, aplicações ou ilustrações. Se determinado campo não puder ser sustentado pelas notas, deixe-o vazio ou escreva uma formulação explicitamente sóbria. Organize de 2 a 4 pontos somente se essa estrutura estiver sustentada pelo material pesquisado.

IDIOMA OBRIGATÓRIO: escreva TODO o conteúdo dos campos em português brasileiro (pt-BR). Apenas nomes próprios, termos originais indispensáveis e títulos bibliográficos podem permanecer no idioma original quando necessário.

Retorne APENAS JSON válido com os campos: ict, tese, fcd, proposito_redentivo, proposito_basico, proposito_especifico, intro, topicos, conexao_cristocentrica e conclusao. Cada tópico deve conter titulo, texto_base, explicacao, ilustracao, aplicacao e transicao.
"""
    try:
        json_str, provider = ai_service.generate_sermon_json(prompt, notes)
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
        if reference != sermon.reference:
            sermon.passage_cache = None
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


@bp.get("/bible/catalog")
@login_required
def bible_catalog():
    return jsonify({"books": bible.catalog(), "version": bible.DEFAULT_VERSION.upper()})


@bp.get("/bible/chapter")
@login_required
@limiter.limit("30 per minute")
def bible_chapter():
    book = request.args.get("book", "").strip().lower()
    try:
        chapter = int(request.args.get("chapter", "0"))
    except ValueError:
        return jsonify({"error": "Capítulo inválido."}), 400

    catalog_entry = next((item for item in bible.catalog() if item["abbr"] == book), None)
    if not catalog_entry or chapter < 1 or chapter > catalog_entry["chapters"]:
        return jsonify({"error": "Livro ou capítulo inválido."}), 400

    data = bible.fetch_chapter(book, chapter)
    if not data:
        return jsonify({"error": "Não foi possível carregar este capítulo agora."}), 503
    return jsonify(data)


@bp.get("/passage")
@login_required
@limiter.limit("60 per minute")
def passage():
    ref = request.args.get("ref", "").strip()
    if not ref or len(ref) > MAX_REFERENCE_LENGTH:
        return jsonify({"error": "Referência bíblica inválida."}), 400

    sermon = None
    sermon_id = request.args.get("sermon_id", "").strip()
    if sermon_id:
        try:
            sermon = _get_owned_sermon(int(sermon_id))
        except ValueError:
            return jsonify({"error": "Sermão inválido."}), 400

        cache = sermon.passage_cache or {}
        if cache.get("reference") == ref and cache.get("text") and cache.get("version"):
            return jsonify(
                {
                    "version": cache["version"],
                    "text": cache["text"],
                    "cached": True,
                }
            )

    result = bible.fetch_passage(ref)
    if not result:
        return jsonify({})

    if sermon is not None:
        sermon.passage_cache = {
            "reference": ref,
            "version": result["version"],
            "text": result["text"],
        }
        db.session.commit()

    return jsonify({**result, "cached": False})
