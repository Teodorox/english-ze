"use strict";

// ---------- Utilitários ----------

const $ = (sel, root = document) => root.querySelector(sel);

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (res.status === 401 && path !== "/api/login") {
    location.href = "/login.html"; // sessão expirou
    throw new Error("Faça login");
  }
  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = await res.json();
      message = typeof data.detail === "string" ? data.detail : message;
    } catch {}
    throw new Error(message);
  }
  return res.status === 204 ? null : res.json();
}

const store = {
  get(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value === null ? fallback : JSON.parse(value);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
  },
};

function flash(target, message, ms = 2500) {
  target.textContent = message;
  if (ms) setTimeout(() => { if (target.textContent === message) target.textContent = ""; }, ms);
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

// ---------- Voz (Text-to-Speech) ----------

const tts = {
  voice: null,
  supported: "speechSynthesis" in window,

  pickVoice() {
    if (!this.supported) return;
    const voices = speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith("en-us"));
    // Vozes "Natural" (Edge) e Google soam bem mais humanas.
    this.voice =
      voices.find((v) => /natural/i.test(v.name)) ||
      voices.find((v) => /google/i.test(v.name)) ||
      voices[0] || null;
  },

  speak(text, rate = 1) {
    if (!this.supported || !text) return;
    speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "en-US";
    utter.rate = rate;
    if (this.voice) utter.voice = this.voice;
    speechSynthesis.speak(utter);
  },
};

if (tts.supported) {
  tts.pickVoice();
  speechSynthesis.addEventListener("voiceschanged", () => tts.pickVoice());
}

// ---------- Abas ----------

const loaders = {};
let activeTab = "study";

function showTab(name) {
  activeTab = name;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((s) => s.classList.toggle("active", s.id === `tab-${name}`));
  loaders[name]?.();
}

$("#tabs").addEventListener("click", (e) => {
  const button = e.target.closest("button[data-tab]");
  if (button) showTab(button.dataset.tab);
});

// ---------- Estudar ----------

const study = {
  queue: [],
  current: null,
  revealed: false,
  mode: store.get("studyMode", "read"),
  done: 0,
};

const newLimitInput = $("#new-limit");
newLimitInput.value = store.get("newLimit", 10);
newLimitInput.addEventListener("change", () => {
  const value = Math.max(0, Math.min(100, Number(newLimitInput.value) || 0));
  newLimitInput.value = value;
  store.set("newLimit", value);
  loadStudy();
});

function syncModeButtons() {
  document.querySelectorAll("#study-mode button").forEach((b) => b.classList.toggle("active", b.dataset.mode === study.mode));
}
syncModeButtons();

$("#study-mode").addEventListener("click", (e) => {
  const button = e.target.closest("button[data-mode]");
  if (!button) return;
  study.mode = button.dataset.mode;
  store.set("studyMode", study.mode);
  syncModeButtons();
  renderStudy();
});

async function loadStudy() {
  const area = $("#study-area");
  try {
    const data = await api(`/api/session?new_limit=${Number(newLimitInput.value) || 0}`);
    study.queue = [...data.due, ...data.new];
    study.current = null;
    study.done = 0;
    nextCard();
  } catch (err) {
    area.replaceChildren(el("p", { class: "card" }, `Erro ao carregar: ${err.message}`));
  }
}
loaders.study = loadStudy;

function nextCard() {
  study.current = study.queue.shift() || null;
  study.revealed = false;
  renderStudy();
  if (study.current && study.mode === "listen") tts.speak(study.current.front);
}

