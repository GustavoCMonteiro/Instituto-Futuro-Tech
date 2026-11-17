"""Fixtures compartilhadas para testes com SQLite em memória."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import hash_senha
from backend.database import Base, get_db
from backend.main import app
from backend.models import Aluno, Computador, Turma, Usuario


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    turma = Turma(nome="Turma Teste", curso="QA", turno="Tarde")
    session.add(turma)
    session.flush()

    session.add(
        Usuario(
            nome="Tester",
            email="tester@futurotech.edu.br",
            senha_hash=hash_senha("senha123"),
            papel="educador",
        )
    )
    session.add_all(
        [
            Aluno(matricula="T001", nome="Aluno Um", turma_id=turma.id),
            Aluno(matricula="T002", nome="Aluno Dois", turma_id=turma.id),
            Aluno(matricula="T003", nome="Aluno Três", turma_id=turma.id),
        ]
    )
    session.add_all(
        [
            Computador(codigo="PC-T1", lab="Lab T", turma_id=turma.id),
            Computador(codigo="PC-T2", lab="Lab T", turma_id=turma.id),
        ]
    )
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_header(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "tester@futurotech.edu.br", "senha": "senha123"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
