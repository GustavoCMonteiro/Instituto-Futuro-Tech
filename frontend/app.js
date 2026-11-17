/* Gestão Ágil — lógica do PWA e consumo da API */
(() => {
  const TOKEN_KEY = "gestao_agil_token";
  const USER_KEY = "gestao_agil_user";

  const els = {
    viewLogin: document.getElementById("view-login"),
    viewApp: document.getElementById("view-app"),
    formLogin: document.getElementById("form-login"),
    loginMsg: document.getElementById("login-msg"),
    onlineStatus: document.getElementById("online-status"),
    userChip: document.getElementById("user-chip"),
    btnLogout: document.getElementById("btn-logout"),
    screenChamada: document.getElementById("screen-chamada"),
    screenAlertas: document.getElementById("screen-alertas"),
    selectTurma: document.getElementById("select-turma"),
    inputData: document.getElementById("input-data"),
    listaAlunos: document.getElementById("lista-alunos"),
    listaAlertas: document.getElementById("lista-alertas"),
    btnSalvar: document.getElementById("btn-salvar-chamada"),
    chamadaMsg: document.getElementById("chamada-msg"),
    btnInstalar: document.getElementById("btn-instalar"),
    navButtons: document.querySelectorAll(".nav-bottom [data-screen]"),
  };

  let deferredPrompt = null;
  let alunosCache = [];
  let computadoresCache = [];

  function token() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setSession(data) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(
      USER_KEY,
      JSON.stringify({ nome: data.nome, papel: data.papel })
    );
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function showMsg(el, text, type) {
    el.textContent = text;
    el.className = `msg ${type}`;
  }

  async function api(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
    const t = token();
    if (t) headers.Authorization = `Bearer ${t}`;

    const res = await fetch(path, { ...options, headers });
    let body = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      body = await res.json();
    } else {
      body = await res.text();
    }
    if (!res.ok) {
      const detail = body?.detail || "Falha na requisição.";
      const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      err.status = res.status;
      throw err;
    }
    return body;
  }

  function renderAuth() {
    const logged = Boolean(token());
    els.viewLogin.classList.toggle("hidden", logged);
    els.viewApp.classList.toggle("hidden", !logged);
    if (logged) {
      const user = JSON.parse(localStorage.getItem(USER_KEY) || "{}");
      els.userChip.textContent = user.nome || "Educador";
      showScreen("chamada");
      bootstrapAppData().catch((e) => {
        showMsg(els.chamadaMsg, e.message, "error");
      });
    }
  }

  function showScreen(name) {
    els.screenChamada.classList.toggle("hidden", name !== "chamada");
    els.screenAlertas.classList.toggle("hidden", name !== "alertas");
    els.navButtons.forEach((btn) => {
      btn.setAttribute("aria-current", btn.dataset.screen === name ? "page" : "false");
    });
    if (name === "alertas") {
      loadAlertas().catch((e) => {
        els.listaAlertas.innerHTML = `<div class="msg error">${e.message}</div>`;
      });
    }
  }

  async function bootstrapAppData() {
    if (!els.inputData.value) {
      els.inputData.value = new Date().toISOString().slice(0, 10);
    }
    const turmas = await api("/api/turmas");
    els.selectTurma.innerHTML = turmas
      .map((t) => `<option value="${t.id}">${t.nome} · ${t.turno}</option>`)
      .join("");
    if (turmas.length) {
      await loadTurmaDetalhe();
    } else {
      els.listaAlunos.innerHTML =
        '<p class="meta">Nenhuma turma cadastrada. Execute o seed do backend.</p>';
    }
  }

  async function loadTurmaDetalhe() {
    const turmaId = els.selectTurma.value;
    if (!turmaId) return;
    const [alunos, comps] = await Promise.all([
      api(`/api/turmas/${turmaId}/alunos`),
      api(`/api/turmas/${turmaId}/computadores`),
    ]);
    alunosCache = alunos;
    computadoresCache = comps;
    renderAlunos();
  }

  function renderAlunos() {
    const disponiveis = computadoresCache.filter((c) => c.disponivel);
    els.listaAlunos.innerHTML = alunosCache
      .map((a) => {
        const options = [
          '<option value="">Sem computador</option>',
          ...disponiveis.map(
            (c) => `<option value="${c.id}">${c.codigo} · ${c.lab}</option>`
          ),
        ].join("");
        return `
          <article class="list-item" data-aluno-id="${a.id}">
            <header>
              <strong>${a.nome}</strong>
              <span class="meta">${a.matricula}</span>
            </header>
            <div class="row-actions">
              <label class="toggle">
                <input type="checkbox" class="chk-presente" checked />
                Presente
              </label>
              <label>
                Computador
                <select class="sel-pc">${options}</select>
              </label>
            </div>
          </article>`;
      })
      .join("");
  }

  async function salvarChamada() {
    const turmaId = Number(els.selectTurma.value);
    const data = els.inputData.value;
    const registros = [...els.listaAlunos.querySelectorAll(".list-item")].map((item) => {
      const presente = item.querySelector(".chk-presente").checked;
      const pc = item.querySelector(".sel-pc").value;
      return {
        aluno_id: Number(item.dataset.alunoId),
        presente,
        computador_id: presente && pc ? Number(pc) : null,
      };
    });

    try {
      const out = await api("/api/chamadas", {
        method: "POST",
        body: JSON.stringify({ turma_id: turmaId, data, registros }),
      });
      const conflitos = out.resultados.filter((r) => r.status === "overbooking");
      if (conflitos.length) {
        showMsg(
          els.chamadaMsg,
          `Chamada salva com travas: ${conflitos.length} overbooking(s) bloqueado(s). Alertas: ${out.alertas_gerados}.`,
          "warn"
        );
      } else {
        showMsg(
          els.chamadaMsg,
          `Chamada salva. Alertas gerados: ${out.alertas_gerados}.`,
          "ok"
        );
      }
      await loadTurmaDetalhe();
    } catch (e) {
      showMsg(els.chamadaMsg, e.message, "error");
    }
  }

  async function loadAlertas() {
    const alertas = await api("/api/alertas");
    if (!alertas.length) {
      els.listaAlertas.innerHTML = '<p class="meta">Nenhum alerta aberto no momento.</p>';
      return;
    }
    els.listaAlertas.innerHTML = alertas
      .map(
        (a) => `
        <article class="list-item">
          <header>
            <strong>${a.aluno?.nome || `Aluno #${a.aluno_id}`}</strong>
            <span class="badge risco">${a.faltas_consecutivas} faltas</span>
          </header>
          <p class="meta">${a.mensagem}</p>
          <button class="btn btn-danger" type="button" data-resolver="${a.id}">Marcar resolvido</button>
        </article>`
      )
      .join("");
  }

  els.formLogin.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const email = document.getElementById("login-email").value.trim();
    const senha = document.getElementById("login-senha").value;
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, senha }),
      });
      setSession(data);
      showMsg(els.loginMsg, "Login realizado com sucesso.", "ok");
      renderAuth();
    } catch (e) {
      showMsg(els.loginMsg, e.message, "error");
    }
  });

  els.btnLogout.addEventListener("click", () => {
    clearSession();
    renderAuth();
  });

  els.navButtons.forEach((btn) => {
    btn.addEventListener("click", () => showScreen(btn.dataset.screen));
  });

  els.selectTurma.addEventListener("change", () => {
    loadTurmaDetalhe().catch((e) => showMsg(els.chamadaMsg, e.message, "error"));
  });

  els.btnSalvar.addEventListener("click", salvarChamada);

  els.listaAlertas.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("[data-resolver]");
    if (!btn) return;
    try {
      await api(`/api/alertas/${btn.dataset.resolver}/resolver`, { method: "PATCH" });
      await loadAlertas();
    } catch (e) {
      els.listaAlertas.insertAdjacentHTML(
        "afterbegin",
        `<div class="msg error">${e.message}</div>`
      );
    }
  });

  function updateOnline() {
    const on = navigator.onLine;
    els.onlineStatus.textContent = on ? "Online" : "Offline";
  }
  window.addEventListener("online", updateOnline);
  window.addEventListener("offline", updateOnline);
  updateOnline();

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    els.btnInstalar.classList.remove("hidden");
  });

  els.btnInstalar.addEventListener("click", async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    els.btnInstalar.classList.add("hidden");
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    });
  }

  renderAuth();
})();
