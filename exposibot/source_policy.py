"""Política de fontes para o fallback de pesquisa via Tavily.

A ordem privilegia material primário/confessional e acadêmico antes de recursos
ministeriais. Fóruns e conteúdo comunitário não são usados como evidência-base.
"""

SOURCE_TIERS = {
    "primary_academic": [
        "opc.org",
        "pcahistory.org",
        "ccel.org",
        "etsjets.org",
        "tyndalebulletin.org",
        "themelios.thegospelcoalition.org",
        "reformed.org",
    ],
    "institutional": [
        "ligonier.org",
        "monergism.com",
        "banneroftruth.org",
    ],
    "pastoral": [
        "thegospelcoalition.org",
        "9marks.org",
        "desiringgod.org",
    ],
}


def ordered_domains():
    return [domain for tier in SOURCE_TIERS.values() for domain in tier]
