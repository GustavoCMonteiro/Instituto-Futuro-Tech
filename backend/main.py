"""API FastAPI — Login, Chamada, Alocação e Painel de Alertas."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
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
from backend.models import Alerta, Aluno, Computador, Turma, Usuario
from backend.schemas import (
    AlertaOut,
    AlocacaoResultado,
    AlunoOut,
    ChamadaDiariaIn,
    ChamadaDiariaOut,
    ComputadorOut,
    LoginIn,
    TokenOut,
    TurmaOut,
    UsuarioCreate,
    UsuarioOut,
)
from backend.services import (
    alocar_com_trava_overbooking,
    atualizar_risco_evasao,
    computadores_ocupados_na_data,
    listar_alertas_abertos,
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _seed_demo()
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


def _seed_demo() -> None:
    """Dados iniciais para demonstração acadêmica."""
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

        if not db.query(Turma).first():
            turma = Turma(
                nome="1º Ano A",
                curso="Informática",
                turno="Manhã",
            )
            db.add(turma)
            db.flush()

            alunos = [
                Aluno(matricula="IFT2026001", nome="Beatriz Lima", turma_id=turma.id),
                Aluno(matricula="IFT2026002", nome="Gabriel Souza", turma_id=turma.id),
                Aluno(matricula="IFT2026003", nome="Mariana Alves", turma_id=turma.id),
                Aluno(matricula="IFT2026004", nome="Lucas Pereira", turma_id=turma.id),
                Aluno(matricula="IFT2026005", nome="Ana Costa", turma_id=turma.id),
            ]
            db.add_all(alunos)

            pcs = [
                Computador(codigo="PC 01", lab="Lab 1", turma_id=turma.id),
                Computador(codigo="PC 02", lab="Lab 1", turma_id=turma.id),
                Computador(codigo="PC 03", lab="Lab 1", turma_id=turma.id),
                Computador(codigo="PC 04", lab="Lab 1", turma_id=turma.id),
                Computador(codigo="PC 05", lab="Lab 1", turma_id=turma.id),
                Computador(codigo="PC 06", lab="Lab 1", turma_id=turma.id, disponivel=False),
            ]
            db.add_all(pcs)

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


@app.get("/api/turmas", response_model=list[TurmaOut])
def listar_turmas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return db.query(Turma).filter(Turma.ativa.is_(True)).order_by(Turma.nome).all()


@app.get("/api/turmas/{turma_id}/alunos", response_model=list[AlunoOut])
def listar_alunos(
    turma_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    turma = db.get(Turma, turma_id)
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    return (
        db.query(Aluno)
        .filter(Aluno.turma_id == turma_id, Aluno.ativo.is_(True))
        .order_by(Aluno.nome)
        .all()
    )


@app.get("/api/turmas/{turma_id}/computadores", response_model=list[ComputadorOut])
def listar_computadores(
    turma_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    turma = db.get(Turma, turma_id)
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    return (
        db.query(Computador)
        .filter(Computador.turma_id == turma_id)
        .order_by(Computador.codigo)
        .all()
    )


@app.post("/api/chamadas", response_model=ChamadaDiariaOut)
def registrar_chamada(
    payload: ChamadaDiariaIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Chamada diária com alocação e trava de overbooking de computadores."""
    turma = db.get(Turma, payload.turma_id)
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")

    dia = payload.data or date.today()
    ocupados = computadores_ocupados_na_data(db, payload.turma_id, dia)
    resultados: list[AlocacaoResultado] = []
    alertas_gerados = 0

    # Detecta tentativa explícita de overbooking no mesmo payload
    vistos_no_payload: set[int] = set()

    for item in payload.registros:
        aluno = (
            db.query(Aluno)
            .filter(Aluno.id == item.aluno_id, Aluno.turma_id == payload.turma_id)
            .first()
        )
        if not aluno:
            resultados.append(
                AlocacaoResultado(
                    aluno_id=item.aluno_id,
                    presente=item.presente,
                    status="aluno_invalido",
                    detalhe="Aluno não pertence à turma.",
                )
            )
            continue

        computador_id = item.computador_id
        if (
            item.presente
            and computador_id is not None
            and computador_id in vistos_no_payload
        ):
            # Trava imediata no batch: dois alunos no mesmo PC
            freq, status_aloc, detalhe = alocar_com_trava_overbooking(
                db,
                aluno=aluno,
                dia=dia,
                presente=True,
                computador_id=None,
                observacao=(item.observacao or "") + " [overbooking no lote]",
                ocupados_batch=ocupados,
            )
            status_aloc = "overbooking"
            detalhe = f"Computador {computador_id} duplicado no mesmo envio."
        else:
            if item.presente and computador_id is not None:
                vistos_no_payload.add(computador_id)
            freq, status_aloc, detalhe = alocar_com_trava_overbooking(
                db,
                aluno=aluno,
                dia=dia,
                presente=item.presente,
                computador_id=computador_id,
                observacao=item.observacao,
                ocupados_batch=ocupados,
            )

        alerta = atualizar_risco_evasao(db, aluno, dia)
        if alerta and not alerta.resolvido and alerta.faltas_consecutivas >= 3:
            # Conta apenas quando o alerta reflete o estado atual pós-chamada
            if not item.presente:
                alertas_gerados += 1

        resultados.append(
            AlocacaoResultado(
                aluno_id=aluno.id,
                presente=item.presente if freq else item.presente,
                computador_id=freq.computador_id if freq else None,
                status=status_aloc,
                detalhe=detalhe,
            )
        )

    db.commit()
    return ChamadaDiariaOut(
        data=dia,
        turma_id=payload.turma_id,
        resultados=resultados,
        alertas_gerados=alertas_gerados,
    )


@app.get("/api/alertas", response_model=list[AlertaOut])
def painel_alertas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return listar_alertas_abertos(db)


@app.patch("/api/alertas/{alerta_id}/resolver", response_model=AlertaOut)
def resolver_alerta(
    alerta_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    alerta = db.get(Alerta, alerta_id)
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    alerta.resolvido = True
    db.commit()
    db.refresh(alerta)
    return alerta


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
