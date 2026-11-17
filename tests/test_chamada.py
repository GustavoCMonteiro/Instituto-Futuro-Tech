"""Testes da lógica de alocação e trava de overbooking."""

from backend.models import Aluno, Computador, Frequencia, Turma


def _turma_e_recursos(db_session):
    turma = db_session.query(Turma).first()
    alunos = db_session.query(Aluno).order_by(Aluno.id).all()
    pcs = db_session.query(Computador).order_by(Computador.id).all()
    return turma, alunos, pcs


def test_chamada_aloca_computador(client, auth_header, db_session):
    turma, alunos, pcs = _turma_e_recursos(db_session)
    payload = {
        "turma_id": turma.id,
        "data": "2026-03-10",
        "registros": [
            {
                "aluno_id": alunos[0].id,
                "presente": True,
                "computador_id": pcs[0].id,
            }
        ],
    }
    res = client.post("/api/chamadas", json=payload, headers=auth_header)
    assert res.status_code == 200
    body = res.json()
    assert body["resultados"][0]["status"] == "ok"
    assert body["resultados"][0]["computador_id"] == pcs[0].id

    freq = (
        db_session.query(Frequencia)
        .filter(Frequencia.aluno_id == alunos[0].id)
        .one()
    )
    assert freq.computador_id == pcs[0].id


def test_trava_overbooking_mesmo_pc_no_lote(client, auth_header, db_session):
    turma, alunos, pcs = _turma_e_recursos(db_session)
    payload = {
        "turma_id": turma.id,
        "data": "2026-03-11",
        "registros": [
            {
                "aluno_id": alunos[0].id,
                "presente": True,
                "computador_id": pcs[0].id,
            },
            {
                "aluno_id": alunos[1].id,
                "presente": True,
                "computador_id": pcs[0].id,  # conflito
            },
        ],
    }
    res = client.post("/api/chamadas", json=payload, headers=auth_header)
    assert res.status_code == 200
    resultados = res.json()["resultados"]
    assert resultados[0]["status"] == "ok"
    assert resultados[1]["status"] == "overbooking"
    assert resultados[1]["computador_id"] is None

    alocados = (
        db_session.query(Frequencia)
        .filter(
            Frequencia.data == "2026-03-11",
            Frequencia.computador_id == pcs[0].id,
        )
        .count()
    )
    assert alocados == 1


def test_trava_overbooking_entre_chamadas(client, auth_header, db_session):
    turma, alunos, pcs = _turma_e_recursos(db_session)
    dia = "2026-03-12"
    primeiro = {
        "turma_id": turma.id,
        "data": dia,
        "registros": [
            {
                "aluno_id": alunos[0].id,
                "presente": True,
                "computador_id": pcs[1].id,
            }
        ],
    }
    segundo = {
        "turma_id": turma.id,
        "data": dia,
        "registros": [
            {
                "aluno_id": alunos[1].id,
                "presente": True,
                "computador_id": pcs[1].id,
            }
        ],
    }
    assert client.post("/api/chamadas", json=primeiro, headers=auth_header).status_code == 200
    res = client.post("/api/chamadas", json=segundo, headers=auth_header)
    assert res.status_code == 200
    assert res.json()["resultados"][0]["status"] == "overbooking"