function renderStudy() {
  const area = $("#study-area");
  const card = study.current;
  const newCount = study.queue.filter((c) => !c.introduced_on).length + (card && !card.introduced_on ? 1 : 0);
  const total = study.queue.length + (card ? 1 : 0);
  $("#study-counts").textContent = card ? `${total} restantes · ${newCount} novos` : "";

  if (!card) {
    area.replaceChildren(
      el("div", { class: "card done" },
        el("div", { class: "big" }, study.done ? "🏆" : "😎"),
        el("h2", {}, study.done ? "That's a W" : "We're all caught up"),
        el("p", {}, study.done ? `${study.done} revisões hoje. Bro is locked in. 🔒` : "Nada pra revisar agora."),
        el("p", { class: "muted" }, "Que tal minerar umas frases da próxima live ou fazer um shadowing rápido?"),
      ),
    );
    return;
  }

  const hideFront = study.mode === "listen" && !study.revealed;
  const children = [
    el("div", { class: "meta" },
      el("span", { class: `badge ${card.introduced_on ? "" : "new"}` }, card.introduced_on ? "revisão" : "novo"),
      el("span", { class: "badge" }, card.category),
    ),
    hideFront
      ? el("p", { class: "front muted" }, "🎧 Ouça e tente entender")
      : el("p", { class: "front" }, card.front),
    el("div", { class: "audio-row" },
      el("button", { onclick: () => tts.speak(card.front) }, "🔊 Ouvir"),
      el("button", { onclick: () => tts.speak(card.front, 0.7) }, "🐢 Devagar"),
    ),
  ];

  if (!study.revealed) {
    children.push(el("div", {}, el("button", { class: "primary", onclick: reveal }, "Mostrar resposta")));
  } else {
    children.push(
      el("p", { class: "back" }, card.back),
      card.note && el("p", { class: "note" }, card.note),
      card.source && card.source !== "deck inicial" && el("p", { class: "source" }, `Fonte: ${card.source}`),
      el("div", { class: "grades" },
        gradeButton(0, "L", "errei", "g-again"),
        gradeButton(1, "Mid", "difícil", "g-hard"),
        gradeButton(2, "W", "bom", "g-good"),
        gradeButton(3, "GOAT 🐐", "fácil", "g-easy"),
      ),
    );
  }

  area.replaceChildren(el("div", { class: "card flashcard" }, children));
}

function gradeButton(grade, label, sub, cls) {
  return el("button", { class: cls, onclick: () => grade_(grade) }, label, el("small", {}, `${grade + 1} · ${sub}`));
}

// ---------- Chat da live (reações aos acertos) ----------

const CHAT_USERS = ["lilbro_22", "chat_goblin", "bronx_kid", "zeboy", "goat_watcher", "nyc_lurker", "yapper99", "lockedin_ana"];
const CHAT_COLORS = ["#ff3b4e", "#22e07a", "#ffc93c", "#9b5cff", "#3fa9ff", "#ff8a1f"];
const CHAT_REACTIONS = [
  ["L 😭", "it's ok bro, run it back", "we been there 💀", "next one fr"],
  ["mid but we take those", "almost had it", "lock in 🔒", "keep cooking"],
  ["W", "W W W", "LETS GOOO", "bro is locked in 🔒", "no cap that was clean"],
  ["GOAT 🐐", "HE'S HIM", "aura +1000", "bro is cooking 🔥", "too easy"],
];
const pick = (list) => list[Math.floor(Math.random() * list.length)];

function chatPop(grade) {
  const feed = $("#chat-feed");
  const count = grade >= 2 ? 3 : 1;
  for (let i = 0; i < count; i++) {
    setTimeout(() => {
      const msg = el("div", { class: "chat-msg" },
        el("b", { style: `color:${pick(CHAT_COLORS)}` }, pick(CHAT_USERS)),
        pick(CHAT_REACTIONS[grade]),
      );
      feed.append(msg);
      while (feed.children.length > 5) feed.firstChild.remove();
      setTimeout(() => msg.remove(), 2700);
    }, i * 180);
  }
}

function reveal() {
  if (!study.current || study.revealed) return;
  study.revealed = true;
  renderStudy();
}

let grading = false;
async function grade_(grade) {
  const card = study.current;
  if (!card || !study.revealed || grading) return;
  grading = true;
  try {
    await api(`/api/cards/${card.id}/review`, { method: "POST", body: { grade } });
    study.done += 1;
    chatPop(grade);
    card.introduced_on = card.introduced_on || "hoje";
    if (grade === 0) study.queue.push(card); // errou: volta no fim da fila
    nextCard();
  } catch (err) {
    alert(`Não consegui salvar: ${err.message}`);
  } finally {
    grading = false;
  }
}

