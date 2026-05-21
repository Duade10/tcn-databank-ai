const sourceList = document.querySelector("#sourceList");
const metrics = document.querySelector("#metrics");
const chatMessages = document.querySelector("#chatMessages");
const queryForm = document.querySelector("#queryForm");
const sourceForm = document.querySelector("#sourceForm");
const installButton = document.querySelector("#installButton");
const archiveStatus = document.querySelector("#archiveStatus");
const ingestButton = document.querySelector("#ingestButton");
let deferredPrompt;
let chatHistory = JSON.parse(localStorage.getItem("tcnChatHistory") || "[]");

async function api(path, options = {}) {
  const { headers: optionHeaders = {}, ...fetchOptions } = options;
  const headers = { "Content-Type": "application/json", ...optionHeaders };
  const response = await fetch(path, {
    headers,
    ...fetchOptions,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || "Request failed");
  }
  return response.json();
}

function switchView(name) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelectorAll(".nav-button").forEach((button) => button.classList.remove("active"));
  document.querySelector(`#${name}View`).classList.add("active");
  document.querySelector(`[data-view="${name}"]`).classList.add("active");
}

async function loadSources() {
  const sources = await api("/api/sources");
  sourceList.innerHTML = sources.map((source) => `
    <label class="source-item">
      <input type="checkbox" value="${source.id}" checked>
      <span>
        <strong>${source.name}</strong>
        <small>${source.category}</small>
      </span>
    </label>
  `).join("");
}

async function loadCatalog() {
  const catalog = await api("/api/catalog");
  metrics.innerHTML = [
    ["Records", catalog.records],
    ["Numeric readings", catalog.numeric_readings],
    ["Status notes", catalog.status_readings],
    ["Lines", catalog.lines.length],
    ["Interfaces", catalog.interfaces.length],
    ["Dates", catalog.dates.length],
  ].map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join("");
  renderArchive(catalog.archive);
}

function renderArchive(archive) {
  if (!archiveStatus || !archive) return;
  const records = Number(archive.records || 0).toLocaleString();
  const dateRange = archive.first_date && archive.last_date ? `${archive.first_date} to ${archive.last_date}` : "No archived dates";
  archiveStatus.textContent = `${records} records · ${dateRange}`;
}

queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const questionInput = document.querySelector("#question");
  const question = questionInput.value.trim();
  if (!question) return;
  addMessage("user", question);
  questionInput.value = "";
  const loading = addMessage("assistant", "Checking the databank...");
  const source_ids = [...sourceList.querySelectorAll("input:checked")].map((input) => input.value);
  try {
    const result = await api("/api/query", {
      method: "POST",
      body: JSON.stringify({
        question,
        mode: document.querySelector("#mode").value,
        source_ids,
        history: chatHistory.slice(-10),
      }),
    });
    loading.textContent = `${result.answer}\n\nContext rows used: ${result.context_rows}`;
    remember("assistant", result.answer);
  } catch (error) {
    loading.textContent = error.message;
    remember("assistant", error.message);
  }
});

function addMessage(role, content) {
  const message = renderMessage(role, content);
  if (role === "user") remember(role, content);
  return message;
}

function renderMessage(role, content) {
  const message = document.createElement("div");
  message.className = `message ${role === "user" ? "user-message" : "assistant-message"}`;
  message.textContent = content;
  chatMessages.appendChild(message);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return message;
}

function remember(role, content) {
  chatHistory.push({ role, content });
  chatHistory = chatHistory.slice(-20);
  localStorage.setItem("tcnChatHistory", JSON.stringify(chatHistory));
}

function restoreChat() {
  if (!chatHistory.length) return;
  chatMessages.innerHTML = "";
  chatHistory.slice(-8).forEach((message) => {
    renderMessage(message.role, message.content);
  });
}

sourceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const tags = document.querySelector("#tags").value.split(",").map((tag) => tag.trim()).filter(Boolean);
  try {
    await api("/api/sources", {
      method: "POST",
      body: JSON.stringify({
        name: document.querySelector("#sourceName").value,
        description: document.querySelector("#sourceDescription").value,
        sheet_url_or_id: document.querySelector("#sheetUrl").value,
        category: document.querySelector("#category").value,
        tags,
      }),
    });
    await loadSources();
    switchView("assistant");
  } catch (error) {
    alert(error.message);
  }
});

ingestButton?.addEventListener("click", async () => {
  ingestButton.disabled = true;
  archiveStatus.textContent = "Reading live sheet...";
  try {
    const result = await api("/api/ingest", { method: "POST", body: "{}" });
    renderArchive(result.archive);
    await loadCatalog();
  } catch (error) {
    archiveStatus.textContent = error.message;
  } finally {
    ingestButton.disabled = false;
  }
});

document.querySelectorAll(".nav-button").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredPrompt = event;
  installButton.classList.remove("hidden");
});

installButton.addEventListener("click", async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  installButton.classList.add("hidden");
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/service-worker.js");
}

await loadSources();
await loadCatalog();
restoreChat();
