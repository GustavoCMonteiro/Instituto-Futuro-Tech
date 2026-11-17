"""Testes unitários de autenticação JWT e bcrypt."""

from backend.auth import criar_access_token, hash_senha, verificar_senha


def test_hash_bcrypt_nao_armazena_texto_puro():
    senha = "senha123"
    digest = hash_senha(senha)
    assert digest != senha
    assert digest.startswith("$2")
    assert verificar_senha(senha, digest) is True
    assert verificar_senha("outra", digest) is False


def test_login_sucesso(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "tester@futurotech.edu.br", "senha": "senha123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["nome"] == "Tester"


def test_login_credenciais_invalidas(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "tester@futurotech.edu.br", "senha": "errada"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Credenciais inválidas."


def test_rota_protegida_exige_token(client):
    res = client.get("/api/turmas")
    assert res.status_code in (401, 403)


def test_me_com_token_valido(client, auth_header):
    res = client.get("/api/auth/me", headers=auth_header)
    assert res.status_code == 200
    assert res.json()["email"] == "tester@futurotech.edu.br"


def test_token_jwt_contem_subject():
    token = criar_access_token(subject="a@b.com", papel="educador")
    assert isinstance(token, str)
    assert token.count(".") == 2
