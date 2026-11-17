"""Testes do cálculo de faltas consecutivas e alertas de evasão."""

from datetime import date, timedelta

from backend.models import Alerta, Aluno, Frequencia
from backend.services import (
    LIMITE_FALTAS_CONSECUTIVAS,
    atualizar_risco_evasao,
    calcular_faltas_consecutivas,
)


def test_calculo_faltas_consecutivas(db_session):
    aluno = db_session.query(Aluno).filter(Aluno.matricula == "T001").one()
    base = date(2026, 3, 1)
    for i in range(4):
        db_session.add(
            Frequencia(
                aluno_id=aluno.id,
                data=base + timedelta(days=i),
                presente=False,
            )
        )
    db_session.commit()

    faltas = calcular_faltas_consecutivas(db_session, aluno.id, ate=base + timedelta(days=3))
    assert faltas == 4


def test_presenca_zera_sequencia(db_session):
    aluno = db_session.query(Aluno).filter(Aluno.matricula == "T002").one()
    base = date(2026, 3, 1)
    db_session.add_all(
        [
            Frequencia(aluno_id=aluno.id, data=base, presente=False),
            Frequencia(aluno_id=aluno.id, data=base + timedelta(days=1), presente=False),
            Frequencia(aluno_id=aluno.id, data=base + timedelta(days=2), presente=True),
            Frequencia(aluno_id=aluno.id, data=base + timedelta(days=3), presente=False),
        ]
    )
    db_session.commit()

    faltas = calcular_faltas_consecutivas(db_session, aluno.id, ate=base + timedelta(days=3))
    assert faltas == 1


def test_alerta_gerado_ao_atingir_limite(db_session):
    aluno = db_session.query(Aluno).filter(Aluno.matricula == "T003").one()
    base = date(2026, 4, 1)
    for i in range(LIMITE_FALTAS_CONSECUTIVAS):
        db_session.add(
            Frequencia(
                aluno_id=aluno.id,
                data=base + timedelta(days=i),
                presente=False,
            )
        )
    db_session.commit()

    alerta = atualizar_risco_evasao(db_session, aluno, base + timedelta(days=2))
    db_session.commit()

    assert alerta is not None
    assert alerta.tipo == "risco_evasao"
    assert alerta.faltas_consecutivas >= LIMITE_FALTAS_CONSECUTIVAS
    assert aluno.faltas_consecutivas >= LIMITE_FALTAS_CONSECUTIVAS

    abertos = db_session.query(Alerta).filter(Alerta.resolvido.is_(False)).count()
    assert abertos == 1


def test_api_chamada_gera_alerta_de_evasao(client, auth_header, db_session):
    aluno = db_session.query(Aluno).filter(Aluno.matricula == "T001").one()
    turma_id = aluno.turma_id
    base = date(2026, 5, 1)

    for i in range(LIMITE_FALTAS_CONSECUTIVAS):
        payload = {
            "turma_id": turma_id,
            "data": (base + timedelta(days=i)).isoformat(),
            "registros": [{"aluno_id": aluno.id, "presente": False}],
        }
        res = client.post("/api/chamadas", json=payload, headers=auth_header)
        assert res.status_code == 200

    painel = client.get("/api/alertas", headers=auth_header)
    assert painel.status_code == 200
    alertas = painel.json()
    assert any(a["aluno_id"] == aluno.id for a in alertas)