document.addEventListener("keydown", (e) => {
  if (activeTab !== "study" || e.target.matches("input, textarea, select")) return;
  if (e.key === " " || e.key === "Enter") {
    e.preventDefault();
    reveal();
  } else if (["1", "2", "3", "4"].includes(e.key)) {
    grade_(Number(e.key) - 1);
  } else if (e.key.toLowerCase() === "r" && study.current) {
    tts.speak(study.current.front);
  }
});

// ---------- Falar (shadowing) ----------

const shadowText = $("#shadow-text");
const shadowStatus = $("#shadow-status");
let cardsCache = null;

async function randomPhrase() {
  if (!cardsCache) cardsCache = await api("/api/cards");
  if (!cardsCache.length) return;
  shadowText.value = cardsCache[Math.floor(Math.random() * cardsCache.length)].front;
  $("#shadow-result").replaceChildren();
}

loaders.shadow = () => { if (!shadowText.value) randomPhrase(); };

$("#shadow-random").addEventListener("click", randomPhrase);
$("#shadow-play").addEventListener("click", () => tts.speak(shadowText.value));
$("#shadow-slow").addEventListener("click", () => tts.speak(shadowText.value, 0.7));

let recorder = null;
$("#shadow-record").addEventListener("click", async (e) => {
  const button = e.currentTarget;
  if (recorder && recorder.state === "recording") {
    recorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (ev) => chunks.push(ev.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const audio = $("#shadow-audio");
      audio.src = URL.createObjectURL(new Blob(chunks, { type: recorder.mimeType }));
      audio.hidden = false;
      audio.play();
      button.textContent = "⏺ Gravar";
      flash(shadowStatus, "Compare com o áudio original 👆");
    };
    recorder.start();
    button.textContent = "⏹ Parar";
    flash(shadowStatus, "Gravando... fale a frase", 0);
  } catch (err) {
    flash(shadowStatus, `Sem acesso ao microfone: ${err.message}`, 5000);
  }
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function normalizeWords(text) {
  return text
    .toLowerCase()
    .replace(/[’‘]/g, "'")
    .replace(/[^a-z0-9' ]+/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

$("#shadow-check").addEventListener("click", () => {
  const target = shadowText.value.trim();
  if (!target) return;
  if (!SpeechRecognition) {
    flash(shadowStatus, "Seu navegador não tem reconhecimento de voz. Use o Chrome ou o Edge.", 5000);
    return;
  }
  const rec = new SpeechRecognition();
  rec.lang = "en-US";
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  flash(shadowStatus, "Ouvindo... fale agora", 0);

  rec.onresult = (ev) => {
    const heard = ev.results[0][0].transcript;
    const heardWords = new Set(normalizeWords(heard));
    const targetWords = normalizeWords(target);
    const hits = targetWords.filter((w) => heardWords.has(w)).length;
    const score = targetWords.length ? Math.round((hits / targetWords.length) * 100) : 0;

    $("#shadow-result").replaceChildren(
      el("p", { class: "score" }, `${score}% · ${score >= 90 ? "No cap 🔥" : score >= 60 ? "That's a W 👍" : "Run it back 💪"}`),
      el("p", { class: "muted" }, `Entendi: "${heard}"`),
      el("div", { class: "words" },
        targetWords.map((w) => el("span", { class: `word ${heardWords.has(w) ? "ok" : "miss"}` }, w)),
      ),
    );
    shadowStatus.textContent = "";
  };
  rec.onerror = (ev) => flash(shadowStatus, `Não deu pra ouvir (${ev.error}). Tenta de novo.`, 4000);
  rec.onend = () => { if (shadowStatus.textContent.startsWith("Ouvindo")) shadowStatus.textContent = ""; };
  rec.start();
});

// ---------- Minerar ----------

async function loadCategories() {
  const categories = await api("/api/categories");
  $("#category-list").replaceChildren(...categories.map((c) => el("option", { value: c })));
  const select = $("#cards-category");
  const current = select.value;
  select.replaceChildren(
    el("option", { value: "" }, "Todas as categorias"),
    ...categories.map((c) => el("option", { value: c }, c)),
  );
  select.value = current;
}

loaders.mine = loadCategories;

$("#mine-listen").addEventListener("click", () => tts.speak($("#mine-form").front.value));

$("#mine-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const status = $("#mine-status");
  const body = Object.fromEntries(new FormData(form));
  try {
    await api("/api/cards", { method: "POST", body });
    cardsCache = null;
    form.front.value = form.back.value = form.note.value = "";
    form.front.focus();
    flash(status, "✅ Card salvo!");
  } catch (err) {
    flash(status, `⚠️ ${err.message}`, 4000);
  }
});

$("#bulk-import").addEventListener("click", async () => {
  const status = $("#bulk-status");
  const category = $("#mine-form").category.value || "geral";
  const lines = $("#bulk-text").value.split("\n").map((l) => l.trim()).filter(Boolean);
  let ok = 0;
  const failed = [];
  for (const line of lines) {
    const [front = "", back = "", note = ""] = line.split("|").map((p) => p.trim());
    if (!front || !back) { failed.push(line); continue; }
    try {
      await api("/api/cards", { method: "POST", body: { front, back, note, category, source: "importado" } });
      ok += 1;
    } catch {
      failed.push(line);
    }
  }
  cardsCache = null;
  $("#bulk-text").value = failed.join("\n");
  flash(status, `${ok} importados${failed.length ? `, ${failed.length} com erro (ficaram na caixa)` : ""}.`, 6000);
});

// ---------- Cards ----------

let searchTimer;
async function loadCards() {
  await loadCategories();
  const q = encodeURIComponent($("#cards-q").value.trim());
  const category = encodeURIComponent($("#cards-category").value);
  const cards = await api(`/api/cards?q=${q}&category=${category}`);
  $("#cards-count").textContent = `${cards.length} cards`;
  $("#cards-list").replaceChildren(
    ...cards.map((card) =>
      el("li", {},
        el("div", { class: "grow" },
          el("div", { class: "title" }, card.front),
          el("div", {}, card.back),
          el("div", { class: "sub" },
            `${card.category} · `,
            card.introduced_on ? `próxima revisão: ${formatDate(card.due + "T12:00")}` : "ainda não estudado",
          ),
        ),
        el("button", { title: "Ouvir", onclick: () => tts.speak(card.front) }, "🔊"),
        el("button", { title: "Apagar", onclick: () => deleteCard(card) }, "🗑"),
      ),
    ),
  );
}
loaders.cards = loadCards;

async function deleteCard(card) {
  if (!confirm(`Apagar "${card.front}"?`)) return;
  await api(`/api/cards/${card.id}`, { method: "DELETE" });
  cardsCache = null;
  loadCards();
}

$("#cards-q").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadCards, 250);
});
$("#cards-category").addEventListener("change", loadCards);

// ---------- Diário ----------

function correctionPrompt(text) {
  return [
    "Sou brasileiro e estou no nível iniciante de inglês. Corrija o texto abaixo:",
    "1) Mostre a versão corrigida.",
    "2) Liste cada erro com uma explicação curta em português.",
    "3) Mostre como um americano diria isso de um jeito natural e informal.",
    "",
    "Texto:",
    text,
  ].join("\n");
}

async function copyPrompt(text, status) {
  try {
    await navigator.clipboard.writeText(correctionPrompt(text));
    flash(status, "📋 Copiado! Cole no Claude ou no ChatGPT.");
  } catch {
    flash(status, "Não consegui copiar automaticamente.", 4000);
  }
}

let tutorEnabled = false;

async function loadTutorStatus() {
  try {
    tutorEnabled = (await api("/api/tutor/status")).enabled;
  } catch {
    tutorEnabled = false;
  }
  $("#journal-save").textContent = tutorEnabled ? "✨ Salvar e corrigir" : "Salvar";
}

function renderCorrection(c) {
  return el("div", { class: "correction" },
    el("div", { class: "label" }, "✅ Corrigido"),
    el("p", { class: "pre" }, c.corrected),
    el("div", { class: "label" }, "🇺🇸 Como um americano diria"),
    el("p", { class: "pre" }, c.natural, " ",
      el("button", { class: "mini", title: "Ouvir", onclick: () => tts.speak(c.natural) }, "🔊")),
    c.mistakes.length
      ? el("div", {},
          el("div", { class: "label" }, `📝 Erros (${c.mistakes.length})`),
          el("ul", { class: "mistakes" },
            c.mistakes.map((m) =>
              el("li", {},
                el("s", {}, m.original), " → ", el("strong", {}, m.correction),
                el("div", { class: "muted" }, m.explanation),
              ),
            ),
          ),
        )
      : el("p", {}, "Zero erros. You ate that 🔥"),
    el("p", { class: "encourage" }, c.encouragement),
  );
}

async function correctEntry(id, status) {
  flash(status, "✨ Corrigindo...", 0);
  try {
    const result = await api(`/api/journal/${id}/correct`, { method: "POST" });
    if (result.cards_created) cardsCache = null;
    await loadJournal();
    flash(
      $("#journal-status"),
      result.cards_created
        ? `✅ Corrigido! ${result.cards_created} card(s) novo(s) em "meus-erros".`
        : "✅ Corrigido!",
      6000,
    );
  } catch (err) {
    flash(status, `⚠️ ${err.message}`, 8000);
  }
}

async function loadJournal() {
  const entries = await api("/api/journal");
  $("#journal-list").replaceChildren(
    ...entries.map((entry) => {
      const status = el("span", { class: "muted" });
      return el("li", {},
        el("div", { class: "grow" },
          el("div", { class: "sub" }, new Date(entry.created_at).toLocaleString("pt-BR")),
          el("div", { class: "pre" }, entry.text),
          entry.correction && renderCorrection(entry.correction),
          status,
        ),
        tutorEnabled && !entry.correction &&
          el("button", { title: "Corrigir com IA", onclick: () => correctEntry(entry.id, status) }, "✨"),
        el("button", { title: "Copiar prompt de correção", onclick: () => copyPrompt(entry.text, status) }, "📋"),
      );
    }),
  );
}
loaders.journal = async () => {
  await loadTutorStatus();
  await loadJournal();
};

$("#journal-save").addEventListener("click", async (e) => {
  const button = e.currentTarget;
  const text = $("#journal-text").value.trim();
  if (!text || button.disabled) return;
  const status = $("#journal-status");
  button.disabled = true;
  try {
    const entry = await api("/api/journal", { method: "POST", body: { text } });
    $("#journal-text").value = "";
    await loadJournal();
    if (tutorEnabled) await correctEntry(entry.id, status);
    else flash(status, "✅ Salvo!");
  } catch (err) {
    flash(status, `⚠️ ${err.message}`, 6000);
  } finally {
    button.disabled = false;
  }
});

$("#journal-copy").addEventListener("click", () => {
  const text = $("#journal-text").value.trim();
  if (text) copyPrompt(text, $("#journal-status"));
});

// ---------- Progresso ----------

async function loadProgress() {
  const s = await api("/api/stats");
  const tile = (value, label) => el("div", { class: "tile" }, el("div", { class: "value" }, value), el("div", { class: "label" }, label));
  $("#stats-tiles").replaceChildren(
    tile(`🔥 ${s.streak}`, `streak · ${s.streak === 1 ? "dia seguido" : "dias seguidos"}`),
    tile(s.reviews_today, "reps · revisões hoje"),
    tile(`${s.learned}/${s.total_cards}`, "cards já estudados"),
    tile(`🐐 ${s.mature}`, "dominados (21+ dias)"),
    tile(s.due_today, "pra revisar hoje"),
    tile(s.due_tomorrow, "pra amanhã"),
  );
  const max = Math.max(1, ...s.history.map((h) => h.reviews));
  $("#stats-history").replaceChildren(
    ...s.history.map((h) =>
      el("div", { class: "bar", title: `${h.day}: ${h.reviews}` },
        h.reviews || "",
        el("div", { class: "fill", style: `height:${(h.reviews / max) * 100}%` }),
        h.day.slice(8),
      ),
    ),
  );
}
loaders.progress = loadProgress;

// ---------- Login ----------

api("/api/auth/status").then(({ enabled }) => { $("#logout").hidden = !enabled; }).catch(() => {});

$("#logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.href = "/login.html";
});

// ---------- Início ----------

showTab("study");
