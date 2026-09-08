from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SermonPoint(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    titulo: str = Field(default="", max_length=500)
    texto_base: str = Field(default="", max_length=500)
    explicacao: str = Field(default="", max_length=12000)
    ilustracao: str = Field(default="", max_length=8000)
    aplicacao: str = Field(default="", max_length=8000)
    transicao: str = Field(default="", max_length=2000)


class SermonOutline(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    ict: str = Field(default="", max_length=2000)
    tese: str = Field(default="", max_length=2000)
    fcd: str = Field(default="", max_length=4000)
    proposito_redentivo: str = Field(default="", max_length=4000)
    proposito_basico: Literal[
        "Evangelístico",
        "Devocional",
        "Missionário/Consagratório",
        "Pastoral/Consolador",
        "Ético",
        "Doutrinário",
    ] | str = ""
    proposito_especifico: str = Field(default="", max_length=4000)
    intro: str = Field(default="", max_length=12000)
    topicos: list[SermonPoint] = Field(default_factory=list, max_length=8)
    conexao_cristocentrica: str = Field(default="", max_length=8000)
    conclusao: str = Field(default="", max_length=12000)
