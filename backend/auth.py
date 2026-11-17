"""Autenticação JWT com hash bcrypt (OWASP: senhas nunca em texto puro)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Usuario

SECRET_KEY = os.getenv("GESTAO_AGIL_SECRET", "ift-gestao-agil-dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("GESTAO_AGIL_TOKEN_MINUTES", "480"))

security = HTTPBearer(auto_error=True)


def hash_senha(senha: str) -> str:
    """Gera hash bcrypt da senha (custo padrão seguro)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(senha.encode("utf-8"), salt).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Compara senha em texto com o hash armazenado."""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        return False


def criar_access_token(subject: str, papel: str, expires_delta: timedelta | None = None) -> str:
    """Emite JWT assinado com claims mínimos necessários."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "papel": papel,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Valida e decodifica o JWT; levanta 401 em falha."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado. Faça login novamente.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        ) from exc


def autenticar_usuario(db: Session, email: str, senha: str) -> Usuario | None:
    """Retorna o usuário se as credenciais forem válidas."""
    usuario = db.query(Usuario).filter(Usuario.email == email.lower().strip()).first()
    if not usuario or not usuario.ativo:
        return None
    if not verificar_senha(senha, usuario.senha_hash):
        return None
    return usuario


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Dependency: exige Bearer JWT válido e usuário ativo."""
    payload = decodificar_token(credentials.credentials)
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem sujeito (sub).",
        )
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    return usuario
