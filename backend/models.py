"""Modelos ORM: Alunos, Turmas, Computadores, Frequência e Alertas."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Usuario(Base):
    """Usuário do sistema (educador/admin) para autenticação JWT."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[str] = mapped_column(String(40), default="educador", nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Turma(Base):
    """Turma vinculada a um laboratório/curso."""

    __tablename__ = "turmas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    curso: Mapped[str] = mapped_column(String(120), nullable=False)
    turno: Mapped[str] = mapped_column(String(40), nullable=False)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    alunos: Mapped[list[Aluno]] = relationship("Aluno", back_populates="turma")
    computadores: Mapped[list[Computador]] = relationship(
        "Computador", back_populates="turma"
    )


class Aluno(Base):
    """Aluno matriculado em uma turma."""

    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    matricula: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(180), nullable=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id"), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    faltas_consecutivas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    turma: Mapped[Turma] = relationship("Turma", back_populates="alunos")
    frequencias: Mapped[list[Frequencia]] = relationship(
        "Frequencia", back_populates="aluno", cascade="all, delete-orphan"
    )
    alertas: Mapped[list[Alerta]] = relationship(
        "Alerta", back_populates="aluno", cascade="all, delete-orphan"
    )


class Computador(Base):
    """Estação do laboratório com controle de disponibilidade."""

    __tablename__ = "computadores"
    __table_args__ = (
        UniqueConstraint("turma_id", "codigo", name="uq_computador_turma_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    lab: Mapped[str] = mapped_column(String(80), nullable=False)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id"), nullable=False)
    disponivel: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    turma: Mapped[Turma] = relationship("Turma", back_populates="computadores")
    alocacoes: Mapped[list[Frequencia]] = relationship(
        "Frequencia", back_populates="computador"
    )


class Frequencia(Base):
    """Registro de chamada diária com alocação opcional de computador."""

    __tablename__ = "frequencias"
    __table_args__ = (
        UniqueConstraint("aluno_id", "data", name="uq_frequencia_aluno_data"),
        UniqueConstraint(
            "computador_id", "data", name="uq_frequencia_computador_data"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False)
    computador_id: Mapped[int | None] = mapped_column(
        ForeignKey("computadores.id"), nullable=True
    )
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    presente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    aluno: Mapped[Aluno] = relationship("Aluno", back_populates="frequencias")
    computador: Mapped[Computador | None] = relationship(
        "Computador", back_populates="alocacoes"
    )


class Alerta(Base):
    """Alerta de risco de evasão por faltas consecutivas (ODS 4)."""

    __tablename__ = "alertas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(60), default="risco_evasao", nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    faltas_consecutivas: Mapped[int] = mapped_column(Integer, nullable=False)
    resolvido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    aluno: Mapped[Aluno] = relationship("Aluno", back_populates="alertas")
