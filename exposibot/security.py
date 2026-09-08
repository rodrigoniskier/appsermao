import markdown as md
import nh3
from markupsafe import Markup


ALLOWED_TAGS = {
    "a", "blockquote", "br", "code", "em", "h1", "h2", "h3", "h4",
    "h5", "h6", "hr", "li", "ol", "p", "pre", "strong", "ul",
}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}


def render_markdown(text):
    """Renderiza Markdown e sanitiza o HTML final com uma allowlist explícita."""
    rendered = md.markdown(text or "", extensions=["sane_lists"])
    cleaned = nh3.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        link_rel="noopener noreferrer nofollow",
    )
    return Markup(cleaned)
