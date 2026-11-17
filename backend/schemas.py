"""Schemas Pydantic para validação de entrada/saída da API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    nome: str
    papel: str


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)
    papel: str = Field(default="educador", max_length=40)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    papel: str
    ativo: bool


class TurmaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    curso: str
    turno: str
    ativa: bool


class AlunoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matricula: str
    nome: str
    email: str | None
    turma_id: int
    ativo: bool
    faltas_consecutivas: int


class ComputadorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    lab: str
    turma_id: int
    disponivel: bool


class ChamadaItemIn(BaseModel):
    aluno_id: int
    presente: bool
    computador_id: int | None = None
    observacao: str | None = Field(default=None, max_length=500)


class ChamadaDiariaIn(BaseModel):
    turma_id: int
    data: date | None = None
    registros: list[ChamadaItemIn] = Field(min_length=1)


class FrequenciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    computador_id: int | None
    data: date
    presente: bool
    observacao: str | None
    registrado_em: datetime | None = None


class AlertaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    tipo: str
    mensagem: str
    faltas_consecutivas: int
    resolvido: bool
    criado_em: datetime | None = None
    aluno: AlunoOut | None = None


class AlocacaoResultado(BaseModel):
    aluno_id: int
    presente: bool
    computador_id: int | None = None
    status: str
    detalhe: str | None = None


class ChamadaDiariaOut(BaseModel):
    data: date
    turma_id: int
    resultados: list[AlocacaoResultado]
    alertas_gerados: int = 0
