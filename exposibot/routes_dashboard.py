from io import BytesIO

from docx import Document
from docx.shared import Pt
from flask import Blueprint, abort, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required

from exposibot.extensions import db
from exposibot.models import Sermon

bp = Blueprint("dashboard", __name__)


def _get_owned_sermon(sermon_id):
    sermon = db.session.get(Sermon, sermon_id)
    if not sermon or sermon.user_id != current_user.id:
        abort(404)
    return sermon


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    sermons = (
        Sermon.query.filter_by(user_id=current_user.id)
        .order_by(Sermon.updated_at.desc())
        .all()
    )
    return render_template("dashboard.html", sermons=sermons)


@bp.route("/sermon/new", methods=["POST"])
@login_required
def new_sermon():
    sermon = Sermon(user_id=current_user.id, research_notes=[], outline={})
    db.session.add(sermon)
    db.session.commit()
    return redirect(url_for("dashboard.workspace", sermon_id=sermon.id))


@bp.route("/sermon/<int:sermon_id>")
@login_required
def workspace(sermon_id):
    sermon = _get_owned_sermon(sermon_id)
    return render_template("workspace.html", sermon=sermon)


@bp.route("/sermon/<int:sermon_id>/delete", methods=["POST"])
@login_required
def delete_sermon(sermon_id):
    sermon = _get_owned_sermon(sermon_id)
    db.session.delete(sermon)
    db.session.commit()
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/sermon/<int:sermon_id>/preview")
@login_required
def preview(sermon_id):
    sermon = _get_owned_sermon(sermon_id)
    outline = sermon.outline or {}
    return render_template(
        "sermon_preview.html",
        sermon=sermon,
        outline=outline,
        topicos=outline.get("topicos", []),
    )


def _build_docx(sermon):
    outline = sermon.outline or {}
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    document.add_heading("Esboço de Pregação Expositiva", 0)
    document.add_paragraph(f"Texto Base: {sermon.reference}")
    document.add_paragraph(f"ICT: {outline.get('ict', '')}")
    document.add_paragraph(f"Tese: {outline.get('tese', '')}")
    document.add_paragraph(
        f"Propósito: {outline.get('proposito_basico', '')} | {outline.get('proposito_especifico', '')}"
    )
    document.add_paragraph("-" * 60)

    document.add_heading("Introdução", level=1)
    document.add_paragraph(outline.get("intro", ""))

    def _bold_label(text):
        document.add_paragraph().add_run(text).bold = True

    for i, topico in enumerate(outline.get("topicos", []), start=1):
        document.add_heading(f"{i}. {topico.get('titulo', '')}", level=2)
        _bold_label("Explicação:")
        document.add_paragraph(topico.get("explicacao", ""))
        if topico.get("ilustracao"):
            _bold_label("Ilustração:")
            p = document.add_paragraph(topico["ilustracao"])
            try:
                p.style = document.styles["Quote"]
            except KeyError:
                pass
        _bold_label("Aplicação:")
        document.add_paragraph(topico.get("aplicacao", ""))

    document.add_heading("Conclusão", level=1)
    document.add_paragraph(outline.get("conclusao", ""))

    buf = BytesIO()
    document.save(buf)
    buf.seek(0)
    return buf


@bp.route("/sermon/<int:sermon_id>/download.docx")
@login_required
def download_docx(sermon_id):
    sermon = _get_owned_sermon(sermon_id)
    buf = _build_docx(sermon)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"sermao_{sermon.id}.docx",
    )


@bp.route("/sermon/<int:sermon_id>/download.md")
@login_required
def download_md(sermon_id):
    sermon = _get_owned_sermon(sermon_id)
    outline = sermon.outline or {}

    lines = [
        f"# {sermon.display_title()}",
        "",
        f"**Texto Base:** {sermon.reference}",
        f"**ICT:** {outline.get('ict', '')}",
        f"**Tese:** {outline.get('tese', '')}",
        f"**Propósito:** {outline.get('proposito_basico', '')} — {outline.get('proposito_especifico', '')}",
        "",
        "## Introdução",
        outline.get("intro", ""),
        "",
        "## Desenvolvimento",
    ]
    for i, topico in enumerate(outline.get("topicos", []), start=1):
        lines.append(f"### {i}. {topico.get('titulo', '')}")
        lines.append(topico.get("explicacao", ""))
        if topico.get("ilustracao"):
            lines.append(f"> 💡 Ilustração: {topico['ilustracao']}")
        lines.append(f"**Aplicação:** {topico.get('aplicacao', '')}")
        lines.append("")
    lines += ["## Conclusão", outline.get("conclusao", "")]

    buf = BytesIO("\n\n".join(lines).encode("utf-8"))
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"sermao_{sermon.id}.md",
        mimetype="text/markdown",
    )
