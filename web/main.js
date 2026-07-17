/* Whispy Brain — HyperKanban + Notion/Obsidian hybrid, mobile-first. */

const $ = (id) => document.getElementById(id);
let TREE = [];
let CURRENT_VIEW = "tree";
let CURRENT_NODE = null;
let EDITOR_OPEN = false;
let SEARCH_DEBOUNCE = null;

const STATUSES = ["todo", "in_progress", "review", "done"];
const PRIORITIES = ["none", "low", "medium", "high", "urgent"];
const NODE_TYPES = ["workspace", "area", "board", "task", "subtask", "note"];
const STATUS_LABEL = { todo: "Todo", in_progress: "Doing", review: "Review", done: "Done" };
const PRI_LABEL = { none: "None", low: "Low", medium: "Medium", high: "High", urgent: "Urgent" };
const TYPE_LABEL = { workspace: "Workspace", area: "Area", board: "Board", task: "Task", subtask: "Subtask", note: "Note" };
const TYPE_ICON = { workspace: "🗂️", area: "📁", board: "📋", task: "✅", subtask: "▪️", note: "📝" };

/* ────────────────────────────────────────────── API helper ───── */
async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  const r = await fetch(path, opts);
  if (!r.ok) { const t = await r.text().catch(() => r.statusText); showToast(`✕ ${t}`, "error"); throw new Error(t); }
  return r.status === 204 ? null : r.json();
}

/* ────────────────────────────────────────────── Toast ───────── */
function showToast(msg, level = "info") {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast";
  t.classList.remove("hidden");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add("hidden"), 2400);
}

/* ────────────────────────────────────────────── Theme ───────── */
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  $("themeToggle").textContent = t === "dark" ? "🌙" : "☀️";
  localStorage.setItem("whispy-theme", t);
}
$("themeToggle").addEventListener("click", () => applyTheme(localStorage.getItem("whispy-theme") === "dark" ? "light" : "dark"));
applyTheme(localStorage.getItem("whispy-theme") || "dark");

/* ────────────────────────────────────────────── Nav rail ─────── */
document.querySelectorAll(".rail-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

function switchView(view) {
  CURRENT_VIEW = view;
  document.querySelectorAll(".rail-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  renderView();
  closeEditor();
}

/* ────────────────────────────────────────────── Data ────────── */
async function loadTree() {
  const data = await api("GET", "/api/tree");
  TREE = data;
  renderView();
  if (EDITOR_OPEN && CURRENT_NODE) { /* refresh editor node ref */ }
}

/* ────────────────────────────────────────────── Render dispatch */
function renderView() {
  const c = $("content");
  if (EDITOR_OPEN) return;
  if (CURRENT_VIEW === "tree") renderTree(c);
  else if (CURRENT_VIEW === "kanban") renderKanban(c);
  else if (CURRENT_VIEW === "notes") renderNotes(c);
  else if (CURRENT_VIEW === "graph") renderGraph(c);
  else if (CURRENT_VIEW === "stats") renderStats(c);
}

/* ────────────────────────────────────────────── Tree view ────── */
function findNode(nodes, id) {
  for (const n of nodes) {
    if (n.id === id) return n;
    if (n.children?.length) { const f = findNode(n.children, id); if (f) return f; }
  }
  return null;
}
function flatten(nodes, depth = 0, acc = []) {
  for (const n of nodes) { acc.push({ ...n, _depth: depth }); if (n.children?.length) flatten(n.children, depth + 1, acc); }
  return acc;
}

function renderTree(c) {
  let html = '<div class="tree">';
  for (const node of TREE) html += treeHtml(node, 0);
  html += "</div>";
  c.innerHTML = html;
  c.querySelectorAll(".tree-node").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target.classList.contains("tree-toggle")) {
        e.stopPropagation();
        el.parentElement.querySelector(":scope > .tree-children")?.classList.toggle("hidden");
        return;
      }
      openEditor(el.dataset.treeId);
    });
  });
}
function treeHtml(node, depth) {
  const hasChildren = node.children?.length > 0;
  const stClass = `st-${node.status === "in_progress" ? "doing" : node.status}`;
  const isDone = node.status === "done";
  const indent = depth * 18;
  return `<div class="tree-node" data-tree-id="${node.id}" style="margin-left:${indent}px">
    <span class="tree-toggle">${hasChildren ? "▾" : ""}</span>
    <span class="tree-label" style="${isDone ? "opacity:0.5;text-decoration:line-through" : ""}">${TYPE_ICON[node.node_type] || ""} ${escapeHtml(node.title) || "(untitled)"}</span>
    <span class="tree-status ${stClass}">${STATUS_LABEL[node.status] || node.status}</span>
  </div>${hasChildren ? `<div class="tree-children">${node.children.map((ch) => treeHtml(ch, depth + 1)).join("")}</div>` : ""}`;
}

