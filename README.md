# Gestão Ágil — Instituto Futuro Tech (PWA Mobile-First)

Aplicação acadêmica e profissional para **chamada diária**, **alocação de computadores de laboratório** (com trava de overbooking) e **painel de alertas de risco de evasão**, alinhada ao **ODS 4 — Educação de Qualidade**.

## Problema resolvido

- Elimina a descentralização de registros em cadernos físicos
- Evita overbooking de estações no laboratório
- Auxilia na prevenção da evasão escolar por meio de faltas consecutivas

## Stack

| Camada | Tecnologias |
|--------|-------------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy, SQLite |
| Frontend / PWA | HTML5, CSS3 responsivo, JavaScript, Service Worker |
| Segurança | JWT (PyJWT), bcrypt, práticas OWASP (mensagens genéricas de login, senhas hasheadas) |

## Estrutura do repositório

```text
.
├── backend/
│   ├── database.py      # SQLAlchemy + SQLite
│   ├── models.py        # ORM (Alunos, Turmas, Computadores, Frequência, Alertas)
│   ├── schemas.py       # Validação Pydantic
│   ├── auth.py          # JWT + bcrypt
│   ├── services.py      # Overbooking e risco de evasão
│   └── main.py          # Rotas da API + servir PWA
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── sw.js            # Offline-First
│   └── manifest.json
├── tests/
│   ├── test_auth.py
│   ├── test_chamada.py
│   └── test_evasao.py
├── requirements.txt
└── README.md
```

## Pré-requisitos

- Python 3.12 ou superior (testado também em ambientes mais novos)
- `pip` e `venv`
- Navegador moderno com suporte a Service Workers (Chrome, Edge, Firefox)

## Instalação e execução

```bash
# 1) Clone
git clone https://github.com/GustavoCMonteiro/Instituto-Futuro-Tech.git
cd Instituto-Futuro-Tech

# 2) Ambiente virtual
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3) Dependências
# Em Python >= 3.14, se pydantic-core falhar ao compilar:
#   export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
pip install -r requirements.txt

# 4) Subir a API + PWA
export PYTHONPATH=.
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Abra: [http://127.0.0.1:8000](http://127.0.0.1:8000)

Documentação interativa (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Credenciais de demonstração

| Campo | Valor |
|-------|--------|
| E-mail | `educador@futurotech.edu.br` |
| Senha | `ift2026` |

O banco SQLite `gestao_agil.db` é criado automaticamente na primeira execução, com turma, alunos e computadores de exemplo.

## PWA Offline-First

1. Acesse a aplicação via **HTTPS** (ou `localhost`)
2. O Service Worker (`sw.js`) pré-cacheia o shell (HTML/CSS/JS/manifest)
3. Em offline:
   - Telas estáticas continuam disponíveis (cache-first)
   - Chamadas à API retornam `503` amigável (network-first)
4. No Chrome/Edge mobile ou desktop: **Instalar aplicativo** / “Add to Home Screen”
5. O `manifest.json` define nome, ícones, `theme_color` e `display: standalone`

> Dica: use DevTools → Application → Service Workers / Cache Storage para validar o modo offline.

## Principais endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/auth/login` | Login JWT |
| `GET` | `/api/auth/me` | Usuário autenticado |
| `GET` | `/api/turmas` | Lista turmas |
| `GET` | `/api/turmas/{id}/alunos` | Alunos da turma |
| `GET` | `/api/turmas/{id}/computadores` | Computadores do lab |
| `POST` | `/api/chamadas` | Chamada + alocação (trava overbooking) |
| `GET` | `/api/alertas` | Painel de risco de evasão |
| `PATCH` | `/api/alertas/{id}/resolver` | Marca alerta como resolvido |

### Regra de overbooking

Um computador **não pode** ser alocado a dois alunos na mesma data. Conflitos no mesmo lote ou em chamadas posteriores são bloqueados; a presença pode ser registrada sem o PC conflitante e o status retorna `overbooking`.

### Regra de evasão

Após **3 faltas consecutivas** (`LIMITE_FALTAS_CONSECUTIVAS`), o sistema gera/atualiza um alerta do tipo `risco_evasao` no painel pedagógico.

## Testes

```bash
source .venv/bin/activate
export PYTHONPATH=.
pytest tests/ -v
```

Cobertura incluída:

- Autenticação (bcrypt + JWT + rotas protegidas)
- Alocação e trava de overbooking
- Cálculo de faltas consecutivas e geração de alertas

## Variáveis de ambiente (opcional)

| Variável | Padrão | Uso |
|----------|--------|-----|
| `GESTAO_AGIL_SECRET` | chave de desenvolvimento | Segredo JWT |
| `GESTAO_AGIL_TOKEN_MINUTES` | `480` | Expiração do token |

**Em produção**, altere `GESTAO_AGIL_SECRET` e restrinja CORS/`/api/auth/register`.

## Histórico de commits semânticos

1. `feat: estrutura inicial do banco de dados SQLite, modelos ORM e conexões via SQLAlchemy`
2. `feat: implementação da tela de autenticação e rotas de segurança JWT com hash bcrypt`
3. `feat: rotas de chamada diária e lógica de alocação com trava de overbooking de computadores`
4. `test: implementação de testes unitários para o cálculo de faltas consecutivas e alertas de evasão`
5. `docs: atualização do arquivo README.md com instruções de execução e configuração do PWA offline-first`

## Licença

Projeto acadêmico — Instituto Futuro Tech. Uso educacional e demonstração profissional.
