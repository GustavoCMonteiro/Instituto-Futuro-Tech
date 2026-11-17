"""Regras de negócio: alocação, overbooking e risco de evasão."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from backend.models import Alerta, Aluno, Computador, Frequencia

LIMITE_FALTAS_CONSECUTIVAS = 3


def computadores_ocupados_na_data(
    db: Session, turma_id: int, dia: date
) -> set[int]:
    """IDs de computadores já alocados na data para a turma."""
    rows = (
        db.query(Frequencia.computador_id)
        .join(Aluno, Aluno.id == Frequencia.aluno_id)
        .filter(
            Aluno.turma_id == turma_id,
            Frequencia.data == dia,
            Frequencia.presente.is_(True),
            Frequencia.computador_id.isnot(None),
        )
        .all()
    )
    return {r[0] for r in rows if r[0] is not None}


def alocar_com_trava_overbooking(
    db: Session,
    *,
    aluno: Aluno,
    dia: date,
    presente: bool,
    computador_id: int | None,
    observacao: str | None,
    ocupados_batch: set[int],
) -> tuple[Frequencia | None, str, str | None]:
    """
    Registra frequência e aloca PC se possível.

    Retorna (frequencia|None, status, detalhe).
    Status: ok | overbooking | ausente | pc_invalido
    """
    if not presente:
        freq = _upsert_frequencia(
            db,
            aluno_id=aluno.id,
            dia=dia,
            presente=False,
            computador_id=None,
            observacao=observacao,
        )
        return freq, "ausente", None

    if computador_id is None:
        freq = _upsert_frequencia(
            db,
            aluno_id=aluno.id,
            dia=dia,
            presente=True,
            computador_id=None,
            observacao=observacao,
        )
        return freq, "ok", "Presente sem alocação de computador."

    pc = (
        db.query(Computador)
        .filter(
            Computador.id == computador_id,
            Computador.turma_id == aluno.turma_id,
            Computador.disponivel.is_(True),
        )
        .first()
    )
    if not pc:
        return None, "pc_invalido", "Computador indisponível ou de outra turma."

    # Trava de overbooking: mesmo PC não pode ser alocado duas vezes no dia
    ja_ocupado = computador_id in ocupados_batch
    if not ja_ocupado:
        conflito = (
            db.query(Frequencia)
            .filter(
                Frequencia.computador_id == computador_id,
                Frequencia.data == dia,
                Frequencia.presente.is_(True),
                Frequencia.aluno_id != aluno.id,
            )
            .first()
        )
        ja_ocupado = conflito is not None

    if ja_ocupado:
        # Registra presença sem o PC conflitante
        freq = _upsert_frequencia(
            db,
            aluno_id=aluno.id,
            dia=dia,
            presente=True,
            computador_id=None,
            observacao=(observacao or "") + " [overbooking bloqueado]",
        )
        return freq, "overbooking", f"Computador {pc.codigo} já alocado nesta data."

    freq = _upsert_frequencia(
        db,
        aluno_id=aluno.id,
        dia=dia,
        presente=True,
        computador_id=computador_id,
        observacao=observacao,
    )
    ocupados_batch.add(computador_id)
    return freq, "ok", f"Alocado em {pc.codigo}."


def _upsert_frequencia(
    db: Session,
    *,
    aluno_id: int,
    dia: date,
    presente: bool,
    computador_id: int | None,
    observacao: str | None,
) -> Frequencia:
    freq = (
        db.query(Frequencia)
        .filter(Frequencia.aluno_id == aluno_id, Frequencia.data == dia)
        .first()
    )
    if freq:
        freq.presente = presente
        freq.computador_id = computador_id
        freq.observacao = observacao
    else:
        freq = Frequencia(
            aluno_id=aluno_id,
            data=dia,
            presente=presente,
            computador_id=computador_id,
            observacao=observacao,
        )
        db.add(freq)
    db.flush()
    return freq


def calcular_faltas_consecutivas(db: Session, aluno_id: int, ate: date | None = None) -> int:
    """Conta faltas consecutivas a partir da data mais recente para trás."""
    limite = ate or date.today()
    registros = (
        db.query(Frequencia)
        .filter(Frequencia.aluno_id == aluno_id, Frequencia.data <= limite)
        .order_by(Frequencia.data.desc())
        .all()
    )
    faltas = 0
    esperado = limite
    # Conta apenas sequência contínua de ausências nas datas registradas
    for reg in registros:
        if reg.presente:
            break
        faltas += 1
        esperado = reg.data - timedelta(days=1)
    return faltas


def atualizar_risco_evasao(db: Session, aluno: Aluno, dia: date) -> Alerta | None:
    """Atualiza contador e gera alerta se atingir o limite (prevenção de evasão)."""
    faltas = calcular_faltas_consecutivas(db, aluno.id, ate=dia)
    aluno.faltas_consecutivas = faltas

    if faltas < LIMITE_FALTAS_CONSECUTIVAS:
        return None

    aberto = (
        db.query(Alerta)
        .filter(
            Alerta.aluno_id == aluno.id,
            Alerta.resolvido.is_(False),
            Alerta.tipo == "risco_evasao",
        )
        .first()
    )
    mensagem = (
        f"Risco de evasão: {aluno.nome} acumulou {faltas} faltas consecutivas "
        f"(limite {LIMITE_FALTAS_CONSECUTIVAS}). Ação pedagógica recomendada."
    )
    if aberto:
        aberto.faltas_consecutivas = faltas
        aberto.mensagem = mensagem
        db.flush()
        return aberto

    alerta = Alerta(
        aluno_id=aluno.id,
        tipo="risco_evasao",
        mensagem=mensagem,
        faltas_consecutivas=faltas,
    )
    db.add(alerta)
    db.flush()
    return alerta


def listar_alertas_abertos(db: Session) -> list[Alerta]:
    return (
        db.query(Alerta)
        .options(joinedload(Alerta.aluno))
        .filter(Alerta.resolvido.is_(False))
        .order_by(Alerta.criado_em.desc())
        .all()
    )