/* ────────────────────────────────────────────── Kanban view ──── */
function renderKanban(c) {
  const flat = flatten(TREE).filter((n) => n.node_type === "task" || n.node_type === "subtask");
  const cols = { todo: [], in_progress: [], review: [], done: [] };
  for (const n of flat) (cols[n.status] || (cols[n.status] = [])).push(n);
  let html = '<div class="kanban">';
  for (const st of STATUSES) {
    html += `<div class="kanban-col"><h3>${STATUS_LABEL[st] || st} <span class="col-count">${cols[st].length}</span></h3>`;
    for (const card of cols[st]) {
      const pdot = card.priority === "medium" ? "p-med" : (card.priority === "high" || card.priority === "urgent") ? "p-high" : card.priority === "low" ? "p-low" : "p-none";
      html += `<div class="kanban-card" data-tree-id="${card.id}">
        <div class="card-title">${TYPE_ICON[card.node_type] || ""} ${escapeHtml(card.title) || "(untitled)"}</div>
        <div class="card-meta"><span class="priority-dot ${pdot}"></span>${card.due_date ? `📅 ${card.due_date.slice(0,10)}` : ""} ${(card.tags||[]).map((t)=>`#${t}`).join(" ")}</div>
      </div>`;
    }
    html += "</div>";
  }
  html += "</div>";
  c.innerHTML = html;
  c.querySelectorAll("[data-tree-id]").forEach((el) => el.addEventListener("click", () => openEditor(el.dataset.treeId)));
}

/* ────────────────────────────────────────────── Notes view ───── */
function renderNotes(c) {
  const flat = flatten(TREE).filter((n) => n.node_type === "note");
  let html = '<div class="notes-list">';
  if (!flat.length) html += '<div class="empty-state">No notes yet. Add one with + and set type to Note.</div>';
  for (const n of flat) {
    const preview = (n.body_markdown || "").replace(/[#*\[\]]/g, "").slice(0, 120);
    html += `<div class="note-card" data-tree-id="${n.id}">
      <div class="note-title">${escapeHtml(n.title) || "(untitled)"}</div>
      <div class="note-preview">${escapeHtml(preview)}</div>
      <div class="note-date">${new Date(n.updated_at * 1000).toLocaleDateString()} · ${(n.body_markdown||"").match(/\[\[/g)?.length||0} links</div>
    </div>`;
  }
  html += "</div>";
  c.innerHTML = html;
  c.querySelectorAll("[data-tree-id]").forEach((el) => el.addEventListener("click", () => openEditor(el.dataset.treeId)));
}

/* ────────────────────────────────────────────── Stats view ────── */
async function renderStats(c) {
  const s = await api("GET", "/api/stats");
  const rows = (label, map) => Object.entries(map).map(([k,v]) => `<div class="stat-row"><span>${label[k]||k}</span><strong>${v}</strong></div>`).join("");
  c.innerHTML = `<div class="stats-panel">
    <div class="stat-card"><h3>Total nodes</h3><div class="big-num">${s.total}</div></div>
    <div class="stat-card"><h3>Overdue</h3><div class="big-num ${s.overdue ? "warn" : ""}">${s.overdue}</div></div>
    <div class="stat-card"><h3>By status</h3>${rows(STATUS_LABEL, s.by_status)}</div>
    <div class="stat-card"><h3>By priority</h3>${rows(PRI_LABEL, s.by_priority)}</div>
    <div class="stat-card"><h3>By type</h3>${rows(TYPE_LABEL, s.by_type)}</div>
  </div>`;
}

/* ────────────────────────────────────────────── Graph view ────── */
let graphData = null;
let graphNodes = null;
let draggingNode = null;
function renderGraph(c) {
  c.innerHTML = '<canvas id="graphCanvas"></canvas><div class="graph-controls"><button id="graphReset">Reset</button></div>';
  const canvas = $("graphCanvas");
  fetchGraphAndDraw(canvas);
  $("graphReset")?.addEventListener("click", () => { graphData = null; fetchGraphAndDraw(canvas); });
  // pan/drag
  canvas.addEventListener("mousedown", (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    if (!graphNodes) return;
    for (const n of graphNodes) {
      if (Math.hypot(n.x - mx, n.y - my) < 12) { draggingNode = n; break; }
    }
  });
  canvas.addEventListener("mousemove", (e) => {
    if (!draggingNode) return;
    const rect = canvas.getBoundingClientRect();
    draggingNode.x = e.clientX - rect.left; draggingNode.y = e.clientY - rect.top;
    drawGraph(canvas, { nodes: graphNodes.map((n)=>({id:n.id,label:n.label,status:n.status,type:n.type,x:n.x,y:n.y})), edges: graphData.edges });
  });
  canvas.addEventListener("mouseup", () => draggingNode = null);
  canvas.addEventListener("mouseleave", () => draggingNode = null);
}
async function fetchGraphAndDraw(canvas) {
  if (!graphData) graphData = await api("GET", "/api/graph");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  graphNodes = graphData.nodes.map((n, i) => {
    const angle = (i / Math.max(graphData.nodes.length,1)) * Math.PI * 2;
    const r = Math.min(w, h) * 0.32;
    return { ...n, x: w/2 + Math.cos(angle)*r, y: h/2 + Math.sin(angle)*r };
  });
  drawGraph(canvas, { nodes: graphNodes, edges: graphData.edges });
  canvas.addEventListener("click", (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    for (const n of graphNodes) {
      if (Math.hypot(n.x - mx, n.y - my) < 10) { openEditor(n.id); return; }
    }
  }, { once: true });
}
function drawGraph(canvas, data) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  ctx.setTransform(1,0,0,1,0,0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.scale(dpr, dpr);
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!data.nodes.length) {
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--text-dim") || "#888";
    ctx.font = "14px sans-serif"; ctx.fillText("No nodes to graph", w/2 - 60, h/2); return;
  }
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--border") || "#333";
  ctx.lineWidth = 1;
  for (const e of (data.edges || [])) {
    const s = data.nodes.find((n)=>n.id===e.source), t = data.nodes.find((n)=>n.id===e.target);
    if (s && t) { ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke(); }
  }
  const colors = { todo: "#888", in_progress: "#ff9800", review: "#4a9eff", done: "#4caf50", note: "#7c6ef0", workspace: "#4a9eff", area: "#ff9800", board: "#4caf50" };
  for (const n of data.nodes) {
    ctx.beginPath(); ctx.arc(n.x, n.y, 7, 0, Math.PI*2);
    ctx.fillStyle = colors[n.status] || colors[n.type] || "#888"; ctx.fill();
  }
  const textColor = getComputedStyle(document.documentElement).getPropertyValue("--text") || "#fff";
  ctx.fillStyle = textColor; ctx.font = "11px sans-serif";
  for (const n of data.nodes) ctx.fillText(n.label.slice(0,16), n.x + 10, n.y + 3);
}

/* ────────────────────────────────────────────── Editor ───────── */
function fillSelect(sel, options, current) {
  sel.innerHTML = options.map((o) => `<option value="${o}" ${o===current?"selected":""}>${(typeof o === 'string' ? (STATUS_LABEL[o]||PRI_LABEL[o]||TYPE_LABEL[o]||o) : o)}</option>`).join("");
}
async function openEditor(id) {
  const node = findNode(TREE, id);
  if (!node) return;
  CURRENT_NODE = node;
  EDITOR_OPEN = true;
  $("editor").classList.remove("hidden");
  $("editorTitle").value = node.title;
  $("editorBody").value = node.body_markdown || "";
  $("editorDue").value = node.due_date ? node.due_date.slice(0,10) : "";
  $("editorTags").value = (node.tags || []).join(", ");
  fillSelect($("editorStatus"), STATUSES, node.status);
  fillSelect($("editorPriority"), PRIORITIES, node.priority);
  fillSelect($("editorType"), NODE_TYPES, node.node_type);
  await loadBacklinks(id);
  setTimeout(() => $("editorTitle").focus(), 60);
}
function closeEditor() {
  EDITOR_OPEN = false;
  $("editor").classList.add("hidden");
  CURRENT_NODE = null;
}
async function loadBacklinks(id) {
  try {
    const bl = await api("GET", `/api/backlinks/${id}`);
    const c = $("editorBacklinks");
    if (!bl.results.length) { c.innerHTML = '<div class="backlinks-title">No backlinks</div>'; return; }
    c.innerHTML = `<div class="backlinks-title">Linked from (${bl.results.length})</div>` + bl.results.map((b) => `<div class="backlink-item" data-tree-id="${b.id}">← ${escapeHtml(b.title)}</div>`).join("");
    c.querySelectorAll("[data-tree-id]").forEach((el) => el.addEventListener("click", () => openEditor(el.dataset.treeId)));
  } catch(_) { $("editorBacklinks").innerHTML = ""; }
}
let saveTimer = null;
function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(() => { saveEditor(); showToast("Saved"); }, 800); }
["editorTitle", "editorBody", "editorDue", "editorTags"].forEach((id) => $(id).addEventListener("input", scheduleSave));
["editorStatus", "editorPriority", "editorType"].forEach((id) => $(id).addEventListener("change", scheduleSave));
async function saveEditor() {
  if (!CURRENT_NODE) return;
  const tags = $("editorTags").value.split(",").map((t) => t.trim()).filter(Boolean);
  await api("PATCH", `/api/nodes/${CURRENT_NODE.id}`, {
    title: $("editorTitle").value.trim(), body_markdown: $("editorBody").value,
    status: $("editorStatus").value, priority: $("editorPriority").value, node_type: $("editorType").value,
    due_date: $("editorDue").value || null, tags
  });
}
$("editorBack").addEventListener("click", async () => { await saveEditor(); closeEditor(); await loadTree(); });

/* ────────────────────────────────────────────── Add / Context ── */
$("addBtn").addEventListener("click", () => quickAdd());
async function quickAdd() {
  const title = prompt("New task title:");
  if (!title) return;
  const node = await api("POST", "/api/nodes", { title, node_type: "task", status: "todo" });
  showToast("✓ Task added");
  await loadTree();
  openEditor(node.id);
}
$("editorMenu").addEventListener("click", (e) => {
  if (!CURRENT_NODE) return;
  showCtxMenu((e.clientX||window.innerWidth-220), (e.clientY||60), [
    { label: "✓ Toggle status", fn: async () => { await api("POST", `/api/nodes/${CURRENT_NODE.id}/toggle`); await loadTree(); openEditor(CURRENT_NODE.id); } },
    { label: "➕ Add subtask", fn: async () => { const t = prompt("Subtask:"); if (t) { await api("POST", "/api/nodes", { title: t, parent_id: CURRENT_NODE.id, node_type: "subtask" }); await loadTree(); } } },
    { label: "📋 Add child board", fn: async () => { const t = prompt("Board name:"); if (t) { await api("POST", "/api/nodes", { title: t, parent_id: CURRENT_NODE.id, node_type: "board" }); await loadTree(); } } },
    { label: "📝 Convert to note", fn: async () => { await api("PATCH", `/api/nodes/${CURRENT_NODE.id}`, { node_type: "note" }); await loadTree(); } },
    { sep: true },
    { label: "🗑 Delete", danger: true, fn: async () => { if (confirm("Delete this node and all children?")) { await api("DELETE", `/api/nodes/${CURRENT_NODE.id}`); closeEditor(); await loadTree(); } } },
  ]);
});
function showCtxMenu(x, y, items) {
  document.querySelectorAll(".ctx-menu").forEach((m) => m.remove());
  const m = document.createElement("div");
  m.className = "ctx-menu"; m.style.left = Math.min(x, window.innerWidth-200) + "px"; m.style.top = Math.min(y, window.innerHeight-260) + "px";
  for (const it of items) {
    if (it.sep) { const s = document.createElement("div"); s.className = "ctx-sep"; m.appendChild(s); continue; }
    const el = document.createElement("div");
    el.className = "ctx-item" + (it.danger ? " danger" : "");
    el.textContent = it.label;
    el.addEventListener("click", async (ev) => { ev.stopPropagation(); m.remove(); await it.fn(); });
    m.appendChild(el);
  }
  document.body.appendChild(m);
  setTimeout(() => document.addEventListener("click", () => m.remove(), { once: true }), 10);
}

/* ────────────────────────────────────────────── Search ───────── */
$("search").addEventListener("input", (e) => {
  clearTimeout(SEARCH_DEBOUNCE);
  const q = e.target.value;
  SEARCH_DEBOUNCE = setTimeout(async () => {
    if (!q.trim()) { renderView(); return; }
    const { results } = await api("GET", `/api/search?q=${encodeURIComponent(q)}`);
    const c = $("content");
    c.innerHTML = `<div class="notes-list"><div class="search-info">${results.length} results for "${escapeHtml(q)}"</div>` +
      results.map((n) => `<div class="note-card" data-tree-id="${n.id}"><div class="note-title">${TYPE_ICON[n.node_type]||""} ${escapeHtml(n.title)}</div><div class="note-preview">${escapeHtml((n.body_markdown||n.description||"").slice(0,120))}</div></div>`).join("") + "</div>";
    c.querySelectorAll("[data-tree-id]").forEach((el) => el.addEventListener("click", () => openEditor(el.dataset.treeId)));
  }, 280);
});

/* ────────────────────────────────────────────── Keyboard ─────── */
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
  if (e.key === "n" || e.key === "N") { e.preventDefault(); quickAdd(); }
  if (e.key === "/") { e.preventDefault(); $("search").focus(); }
  if (e.key === "Escape" && EDITOR_OPEN) { closeEditor(); loadTree(); }
});

/* ────────────────────────────────────────────── Utils ────────── */
function escapeHtml(s) { return (s||"").replace(/[&<>"']/g, (c) => ({"&":"&","<":"<",">":">",'"':""","'":"&#39;"}[c])); }

/* ────────────────────────────────────────────── Init ─────────── */
loadTree();
