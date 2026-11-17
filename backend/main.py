"""API FastAPI — autenticação JWT e bootstrap do Gestão Ágil."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.auth import (
    autenticar_usuario,
    criar_access_token,
    get_current_user,
    hash_senha,
)
from backend.database import SessionLocal, get_db, init_db
from backend.models import Usuario
from backend.schemas import LoginIn, TokenOut, UsuarioCreate, UsuarioOut

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _seed_admin()
    yield


app = FastAPI(
    title="Gestão Ágil - Instituto Futuro Tech",
    description=(
        "PWA Mobile-First para chamada diária, alocação de computadores "
        "e prevenção de evasão (ODS 4)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _seed_admin() -> None:
    """Cria educador padrão para demonstração acadêmica."""
    db = SessionLocal()
    try:
        email = "educador@futurotech.edu.br"
        if not db.query(Usuario).filter(Usuario.email == email).first():
            db.add(
                Usuario(
                    nome="Educador Demo",
                    email=email,
                    senha_hash=hash_senha("ift2026"),
                    papel="educador",
                )
            )
            db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "servico": "gestao-agil-futuro-tech"}


@app.post("/api/auth/register", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def register(payload: UsuarioCreate, db: Session = Depends(get_db)):
    """Cadastro de usuário (demo acadêmica; em produção restringir a admin)."""
    email = str(payload.email).lower().strip()
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado.",
        )
    usuario = Usuario(
        nome=payload.nome.strip(),
        email=email,
        senha_hash=hash_senha(payload.senha),
        papel=payload.papel,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """Login com e-mail/senha; retorna JWT Bearer."""
    usuario = autenticar_usuario(db, str(payload.email), payload.senha)
    if not usuario:
        # Mensagem genérica evita enumeração de usuários (OWASP)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )
    token = criar_access_token(subject=usuario.email, papel=usuario.papel)
    return TokenOut(
        access_token=token,
        nome=usuario.nome,
        papel=usuario.papel,
    )


@app.get("/api/auth/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/manifest.json")
    def manifest():
        return FileResponse(FRONTEND_DIR / "manifest.json")

    @app.get("/sw.js")
    def service_worker():
        return FileResponse(
            FRONTEND_DIR / "sw.js",
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )
