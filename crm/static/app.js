"use strict";
const paths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  users:
    '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
  compass:
    '<circle cx="12" cy="12" r="9"/><path d="m16 8-2.5 5.5L8 16l2.5-5.5Z"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 6 9 7 9-7"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  settings:
    '<path d="m9 3-.5 2-2 .8-2-.6L2.8 9l1.5 1.4v2.3L2.8 14l1.7 3.8 2-.6 2 .8.5 2h5l.5-2 2-.8 2 .6 1.7-3.8-1.5-1.3v-2.3L20.7 9 19 5.2l-2 .6-2-.8-.5-2Z"/><circle cx="12" cy="11.5" r="3"/>',
  shield:
    '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  moon: '<path d="M20 13a8.5 8.5 0 0 1-9-9 8.5 8.5 0 1 0 9 9Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  home: '<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
  refresh:
    '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 6a8 8 0 0 1 14 6M18 18A8 8 0 0 1 4 12"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  arrowUp: '<path d="m7 17 10-10M7 7h10v10"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  upload: '<path d="M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  back: '<path d="m15 5-7 7 7 7"/>',
  spark:
    '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5ZM20 2v4m-2-2h4"/>',
  send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="m11 13 11-11"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  edit: '<path d="m15 4 5 5M4 20l5-1L21 7l-5-5L4 14ZM4 20h16"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  link: '<path d="m10 13 4-4m-6 7-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m2 1 2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>',
  file: '<path d="M14 2H5v20h14V7Z"/><path d="M14 2v5h5M8 12h8M8 16h6"/>',
  pin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  building: '<path d="M4 21V3h12v18M16 9h4v12M8 7h4M8 11h4M8 15h4M2 21h20"/>',
  heart: '<path d="M12 21 3.5 12a5.5 5.5 0 0 1 8.5-7 5.5 5.5 0 0 1 8.5 7Z"/>',
  tool: '<path d="m14 7 3 3 4-4a7 7 0 0 1-9 9l-7 7-3-3 7-7a7 7 0 0 1 9-9Z"/>',
  trophy:
    '<path d="M7 3h10v8a5 5 0 0 1-10 0ZM7 5H3v3a4 4 0 0 0 4 4m10-7h4v3a4 4 0 0 1-4 4M12 16v5m-4 0h8"/>',
  pause: '<path d="M8 5v14M16 5v14"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  logout: '<path d="M9 3H4v18h5m5-5 5-4-5-4m-5 4h12"/>',
};
const icon = (name) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.building}</svg>`;
const $ = (s) => document.querySelector(s);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const statusNames = {
  novo: "Novo",
  em_cadencia: "Em cadência",
  respondeu: "Respondeu",
  negociacao: "Em negociação",
  ganho: "Convertido",
  pausado: "Pausado",
  sem_interesse: "Sem interesse",
  arquivado: "Arquivado",
};
const titles = {
  overview: "Visão geral",
  leads: "Meus leads",
  capture: "Encontrar empresas",
  campaign: "Campanha & cadência",
  activity: "Atividades",
  settings: "Configurações",
};
const state = {
  view: "overview",
  dashboard: null,
  settings: null,
  leads: [],
  total: 0,
  page: 1,
  query: "",
  status: "",
  selected: new Set(),
  campaign: null,
  tab: 0,
  attachments: [],
  capture: null,
  busy: false,
};
let toastTimer,
  searchTimer,
  renderId = 0;

async function api(path, options = {}) {
  if (options.body && !(options.body instanceof FormData)) {
    options.body = JSON.stringify(options.body);
    options.headers = {
      ...options.headers,
      "Content-Type": "application/json",
    };
  }
  const r = await fetch(path, options);
  if (r.status === 401) {
    location.href = "/login";
    throw new Error("Sessão encerrada");
  }
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Revise os campos preenchidos.",
    );
  return data;
}
function toast(message, error = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("error", error);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(
    () => {
      el.hidden = true;
    },
    error ? 14000 : 7000,
  );
}
function hydrateIcons() {
  document.querySelectorAll("[data-icon]").forEach((el) => {
    el.innerHTML = icon(el.dataset.icon);
  });
}
function pill(status) {
  return `<span class="pill ${esc(status)}">${esc(statusNames[status] || status)}</span>`;
}
function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}
function date(value) {
  return value
    ? new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "America/Sao_Paulo",
      }).format(new Date(value))
    : "Ainda não sincronizada";
}
function num(n) {
  return new Intl.NumberFormat("pt-BR").format(n || 0);
}
function progress(value, max, blue = false) {
  return `<div class="progress-track ${blue ? "blue" : ""}"><span data-progress="${Math.min(100, max ? Math.round((value / max) * 100) : 0)}"></span></div>`;
}
function applyProgress() {
  document.querySelectorAll("[data-progress]").forEach((e) => {
    e.style.setProperty("--progress", `${e.dataset.progress}%`);
  });
}
function heading(eyebrow, title, subtitle, actions = "") {
  return `<div class="page-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p>${subtitle}</p></div><div class="heading-actions">${actions}</div></div>`;
}
function empty(title, description, action = "", compact = false) {
  return `<div class="empty-state ${compact ? "compact" : ""}"><div class="empty-illustration">${icon("compass")}</div><h3>${title}</h3><p>${description}</p>${action}</div>`;
}
function captureButton() {
  return `<a class="button primary" href="#capture">${icon("compass")} Encontrar empresas</a>`;
}
function activityItems(items, all = false) {
  return items.length
    ? items
        .map(
          (a) =>
            `<div class="activity-mini"><span class="activity-dot">${icon({ envio: "send", resposta: "mail", captacao: "compass", erro: "shield", campanha: "spark" }[a.kind] || "clock")}</span><div><p>${esc(a.detail)}</p><small>${date(a.created_at)}</small></div></div>`,
        )
        .join("")
    : empty(
        "Tudo pronto para começar",
        "Suas captações, envios e respostas aparecerão aqui.",
        "",
        !all,
      );
}
function quotaPanel(d) {
  const c = d.campaign;
  return `<section class="panel"><div class="panel-header"><div><h2>Seu ritmo, sem excessos</h2><p>Limites compartilhados por toda a operação.</p></div>${icon("shield")}</div><div class="panel-body"><div class="quota-row"><span>Primeiros contatos</span><strong>${d.daily.initial} <span>/ ${c.daily_initial}</span></strong></div>${progress(d.daily.initial, c.daily_initial)}<div class="quota-row"><span>Follow-ups</span><strong>${d.daily.followup} <span>/ ${c.daily_followup}</span></strong></div>${progress(d.daily.followup, c.daily_followup, true)}<div class="quota-row"><span>Capacidade diária</span><strong>${d.daily.total} / ${c.daily_total} emails</strong></div></div><div class="subtle-note">${icon("clock")} Reservas e envios incertos também consomem a cota.</div></section>`;
}
function schedulePanel(c) {
  return `<section class="panel schedule-card"><div class="panel-header"><h2>Sua operação no automático</h2>${icon("spark")}</div><div class="panel-body"><div class="schedule-time">09:00 <span class="schedule-caption">— 10:00</span></div><p class="schedule-caption">Todos os dias · Horário de Brasília</p><div class="schedule-divider"></div><div class="schedule-status"><span>Automação diária</span><span class="pill">${c.enabled ? "Habilitada" : "Pausada"}</span></div></div></section>`;
}
function metrics(d) {
  return `<div class="metrics">${[
    [
      "Empresas na sua base",
      num(d.total),
      "users",
      "Sem duplicar oportunidades",
    ],
    [
      "Em cadência",
      num(d.counts.em_cadencia),
      "send",
      "Acompanhamento em andamento",
    ],
    [
      "Emails enviados hoje",
      num(d.sent_today),
      "mail",
      `${d.campaign.daily_total - d.daily.total} reservas disponíveis hoje`,
    ],
    [
      "Taxa de resposta",
      `${d.reply_rate.toLocaleString("pt-BR")}%`,
      "arrowUp",
      "Respostas ÷ leads na base",
    ],
  ]
    .map(
      ([label, value, i, note]) =>
        `<section class="metric"><div class="metric-top"><span>${label}</span><span class="metric-icon">${icon(i)}</span></div><div class="metric-number">${value}</div><div class="metric-note">${icon(i === "arrowUp" ? "arrowUp" : "check")} ${note}</div></section>`,
    )
    .join("")}</div>`;
}
function funnel(d) {
  const vals = [
    d.counts.novo || 0,
    d.counts.em_cadencia || 0,
    (d.counts.respondeu || 0) + (d.counts.negociacao || 0),
    d.counts.ganho || 0,
  ];
  return `<section class="panel"><div class="panel-header"><div><h2>De oportunidade a conexão</h2><p>Um olhar sobre o seu funil de prospecção.</p></div><a href="#leads" class="text-button">Ver leads ${icon("arrow")}</a></div><div class="panel-body"><div class="funnel"><div class="funnel-new"></div><div class="funnel-cadence"></div><div class="funnel-reply"></div><div class="funnel-won"></div></div><div class="funnel-stats">${["Novos leads", "Em cadência", "Em conversa", "Convertidos"].map((n, i) => `<div class="funnel-stat"><span class="funnel-stat-label">${n}</span><strong>${num(vals[i])}</strong><small>${d.total ? Math.round((vals[i] / d.total) * 100) : 0}% da sua base</small></div>`).join("")}</div></div><div class="subtle-note">${icon("shield")} Respondeu? A sequência de emails é interrompida.</div></section>`;
}
function tableRows(rows, overview = false) {
  return rows
    .map(
      (l) =>
        `<tr><td><input type="checkbox" data-select="${l.id}" ${state.selected.has(l.id) ? "checked" : ""} aria-label="Selecionar ${esc(l.name)}"></td><td><div class="company-cell"><span class="company-avatar">${esc(initials(l.name))}</span><div><span class="company-name">${esc(l.name)}</span><span class="company-sub">${esc(l.niche || "Nicho não informado")} · ${esc(l.city || "Cidade não informada")}</span></div></div></td><td><div class="contact-cell">${l.email ? `<a href="mailto:${esc(l.email)}">${esc(l.email)}</a>` : '<span class="no-email">Email não informado</span>'}<small>${l.phone ? `<a href="https://wa.me/${esc(l.phone)}" target="_blank" rel="noopener noreferrer" title="Abrir conversa; não envia automaticamente">+${esc(l.phone)}</a>` : "Telefone não informado"}</small></div></td><td><span class="review-chip"><span class="star">★</span>${esc(l.rating || "—")} <small>(${num(l.reviews)})</small></span></td><td>${pill(l.status)}</td><td><div class="cadence-dots">${[0, 1, 2, 3].map((i) => `<span class="${l.stage >= i ? "done" : ""}"></span>`).join("")}<small>${l.stage < 0 ? "Não iniciada" : l.stage === 0 ? "Inicial" : `F${l.stage}`}</small></div></td><td><button class="icon-button" data-action="edit-lead" data-id="${l.id}" aria-label="Editar ${esc(l.name)}" title="Editar lead">${icon("edit")}</button>${!overview ? `<button class="icon-button" data-action="delete-one" data-id="${l.id}" aria-label="Excluir ${esc(l.name)}" title="Excluir lead">${icon("trash")}</button>` : ""}</td></tr>`,
    )
    .join("");
}
function table(overview = false) {
  const rows = overview ? state.leads.slice(0, 5) : state.leads;
  const d = state.dashboard;
  return `<section class="panel table-panel"><div class="panel-header"><div><h2>${overview ? "Suas próximas oportunidades" : "Uma base organizada. Mais oportunidades."}</h2><p>${overview ? "Empresas para começar uma boa conversa." : "Gerencie contatos, acompanhe o interesse e mantenha o foco."}</p></div>${overview ? '<a href="#leads" class="text-button">Ver todos ' + icon("arrow") + "</a>" : `<button class="button secondary small-button" data-action="import">${icon("upload")} Importar CSV</button>`}</div><div class="table-controls"><div class="filter-tabs">${[
    ["", "Todos", d.total],
    ["novo", "Novos", d.counts.novo || 0],
    ["em_cadencia", "Em cadência", d.counts.em_cadencia || 0],
    ["respondeu", "Respostas", d.counts.respondeu || 0],
  ]
    .map(
      ([v, n, c]) =>
        `<button class="filter-tab ${state.status === v ? "active" : ""}" data-action="filter" data-status="${v}">${n}<span>${num(c)}</span></button>`,
    )
    .join(
      "",
    )}</div><label class="search-field">${icon("search")}<input id="lead-search" type="search" placeholder="Buscar empresa, email ou cidade…" aria-label="Buscar leads" value="${esc(state.query)}"></label></div><div class="bulk-bar" ${state.selected.size ? "" : "hidden"}><strong>${state.selected.size} selecionado(s)</strong><select id="bulk-status" aria-label="Novo status">${Object.entries(
    statusNames,
  )
    .map(([v, n]) => `<option value="${v}">${n}</option>`)
    .join(
      "",
    )}</select><button class="button secondary small-button" data-action="bulk-status">Atualizar status</button><button class="button secondary small-button" data-action="bulk-delete">${icon("trash")} Excluir</button><button class="button primary small-button" data-action="send">${icon("send")} Enviar emails</button></div><div class="table-scroll ${rows.length ? "" : "is-empty"}"><table><thead><tr><th><input type="checkbox" id="select-all" aria-label="Selecionar todos desta página" ${rows.length && rows.every((l) => state.selected.has(l.id)) ? "checked" : ""}></th><th>EMPRESA</th><th>CONTATO</th><th>GOOGLE</th><th>STATUS</th><th>CADÊNCIA</th><th></th></tr></thead><tbody>${rows.length ? tableRows(rows, overview) : `<tr><td colspan="7">${empty(state.total ? "Nenhum lead com esse filtro" : "Seu próximo cliente está por aí", state.total ? "Tente outro status ou termo de busca." : "Encontre empresas brasileiras com potencial ou adicione seus próprios contatos.", state.total ? '<button class="button secondary" data-action="clear-filters">Limpar filtros</button>' : captureButton())}</td></tr>`}</tbody></table></div><div class="table-footer"><span>${state.total ? `${(state.page - 1) * 25 + 1}–${(state.page - 1) * 25 + rows.length} de ${num(state.total)} empresas` : "Sua base começa com uma boa oportunidade."}</span>${overview ? "<span>Sem website · Brasil</span>" : `<div class="pagination"><button class="icon-button" data-action="prev" ${state.page <= 1 ? "disabled" : ""} aria-label="Página anterior">${icon("back")}</button><span>Página ${state.page}</span><button class="icon-button" data-action="next" ${state.page * 25 >= state.total ? "disabled" : ""} aria-label="Próxima página">${icon("chevron")}</button></div>`}</div></section>`;
}
function overviewView() {
  const d = state.dashboard;
  return (
    heading(
      "SEU RADAR DE OPORTUNIDADES",
      "Pequenas empresas. Grandes possibilidades.",
      "Conecte-se com quem está pronto para dar o próximo passo no digital.",
      `<button class="button secondary" data-action="new-lead">${icon("plus")} Adicionar lead</button>${captureButton()}`,
    ) +
    metrics(d) +
    `<div class="split-content">${funnel(d)}${schedulePanel(d.campaign)}</div>` +
    table(true) +
    `<div class="bottom-grid">${quotaPanel(d)}<section class="panel"><div class="panel-header"><h2>Aconteceu por aqui</h2><a class="text-button" href="#activity">Ver atividades ${icon("arrow")}</a></div><div class="panel-body">${activityItems(d.activity.slice(0, 2))}</div></section></div>`
  );
}
function leadsView() {
  return (
    heading(
      "RELACIONAMENTOS QUE CRESCEM",
      "Cada lead, uma possibilidade.",
      "Seus contatos, histórico e próximos passos em um só lugar.",
      `<a class="button secondary" href="/api/export">${icon("download")} Exportar CSV</a><button class="button primary" data-action="new-lead">${icon("plus")} Adicionar lead</button>`,
    ) + table()
  );
}
function captureView() {
  const niches = state.settings.niches,
    nicheIcons = ["heart", "tool", "spark", "heart", "building", "trophy"];
  return (
    heading(
      "ENCONTRE SEU PRÓXIMO CLIENTE",
      "Boas oportunidades estão perto.",
      "Empresas brasileiras bem avaliadas, ainda sem um website próprio.",
    ) +
    `<div class="capture-layout"><div><section class="panel"><div class="panel-header"><div><h2>Onde vamos encontrar oportunidades?</h2><p>Escolha uma região e um segmento para começar.</p></div>${icon("compass")}</div><div class="panel-body"><form id="capture-form" class="capture-form"><label>Cidade / UF<input name="city" placeholder="Ex.: Campinas, SP" required minlength="2" maxlength="120"></label><label>Nicho de atuação<input name="niche" id="capture-niche" list="niche-list" placeholder="Ex.: Clínicas odontológicas" required minlength="2" maxlength="120"></label><label>Resultados a consultar<select name="limit"><option value="25">Até 25 empresas</option><option value="50" selected>Até 50 empresas</option><option value="100">Até 100 empresas</option></select><small>A fonte pode cobrar por consulta, inclusive resultados fora do perfil.</small></label><div></div><button class="button primary" type="submit">${icon("search")} Buscar empresas</button><button class="button secondary" type="button" data-action="poll-capture">${icon("refresh")} Atualizar resultado</button></form><div id="capture-result" class="capture-result">${captureResult()}</div></div></section><p class="section-label">Nichos sugeridos · Serviços com presença local</p><div class="niche-grid">${niches.map((n, i) => `<button class="niche-card" data-action="choose-niche" data-niche="${esc(n)}">${icon(nicheIcons[i])}<strong>${esc(n)}</strong><small>Contato local · Serviços recorrentes</small></button>`).join("")}</div><div class="notice">${icon("mail")}<div><strong>Contatos reais, sem adivinhações.</strong><p>Telefone, email e redes sociais são preenchidos apenas quando disponíveis na fonte. Empresas sem email ficam na base para enriquecimento manual e não recebem disparos. Nichos sugeridos não representam garantia de conversão.</p></div></div></div><aside><section class="panel"><div class="panel-header"><h2>O perfil que buscamos</h2></div><div class="panel-body"><ul class="criteria">${["Empresas no Brasil", "Sem website informado", "De 50 a 400 avaliações", "Negócios em atividade", "Sem repetir leads já captados"].map((t) => `<li>${icon("check")}${t}</li>`).join("")}</ul></div><div class="subtle-note">${icon("shield")} Deduplicação por Google ID, email e telefone.</div></section><div class="notice warn side-notice">${icon("link")}<div><strong>${state.settings.variables.CRM_APIFY_TOKEN ? "Fonte configurada" : "Conecte sua fonte de leads"}</strong><p>${state.settings.variables.CRM_APIFY_TOKEN ? "Apify configurado no servidor. A primeira consulta verificará o acesso." : "Configure CRM_APIFY_TOKEN no Render para consultar o Google Maps via Apify."}</p><a href="#settings" class="text-button">Ver configuração ${icon("arrow")}</a></div></div></aside></div>`
  );
}
function captureResult() {
  const c = state.capture;
  if (!c)
    return "Ainda não há uma captação nesta sessão. Você também pode atualizar uma busca iniciada anteriormente.";
  if (c.status === "SUCCEEDED")
    return `${icon("check")} Captação concluída: <strong>${c.added} novos leads</strong>, ${c.duplicates} duplicados e ${c.rejected} resultados fora do perfil ou inválidos. <a href="#leads" class="text-button">Ver leads →</a>`;
  return `Status: <strong>${esc(c.status)}</strong>${c.city ? ` · ${esc(c.niche)} em ${esc(c.city)}` : ""}. ${["RUNNING", "READY"].includes(c.status) ? "Aguarde a fonte concluir e atualize o resultado." : ""}`;
}
function campaignView() {
  const c = state.campaign;
  return (
    heading(
      "CONVERSAS COM PROPÓSITO",
      "Uma proposta. Uma boa primeira impressão.",
      "Personalize sua campanha e acompanhe cada contato com cuidado.",
      `<button class="button secondary" data-action="preview">${icon("eye")} Prévia salva</button><button class="button primary" data-action="save-campaign">${icon("check")} Salvar campanha</button>`,
    ) +
    `<div class="notice ${c.enabled ? "" : "warn"}">${icon(c.enabled ? "send" : "pause")}<div><strong>${c.enabled ? "Campanha habilitada" : "Você está no controle. Os envios estão pausados."}</strong><p>Somente campanhas revisadas, habilitadas e dentro da validade podem enviar. Respostas interrompem a sequência; o follow-up 3 encerra a cadência.</p></div></div><div class="campaign-layout"><div><section class="panel campaign-editor"><div class="panel-header"><div><h2>Seu texto, sua voz.</h2><p>Uma mensagem inicial e três retomadas.</p></div><span class="pill active">Oferta R$ 700</span></div><div class="filter-tabs">${["Primeiro contato", "Follow-up 1", "Follow-up 2", "Follow-up 3"].map((n, i) => `<button class="filter-tab ${state.tab === i ? "active" : ""}" data-action="template-tab" data-tab="${i}">${n}</button>`).join("")}</div><div class="panel-body"><label>Assunto<input id="template-subject" maxlength="200" value="${esc(c.templates[state.tab].subject)}"></label><label>Mensagem<textarea id="template-body" class="template-body" maxlength="15000">${esc(c.templates[state.tab].body)}</textarea></label><div class="variables"><span class="variable">{empresa}</span><span class="variable">{cidade}</span><span class="variable">{validade}</span><small class="muted">Preenchidos para cada lead</small></div><p class="field-note">A assinatura e a opção de interromper contatos são incluídas automaticamente. O texto inicial compara faixas de R$ 2.500–3.000 conforme o escopo; revise essa comparação antes de aprovar.</p></div></section><section class="panel campaign-details"><div class="panel-header"><div><h2>Detalhes da campanha</h2><p>A oferta tem validade real de até sete dias.</p></div></div><div class="panel-body"><div class="campaign-meta"><label>Nome da campanha<input id="campaign-name" value="${esc(c.name)}" maxlength="120"></label><label>Nome do remetente<input id="sender-name" value="${esc(c.sender_name)}" maxlength="80"></label><label>Email remetente<input id="campaign-sender" type="email" value="${esc(c.sender)}"></label><label>Link da proposta (opcional)<input id="cta-url" type="url" value="${esc(c.cta_url)}" placeholder="https://…"></label><label>Início da oferta<input type="date" id="start-date" value="${esc(c.start_date)}"></label><label>Último dia da oferta<input type="date" id="end-date" value="${esc(c.end_date)}"></label>${c.intervals.map((v, i) => `<label>Intervalo até follow-up ${i + 1} (dias)<input type="number" id="interval-${i}" min="1" max="30" value="${v}"></label>`).join("")}</div><label class="checkbox-label"><input type="checkbox" id="campaign-approved" ${c.approved ? "checked" : ""}>Revisei os quatro textos, o escopo da oferta e a validade da campanha.</label><label class="checkbox-label"><input type="checkbox" id="campaign-enabled" ${c.enabled ? "checked" : ""}>Habilitar envios manuais e automáticos desta campanha.</label><p class="field-note">Se a validade terminar antes de um follow-up, o envio não acontece. Ajuste a cadência ou revise uma nova campanha; a oferta não é renovada automaticamente.</p></div></section><section class="panel preview-panel" id="preview-panel" hidden><div class="panel-header"><h2>Prévia da versão salva</h2><button class="icon-button" data-action="close-preview" aria-label="Fechar prévia">×</button></div><div id="preview-subject" class="preview-subject"></div><iframe id="email-preview" class="email-preview" title="Prévia do email salvo" sandbox=""></iframe></section></div><aside class="campaign-side">${schedulePanel(c)}<section class="panel"><div class="panel-header"><h2>A jornada do contato</h2></div><div class="panel-body">${["Primeiro contato", "Follow-up 1", "Follow-up 2", "Follow-up 3"].map((n, i) => `<div class="sequence-step"><span class="sequence-number">${i === 0 ? icon("mail") : i}</span><div><strong>${n}</strong><small>${i === 0 ? "Ao selecionar e enviar o lead" : `${c.intervals[i - 1]} dias após a mensagem anterior`}${i === 3 ? " · Encerra a sequência" : ""}</small></div></div>`).join("")}</div><div class="subtle-note">${icon("shield")} Caixa de entrada verificada antes dos envios.</div></section><section class="panel"><div class="panel-header"><h2>Imagens & arquivos</h2>${icon("file")}</div><div class="panel-body"><div id="attachment-list">${attachmentsHtml()}</div><label class="file-label">${icon("upload")}Adicionar anexo (até 5 MB)<input type="file" id="attachment-input" accept=".png,.jpg,.jpeg,.webp,.pdf,.txt,.zip,.docx,.xlsx"></label><label class="checkbox-label"><input id="inline-image" type="checkbox">Exibir imagem no corpo do email</label><p class="field-note">Até 5 arquivos, 10 MB no total. Os anexos são usados nas quatro mensagens da campanha.</p></div></section>${quotaPanel(state.dashboard)}</aside></div>`
  );
}
function attachmentsHtml() {
  return state.attachments.length
    ? state.attachments
        .map(
          (a) =>
            `<div class="attachment-row">${icon("file")}<span>${esc(a.name)}<small>${(a.size / 1024).toFixed(0)} KB${a.inline ? " · No corpo do email" : ""}</small></span><button class="icon-button" data-action="remove-attachment" data-id="${a.id}" aria-label="Remover ${esc(a.name)}">${icon("trash")}</button></div>`,
        )
        .join("")
    : '<p class="field-note">Uma proposta visual também abre portas. Adicione materiais, se desejar.</p>';
}
function settingsView() {
  const s = state.settings;
  const hasGmail = [
    "CRM_GMAIL_CLIENT_ID",
    "CRM_GMAIL_CLIENT_SECRET",
    "CRM_GMAIL_REFRESH_TOKEN",
  ].every((k) => s.variables[k]);
  return (
    heading(
      "CADA COISA EM SEU LUGAR",
      "Sua operação, bem conectada.",
      "Credenciais ficam no servidor. Seu painel mostra apenas o estado da configuração.",
    ) +
    `<div class="settings-grid"><section class="panel"><div class="panel-header"><h2>Conexões da operação</h2>${icon("link")}</div><div class="panel-body">${[
      ["Banco de dados", s.database, s.database === "PostgreSQL"],
      ["Gmail", state.dashboard.campaign.sender, hasGmail],
      ["Captação · Apify", "Google Maps · Brasil", s.variables.CRM_APIFY_TOKEN],
      [
        "Automação",
        "GitHub Actions · 09h de Brasília",
        s.variables.CRM_WORKER_TOKEN,
      ],
    ]
      .map(
        ([name, sub, ok]) =>
          `<div class="connection-row"><div><strong>${name}</strong><small>${esc(sub)}</small></div><span class="pill ${ok ? "active" : "pausado"}">${ok ? "Configurado" : "Pendente"}</span></div>`,
      )
      .join(
        "",
      )}<p class="field-note">Configurado indica presença da variável. As operações validam acesso e permissões no provedor.</p></div></section><section class="panel"><div class="panel-header"><h2>Caixa de entrada</h2>${icon("mail")}</div><div class="panel-body"><p class="settings-guide">Qualquer resposta detectada bloqueia novos follow-ups para o contato. Pedidos de remoção também podem ser marcados como “Sem interesse” na base.</p><div class="connection-row"><div><strong>Última sincronização</strong><small>${date(state.dashboard.last_sync)}</small></div></div><button class="button secondary" data-action="sync-inbox">${icon("refresh")} Sincronizar respostas</button></div></section><section class="panel"><div class="panel-header"><h2>Publicar em outra conta</h2>${icon("building")}</div><div class="panel-body settings-guide"><ol><li>Crie um projeto Supabase exclusivo e execute <code>supabase/schema.sql</code> no SQL Editor.</li><li>No Render, use o <code>render.yaml</code> deste repositório e configure <code>CRM_DATABASE_URL</code> com a conexão PostgreSQL do novo projeto.</li><li>Conecte o Gmail por OAuth e adicione as credenciais e o token do Apify nas variáveis do Render.</li><li>No GitHub, habilite Actions e configure os secrets <code>CRM_BASE_URL</code> e <code>CRM_WORKER_TOKEN</code>.</li><li>Personalize e revise os quatro emails antes de habilitar a campanha.</li></ol><a class="text-button" href="https://github.com/carloshenriquemartinssena-hub/hello/blob/main/README.md" target="_blank" rel="noopener noreferrer">Documentação de implantação ${icon("arrowUp")}</a><p>Os arquivos precisam ser enviados ao GitHub para aparecerem no link.</p></div></section><section class="panel"><div class="panel-header"><h2>Variáveis do servidor</h2>${icon("shield")}</div><div class="panel-body">${Object.entries(
      s.variables,
    )
      .map(
        ([k, v]) =>
          `<div class="connection-row"><small>${esc(k)}</small><span class="pill ${v ? "active" : "pausado"}">${v ? "Definida" : "Ausente"}</span></div>`,
      )
      .join("")}</div></section></div>`
  );
}

async function loadLeads() {
  const p = new URLSearchParams({
    q: state.query,
    status: state.status,
    page: String(state.page),
  });
  const d = await api("/api/leads?" + p);
  state.leads = d.items;
  state.total = d.total;
}
async function render() {
  const id = ++renderId;
  state.view =
    location.hash.slice(1) in titles ? location.hash.slice(1) : "overview";
  $("#breadcrumb").textContent = titles[state.view];
  document.title = `${titles[state.view]} · Vértice CRM`;
  document
    .querySelectorAll("[data-nav]")
    .forEach((e) => e.classList.toggle("active", e.dataset.nav === state.view));
  $("#sidebar").classList.remove("open");
  try {
    [state.dashboard, state.settings] = await Promise.all([
      api("/api/dashboard"),
      api("/api/settings"),
    ]);
    if (["overview", "leads"].includes(state.view)) await loadLeads();
    if (state.view === "campaign")
      [state.campaign, state.attachments] = await Promise.all([
        api("/api/campaign"),
        api("/api/attachments"),
      ]);
    const activities =
      state.view === "activity" ? await api("/api/activity") : null;
    if (id !== renderId) return;
    $("#nav-count").textContent = num(state.dashboard.total);
    $("#niche-list").innerHTML = state.settings.niches
      .map((n) => `<option value="${esc(n)}"></option>`)
      .join("");
    const views = {
      overview: overviewView,
      leads: leadsView,
      capture: captureView,
      campaign: campaignView,
      settings: settingsView,
      activity: () =>
        heading(
          "LEMBRAR PARA EVOLUIR",
          "O histórico das suas conexões.",
          "Captações, mensagens, respostas e mudanças na sua base.",
        ) +
        `<section class="panel activity-list">${activityItems(activities, true)}</section>`,
    };
    $("#main").innerHTML = views[state.view]();
    hydrateIcons();
    applyProgress();
  } catch (e) {
    $("#main").innerHTML = empty(
      "Não conseguimos carregar os dados",
      esc(e.message),
      '<button class="button primary" data-action="refresh">Tentar novamente</button>',
    );
    toast(e.message, true);
  }
}
function updateTemplate() {
  if ($("#template-subject")) {
    state.campaign.templates[state.tab] = {
      subject: $("#template-subject").value,
      body: $("#template-body").value,
    };
  }
}
function readCampaign() {
  updateTemplate();
  const c = state.campaign;
  c.name = $("#campaign-name").value;
  c.sender_name = $("#sender-name").value;
  c.sender = $("#campaign-sender").value;
  c.cta_url = $("#cta-url").value;
  c.start_date = $("#start-date").value;
  c.end_date = $("#end-date").value;
  c.approved = $("#campaign-approved").checked;
  c.enabled = $("#campaign-enabled").checked;
  c.intervals = [0, 1, 2].map((i) => Number($("#interval-" + i).value));
  return c;
}
function showLead(id) {
  const l = id ? state.leads.find((x) => x.id === Number(id)) : null;
  const f = $("#lead-form");
  f.reset();
  f.elements.id.value = l?.id || "";
  for (const key of [
    "name",
    "email",
    "phone",
    "city",
    "niche",
    "reviews",
    "rating",
    "instagram",
    "facebook",
    "source_url",
    "notes",
  ])
    f.elements[key].value = l?.[key] ?? (key === "reviews" ? 0 : "");
  $("#lead-dialog-title").textContent = l ? "Editar lead" : "Adicionar lead";
  $("#lead-error").textContent = "";
  $("#lead-dialog").showModal();
}
function confirmAction(title, message, callback) {
  $("#confirm-title").textContent = title;
  $("#confirm-message").textContent = message;
  $("#confirm-dialog").showModal();
  $("#confirm-button").onclick = async () => {
    $("#confirm-dialog").close();
    await run(callback);
  };
}
async function run(fn) {
  if (state.busy) return;
  state.busy = true;
  document.body.setAttribute("aria-busy", "true");
  const buttons = [...document.querySelectorAll("button:not(:disabled)")];
  buttons.forEach((b) => (b.disabled = true));
  try {
    await fn();
  } catch (e) {
    toast(e.message, true);
  } finally {
    state.busy = false;
    buttons.forEach((b) => (b.disabled = false));
    document.body.removeAttribute("aria-busy");
  }
}
async function bulkAction(action, status = "", ids = [...state.selected]) {
  const r = await api("/api/leads/bulk", {
    method: "POST",
    body: { ids, action, status },
  });
  state.selected.clear();
  toast(`${r.updated} lead(s) atualizado(s).`);
  await render();
}

