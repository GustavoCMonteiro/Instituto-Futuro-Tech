/* Gestão Ágil — UI alinhada ao protótipo + consumo da API */
(() => {
  const TOKEN_KEY = "gestao_agil_token";
  const USER_KEY = "gestao_agil_user";

  const els = {
    viewLogin: document.getElementById("view-login"),
    viewApp: document.getElementById("view-app"),
    formLogin: document.getElementById("form-login"),
    loginMsg: document.getElementById("login-msg"),
    onlineStatus: document.getElementById("online-status"),
    headerTitle: document.getElementById("header-title"),
    btnLogout: document.getElementById("btn-logout"),
    screenChamada: document.getElementById("screen-chamada"),
    screenAlertas: document.getElementById("screen-alertas"),
    selectTurma: document.getElementById("select-turma"),
    inputData: document.getElementById("input-data"),
    listaAlunos: document.getElementById("lista-alunos"),
    listaAlertas: document.getElementById("lista-alertas"),
    contador: document.getElementById("contador-alunos"),
    btnSalvar: document.getElementById("btn-salvar-chamada"),
    chamadaMsg: document.getElementById("chamada-msg"),
    riscoTitulo: document.getElementById("risco-titulo"),
    metricOcupacao: document.getElementById("metric-ocupacao"),
    metricPresencas: document.getElementById("metric-presencas"),
    metricPresencasSub: document.getElementById("metric-presencas-sub"),
    btnInstalar: document.getElementById("btn-instalar"),
    btnToggleSenha: document.getElementById("btn-toggle-senha"),
    navButtons: document.querySelectorAll(".nav-bottom [data-screen]"),
  };

  let deferredPrompt = null;
  let alunosCache = [];
  let computadoresCache = [];
  let turmaNome = "";
  /** @type {Record<number, { presente: boolean|null, computadorId: number|null }>} */
  let estadoAlunos = {};

  function token() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setSession(data) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify({ nome: data.nome, papel: data.papel }));
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
    body = ct.includes("application/json") ? await res.json() : await res.text();
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
    document.body.style.background = logged ? "var(--bg)" : "";
    if (logged) {
      showScreen("chamada");
      bootstrapAppData().catch((e) => showMsg(els.chamadaMsg, e.message, "error"));
    }
  }

  function showScreen(name) {
    els.screenChamada.classList.toggle("hidden", name !== "chamada");
    els.screenAlertas.classList.toggle("hidden", name !== "alertas");
    els.headerTitle.textContent =
      name === "alertas" ? "Painel de Alertas" : "Chamada e Máquinas";
    els.navButtons.forEach((btn) => {
      btn.setAttribute("aria-current", btn.dataset.screen === name ? "page" : "false");
    });
    if (name === "alertas") {
      loadAlertas().catch((e) => {
        els.listaAlertas.innerHTML = `<div class="msg error">${e.message}</div>`;
      });
    }
  }

  function pcsOcupadosNoEstado(excetoAlunoId = null) {
    const ids = new Set();
    Object.entries(estadoAlunos).forEach(([alunoId, st]) => {
      if (excetoAlunoId && Number(alunoId) === excetoAlunoId) return;
      if (st.presente === true && st.computadorId) ids.add(st.computadorId);
    });
    return ids;
  }

  function atualizarContador() {
    const total = alunosCache.length;
    const registrados = Object.values(estadoAlunos).filter((s) => s.presente !== null).length;
    els.contador.textContent = `${registrados} de ${total} alunos registrados`;
  }

  function renderAlunos() {
    const ocupados = pcsOcupadosNoEstado();
    els.listaAlunos.innerHTML = alunosCache
      .map((a) => {
        const st = estadoAlunos[a.id] || { presente: null, computadorId: null };
        const showPcs = st.presente === true;
        const pcs = computadoresCache
          .map((c) => {
            const taken = ocupados.has(c.id) && st.computadorId !== c.id;
            const selected = st.computadorId === c.id;
            let cls = "pc-chip";
            if (taken || !c.disponivel) cls += " is-ocupado";
            else if (selected) cls += " is-selected";
            const status = taken || !c.disponivel ? "Ocupado" : selected ? "Selecionado" : "Livre";
            const icon =
              taken || !c.disponivel
                ? "🔒"
                : selected
                  ? "✓"
                  : "✓";
            return `<button type="button" class="${cls}" data-pc="${c.id}" ${
              taken || !c.disponivel ? "disabled" : ""
            }><strong>${c.codigo}</strong><span>${icon} ${status}</span></button>`;
          })
          .join("");

        return `
          <article class="aluno-card" data-aluno-id="${a.id}">
            <header>
              <strong>${a.nome}</strong>
              <span>${turmaNome || "Turma"}</span>
            </header>
            <div class="presence-row">
              <button type="button" class="btn-presence presente ${
                st.presente === true ? "is-active" : ""
              }" data-action="presente">
                👤✓ Presente
              </button>
              <button type="button" class="btn-presence falta ${
                st.presente === false ? "is-active" : ""
              }" data-action="falta">
                👤✕ Falta
              </button>
            </div>
            ${
              showPcs
                ? `<div class="pc-block">
                    <div class="pc-label">💻 Computador — selecione</div>
                    <div class="pc-grid">${pcs}</div>
                  </div>`
                : st.presente === null
                  ? `<p class="pc-hint">Toque em <strong>Presente</strong> para liberar a escolha do computador.</p>`
                  : `<p class="pc-hint is-falta">Falta registrada — sem alocação de máquina.</p>`
            }
          </article>`;
      })
      .join("");
    atualizarContador();
  }

  async function bootstrapAppData() {
    if (!els.inputData.value) {
      els.inputData.value = new Date().toISOString().slice(0, 10);
    }
    const turmas = await api("/api/turmas");
    els.selectTurma.innerHTML = turmas
      .map((t) => `<option value="${t.id}">${t.nome}</option>`)
      .join("");
    if (!turmas.length) {
      els.listaAlunos.innerHTML =
        '<p class="empty-state">Nenhuma turma cadastrada.</p>';
      return;
    }
    turmaNome = turmas[0].nome;
    await loadTurmaDetalhe();
  }

  async function loadTurmaDetalhe() {
    const turmaId = els.selectTurma.value;
    if (!turmaId) return;
    turmaNome = els.selectTurma.selectedOptions[0]?.textContent || turmaNome;
    const [alunos, comps] = await Promise.all([
      api(`/api/turmas/${turmaId}/alunos`),
      api(`/api/turmas/${turmaId}/computadores`),
    ]);
    alunosCache = alunos;
    computadoresCache = comps;
    estadoAlunos = {};
    alunos.forEach((a) => {
      estadoAlunos[a.id] = { presente: null, computadorId: null };
    });
    renderAlunos();
  }

  async function salvarChamada() {
    const turmaId = Number(els.selectTurma.value);
    const data = els.inputData.value;
    const registros = alunosCache
      .filter((a) => estadoAlunos[a.id]?.presente !== null)
      .map((a) => {
        const st = estadoAlunos[a.id];
        return {
          aluno_id: a.id,
          presente: st.presente === true,
          computador_id: st.presente === true ? st.computadorId : null,
        };
      });

    if (!registros.length) {
      showMsg(els.chamadaMsg, "Marque presença ou falta de pelo menos um aluno.", "warn");
      return;
    }

    try {
      const out = await api("/api/chamadas", {
        method: "POST",
        body: JSON.stringify({ turma_id: turmaId, data, registros }),
      });
      const conflitos = out.resultados.filter((r) => r.status === "overbooking");
      showMsg(
        els.chamadaMsg,
        conflitos.length
          ? `Salvo com ${conflitos.length} overbooking(s) bloqueado(s).`
          : `Chamada salva com sucesso.`,
        conflitos.length ? "warn" : "ok"
      );
      await loadTurmaDetalhe();
    } catch (e) {
      showMsg(els.chamadaMsg, e.message, "error");
    }
  }

  async function loadAlertas() {
    const alertas = await api("/api/alertas");
    const totalPc = Math.max(computadoresCache.length, 1);
    const ocupados = pcsOcupadosNoEstado().size;
    const ocupacao = Math.round((ocupados / totalPc) * 100);
    const presentesHoje = Object.values(estadoAlunos).filter((s) => s.presente === true).length;

    els.metricOcupacao.textContent = `${ocupacao}%`;
    els.metricPresencas.textContent = String(presentesHoje);
    els.metricPresencasSub.textContent = `registradas · ${presentesHoje} hoje`;
    els.riscoTitulo.textContent = `Risco de evasão (${alertas.length})`;

    if (!alertas.length) {
      els.listaAlertas.innerHTML =
        '<p class="empty-state">Nenhum alerta aberto no momento.</p>';
      return;
    }

    els.listaAlertas.innerHTML = alertas
      .map(
        (a) => `
        <article class="alerta-card">
          <div class="warn-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4M12 17h.01"/>
            </svg>
          </div>
          <div>
            <strong>${a.aluno?.nome || `Aluno #${a.aluno_id}`} — ${a.faltas_consecutivas} Faltas Consecutivas Detectadas</strong>
            <p>${turmaNome || "Turma"} · Recomenda-se contato com a família.</p>
            <button type="button" class="resolve" data-resolver="${a.id}">Marcar resolvido</button>
          </div>
        </article>`
      )
      .join("");
  }

  els.listaAlunos.addEventListener("click", (ev) => {
    const card = ev.target.closest(".aluno-card");
    if (!card) return;
    const alunoId = Number(card.dataset.alunoId);
    const st = estadoAlunos[alunoId];
    if (!st) return;

    const actionBtn = ev.target.closest("[data-action]");
    if (actionBtn) {
      const action = actionBtn.dataset.action;
      st.presente = action === "presente" ? true : false;
      if (st.presente !== true) st.computadorId = null;
      renderAlunos();
      return;
    }

    const pcBtn = ev.target.closest("[data-pc]");
    if (pcBtn && !pcBtn.disabled) {
      const pcId = Number(pcBtn.dataset.pc);
      st.computadorId = st.computadorId === pcId ? null : pcId;
      st.presente = true;
      renderAlunos();
    }
  });

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
      renderAuth();
    } catch (e) {
      showMsg(els.loginMsg, e.message, "error");
    }
  });

  els.btnToggleSenha?.addEventListener("click", () => {
    const input = document.getElementById("login-senha");
    input.type = input.type === "password" ? "text" : "password";
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
      els.listaAlertas.insertAdjacentHTML("afterbegin", `<div class="msg error">${e.message}</div>`);
    }
  });

  function updateOnline() {
    const on = navigator.onLine;
    els.onlineStatus.classList.toggle("is-offline", !on);
    els.onlineStatus.lastChild.textContent = on ? " Online" : " Offline";
  }
  window.addEventListener("online", updateOnline);
  window.addEventListener("offline", updateOnline);
  updateOnline();

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    els.btnInstalar.classList.remove("hidden");
  });

  els.btnInstalar?.addEventListener("click", async () => {
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