document.addEventListener("click", async (event) => {
  const b = event.target.closest("[data-action]");
  if (!b) return;
  const action = b.dataset.action;
  if (action === "menu") {
    $("#sidebar").classList.toggle("open");
    return;
  }
  if (action === "close-dialog") {
    $("#lead-dialog").close();
    return;
  }
  if (action === "close-confirm") {
    $("#confirm-dialog").close();
    return;
  }
  if (action === "new-lead") {
    showLead();
    return;
  }
  if (action === "edit-lead") {
    showLead(b.dataset.id);
    return;
  }
  if (action === "import") {
    $("#csv-input").click();
    return;
  }
  if (action === "filter") {
    state.status = b.dataset.status;
    state.page = 1;
    state.selected.clear();
    await render();
    return;
  }
  if (action === "clear-filters") {
    state.status = "";
    state.query = "";
    state.page = 1;
    await render();
    return;
  }
  if (action === "prev" || action === "next") {
    state.page += action === "next" ? 1 : -1;
    state.selected.clear();
    await render();
    return;
  }
  if (action === "bulk-delete" || action === "delete-one") {
    const ids =
      action === "delete-one" ? [Number(b.dataset.id)] : [...state.selected];
    confirmAction(
      "Excluir leads?",
      `${ids.length} lead(s) serão removidos da base visível. O histórico e o bloqueio de recaptura serão mantidos.`,
      () => bulkAction("delete", "", ids),
    );
    return;
  }
  if (action === "send") {
    const ids = [...state.selected];
    confirmAction(
      "Enviar emails aos leads selecionados?",
      `O sistema enviará mensagens reais apenas aos contatos elegíveis, respeitando os limites de 30 novos e 30 follow-ups por dia. A campanha precisa estar revisada e habilitada. ${ids.length} lead(s) selecionado(s).`,
      async () => {
        const r = await api("/api/send", { method: "POST", body: { ids } });
        toast(`${r.sent} email(s) enviado(s). ${r.reason}`);
        state.selected.clear();
        await render();
      },
    );
    return;
  }
  if (action === "choose-niche") {
    $("#capture-niche").value = b.dataset.niche;
    document
      .querySelectorAll(".niche-card")
      .forEach((e) => e.classList.toggle("selected", e === b));
    $("#capture-form input[name=city]").focus();
    return;
  }
  if (action === "template-tab") {
    readCampaign();
    state.tab = Number(b.dataset.tab);
    $("#main").innerHTML = campaignView();
    hydrateIcons();
    applyProgress();
    return;
  }
  if (action === "close-preview") {
    $("#preview-panel").hidden = true;
    return;
  }
  await run(async () => {
    if (action === "refresh") await render();
    if (action === "bulk-status")
      await bulkAction("status", $("#bulk-status").value);
    if (action === "save-campaign") {
      await api("/api/campaign", { method: "PUT", body: readCampaign() });
      toast("Campanha salva.");
      await render();
    }
    if (action === "preview") {
      const p = await api("/api/preview/" + state.tab);
      $("#preview-subject").textContent = "Assunto: " + p.subject;
      $("#email-preview").src = "/api/preview/" + state.tab + "/document";
      $("#preview-panel").hidden = false;
      $("#preview-panel").scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
    if (action === "poll-capture") {
      state.capture = await api("/api/capture/poll", { method: "POST" });
      $("#capture-result").innerHTML = captureResult();
      toast("Resultado atualizado.");
    }
    if (action === "remove-attachment") {
      await api("/api/attachments/" + b.dataset.id, { method: "DELETE" });
      state.attachments = await api("/api/attachments");
      $("#attachment-list").innerHTML = attachmentsHtml();
    }
    if (action === "sync-inbox") {
      const r = await api("/api/inbox/sync", { method: "POST" });
      toast(`${r.replies} resposta(s) detectada(s).`);
      await render();
    }
    if (action === "logout") {
      await api("/api/logout", { method: "POST" });
      location.href = "/login";
    }
  });
});
document.addEventListener("change", (event) => {
  const e = event.target;
  if (e.matches("[data-select]")) {
    const id = Number(e.dataset.select);
    e.checked ? state.selected.add(id) : state.selected.delete(id);
    const p = $(".table-panel");
    p.outerHTML = table(state.view === "overview");
  }
  if (e.id === "select-all") {
    const rows =
      state.view === "overview" ? state.leads.slice(0, 5) : state.leads;
    rows.forEach((l) =>
      e.checked ? state.selected.add(l.id) : state.selected.delete(l.id),
    );
    $(".table-panel").outerHTML = table(state.view === "overview");
  }
  if (e.id === "csv-input" && e.files.length)
    run(async () => {
      const form = new FormData();
      form.append("file", e.files[0]);
      const r = await api("/api/import", { method: "POST", body: form });
      toast(
        `${r.added} adicionado(s), ${r.duplicates} duplicado(s), ${r.errors.length} inválido(s).${
          r.errors.length
            ? " Revise as linhas: " +
              r.errors
                .slice(0, 8)
                .map((x) => x.line)
                .join(", ")
            : ""
        }`,
        r.errors.length > 0,
      );
      e.value = "";
      await render();
    });
  if (e.id === "attachment-input" && e.files.length)
    run(async () => {
      const form = new FormData();
      form.append("file", e.files[0]);
      await api("/api/attachments?inline=" + $("#inline-image").checked, {
        method: "POST",
        body: form,
      });
      state.attachments = await api("/api/attachments");
      $("#attachment-list").innerHTML = attachmentsHtml();
      e.value = "";
      toast("Arquivo adicionado à campanha.");
    });
});
document.addEventListener("input", (event) => {
  if (event.target.id === "lead-search") {
    state.query = event.target.value;
    state.page = 1;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
      try {
        await loadLeads();
        $(".table-panel").outerHTML = table(state.view === "overview");
        const input = $("#lead-search");
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      } catch (e) {
        toast(e.message, true);
      }
    }, 300);
  }
});
document.addEventListener("submit", (event) => {
  if (event.target.matches("#lead-form")) {
    event.preventDefault();
    run(async () => {
      const f = event.target;
      const data = Object.fromEntries(new FormData(f));
      const id = data.id;
      delete data.id;
      data.reviews = Number(data.reviews || 0);
      const old = state.leads.find((l) => l.id === Number(id));
      if (old) data.place_id = old.place_id;
      try {
        await api("/api/leads" + (id ? "/" + id : ""), {
          method: id ? "PUT" : "POST",
          body: data,
        });
        $("#lead-dialog").close();
        toast("Lead salvo.");
        await render();
      } catch (e) {
        $("#lead-error").textContent = e.message;
      }
    });
  }
  if (event.target.matches("#capture-form")) {
    event.preventDefault();
    run(async () => {
      const data = Object.fromEntries(new FormData(event.target));
      data.limit = Number(data.limit);
      state.capture = await api("/api/capture", { method: "POST", body: data });
      $("#capture-result").innerHTML = captureResult();
      toast("Busca iniciada. Aguarde e atualize o resultado.");
    });
  }
});
function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("crm2-theme", theme);
  $("#theme-label").textContent =
    theme === "dark" ? "Mudar para tema claro" : "Mudar para tema escuro";
  $("#theme-toggle [data-icon]").innerHTML = icon(
    theme === "dark" ? "sun" : "moon",
  );
}
hydrateIcons();
setTheme(localStorage.getItem("crm2-theme") || "light");
$("#theme-toggle").addEventListener("click", () =>
  setTheme(
    document.documentElement.dataset.theme === "dark" ? "light" : "dark",
  ),
);
window.addEventListener("hashchange", () => {
  state.selected.clear();
  state.status = "";
  state.query = "";
  state.page = 1;
  render();
});
render();
