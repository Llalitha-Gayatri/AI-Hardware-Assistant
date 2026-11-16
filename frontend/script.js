// Frontend JavaScript for Linux Hardware AI Assistant

const API_BASE = window.location.origin.includes(":8000") || window.location.origin.includes(":3000")
  ? window.location.origin
  : "http://localhost:8000";

let conversationHistory = [];
let cachedHardwareSummary = null;

// DOM Elements
const chatHistory = document.getElementById("chat-history");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const typingIndicator = document.getElementById("typing-indicator");
const statusBadge = document.getElementById("status-badge");
const providerBadge = document.getElementById("provider-badge");
const distroLabel = document.getElementById("distro-label");
const wslBanner = document.getElementById("wsl-banner");
const wslMessage = document.getElementById("wsl-message");
const clearChatBtn = document.getElementById("clear-chat-btn");
const refreshHwBtn = document.getElementById("refresh-hw-btn");

// Modal Elements
const dataModal = document.getElementById("data-modal");
const modalTitle = document.getElementById("modal-title");
const modalJson = document.getElementById("modal-json");
const modalClose = document.getElementById("modal-close");
const modalBackdrop = document.getElementById("modal-backdrop");

// Format Markdown to clean HTML
function formatMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  
  // Lists
  const lines = html.split("\n");
  let inList = false;
  let formattedLines = [];

  for (let line of lines) {
    line = line.trim();
    if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList) {
        formattedLines.push("<ul>");
        inList = true;
      }
      formattedLines.push(`<li>${line.substring(2)}</li>`);
    } else {
      if (inList) {
        formattedLines.push("</ul>");
        inList = false;
      }
      if (line.length > 0) {
        formattedLines.push(`<p>${line}</p>`);
      }
    }
  }
  if (inList) formattedLines.push("</ul>");

  return formattedLines.join("");
}

// Auto-expand textarea
userInput.addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = Math.min(this.scrollHeight, 120) + "px";
});

// Submit on Enter key (without Shift)
userInput.addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event("submit"));
  }
});

// Append Message to History
function appendMessage(role, content, toolsUsed = [], toolResults = []) {
  const row = document.createElement("div");
  row.className = `message-row ${role === "user" ? "user" : "ai"}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role === "user" ? "user-avatar" : "ai-avatar"}`;
  avatar.textContent = role === "user" ? "U" : "🤖";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  const header = document.createElement("div");
  header.className = "bubble-header";
  header.innerHTML = `
    <span class="sender-name">${role === "user" ? "You" : "Hardware Assistant"}</span>
    <span class="timestamp">${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
  `;

  const contentDiv = document.createElement("div");
  contentDiv.className = "bubble-content";
  contentDiv.innerHTML = formatMarkdown(content);

  bubble.appendChild(header);
  bubble.appendChild(contentDiv);

  // If AI ran tools, append interactive inspection tool badges
  if (role === "assistant" && toolResults && toolResults.length > 0) {
    const toolsContainer = document.createElement("div");
    toolsContainer.className = "tools-badge-container";
    toolsContainer.innerHTML = `<span class="tools-label">Tools Executed:</span>`;

    toolResults.forEach((tr) => {
      const badge = document.createElement("button");
      badge.className = "tool-badge";
      badge.innerHTML = `🔧 ${tr.display_name || tr.tool_name}`;
      badge.title = "Click to view raw inspection telemetry";
      badge.addEventListener("click", () => {
        showModal(tr.display_name || tr.tool_name, tr.data || { error: tr.error });
      });
      toolsContainer.appendChild(badge);
    });

    bubble.appendChild(toolsContainer);
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatHistory.appendChild(row);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Modal handling
function showModal(title, data) {
  modalTitle.textContent = `${title} (Raw Telemetry)`;
  modalJson.textContent = JSON.stringify(data, null, 2);
  dataModal.classList.add("active");
}

function closeModal() {
  dataModal.classList.remove("active");
}

modalClose.addEventListener("click", closeModal);
modalBackdrop.addEventListener("click", closeModal);

// Handle Chat Submission
chatForm.addEventListener("submit", async function (e) {
  e.preventDefault();
  const message = userInput.value.trim();
  if (!message) return;

  // Append user message to UI
  appendMessage("user", message);
  userInput.value = "";
  userInput.style.height = "auto";
  userInput.disabled = true;
  sendBtn.disabled = true;
  typingIndicator.style.display = "flex";
  chatHistory.scrollTop = chatHistory.scrollHeight;

  try {
    const payload = {
      message: message,
      history: conversationHistory,
    };

    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Server returned status ${res.status}`);
    }

    const data = await res.json();

    // Update conversation context for follow-up questions
    conversationHistory.push({ role: "user", content: message });
    conversationHistory.push({ role: "assistant", content: data.answer });

    // Append AI response
    appendMessage("assistant", data.answer, data.tools_used, data.tool_results);

  } catch (err) {
    appendMessage(
      "assistant",
      `⚠️ **Connection Error**: Could not reach backend server (${err.message}). Please verify the backend is running at ${API_BASE}.`
    );
  } finally {
    typingIndicator.style.display = "none";
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
  }
});

// Suggested Question Chips
document.querySelectorAll(".chip-btn").forEach((chip) => {
  chip.addEventListener("click", () => {
    userInput.value = chip.getAttribute("data-query");
    chatForm.dispatchEvent(new Event("submit"));
  });
});

// Clear Chat History
clearChatBtn.addEventListener("click", () => {
  conversationHistory = [];
  chatHistory.innerHTML = `
    <div class="message-row ai">
      <div class="avatar ai-avatar">🤖</div>
      <div class="message-bubble">
        <div class="bubble-header">
          <span class="sender-name">Hardware AI Assistant</span>
          <span class="timestamp">Just now</span>
        </div>
        <div class="bubble-content">
          <p>Conversation cleared. Feel free to ask another hardware question!</p>
        </div>
      </div>
    </div>
    <div class="suggested-container" id="suggested-container">
      <div class="suggested-title">💡 Suggested Questions</div>
      <div class="suggested-chips">
        <button class="chip-btn" data-query="How much RAM do I have?">How much RAM do I have?</button>
        <button class="chip-btn" data-query="Which processor does my laptop use?">Which processor does my laptop use?</button>
        <button class="chip-btn" data-query="What GPU do I have?">What GPU do I have?</button>
        <button class="chip-btn" data-query="Is my SSD NVMe or SATA?">Is my SSD NVMe or SATA?</button>
        <button class="chip-btn" data-query="How much storage is available?">How much storage is available?</button>
        <button class="chip-btn" data-query="Can I upgrade my RAM?">Can I upgrade my RAM?</button>
      </div>
    </div>
  `;
  // Re-attach chip event listeners
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      userInput.value = chip.getAttribute("data-query");
      chatForm.dispatchEvent(new Event("submit"));
    });
  });
});

// Fetch System Summary and Update Sidebar
async function fetchHardwareSummary() {
  try {
    const res = await fetch(`${API_BASE}/api/hardware`);
    if (!res.ok) throw new Error("Hardware summary failed");

    const data = await res.json();
    cachedHardwareSummary = data;

    // CPU Card
    const cpu = data.cpu;
    document.getElementById("card-cpu-model").textContent = cpu.model || "Unknown";
    let cpuSub = `${cpu.cores || "?"} Cores / ${cpu.threads || "?"} Threads`;
    if (cpu.architecture) cpuSub += ` (${cpu.architecture})`;
    document.getElementById("card-cpu-sub").textContent = cpuSub;

    // RAM Card
    const ram = data.ram;
    if (ram.total_human) {
      document.getElementById("card-ram-val").textContent = `${ram.used_human || "0"} / ${ram.total_human}`;
      document.getElementById("card-ram-sub").textContent = `${ram.available_human || "N/A"} available (${ram.usage_percentage || 0}%)`;
      document.getElementById("ram-progress").style.width = `${Math.min(ram.usage_percentage || 0, 100)}%`;
    } else {
      document.getElementById("card-ram-val").textContent = "N/A";
      document.getElementById("card-ram-sub").textContent = ram.error || "Cannot inspect memory";
    }

    // GPU Card
    const gpu = data.gpu;
    if (gpu.devices && gpu.devices.length > 0) {
      document.getElementById("card-gpu-val").textContent = gpu.devices[0].model;
      document.getElementById("card-gpu-sub").textContent = `${gpu.devices[0].vendor} (${gpu.devices.length} GPU detected)`;
    } else {
      document.getElementById("card-gpu-val").textContent = "No GPU Detected";
      document.getElementById("card-gpu-sub").textContent = gpu.error || "PCI Bus scan empty";
    }

    // Storage Card
    const storage = data.storage;
    const disks = (storage.devices || []).filter((d) => d.device_type === "disk");
    if (disks.length > 0) {
      const primary = disks[0];
      document.getElementById("card-storage-val").textContent = `${primary.name}: ${primary.size_human || "N/A"}`;
      document.getElementById("card-storage-sub").textContent = `${primary.media_type} (${disks.length} drive${disks.length > 1 ? "s" : ""})`;
    } else {
      document.getElementById("card-storage-val").textContent = "No Disks Found";
      document.getElementById("card-storage-sub").textContent = storage.error || "lsblk not available";
    }

    // Motherboard Card
    const mb = data.motherboard;
    if (mb.manufacturer || mb.product_name) {
      document.getElementById("card-mb-val").textContent = `${mb.manufacturer || ""} ${mb.product_name || ""}`.trim();
      document.getElementById("card-mb-sub").textContent = mb.bios_version ? `BIOS: ${mb.bios_version}` : "BIOS detected";
    } else {
      document.getElementById("card-mb-val").textContent = "Generic / Virtual";
      document.getElementById("card-mb-sub").textContent = mb.error || "DMI unavailable";
    }

    // Environment & WSL2
    const env = data.environment;
    distroLabel.textContent = env.distro_name || "Linux Host";

    if (env.is_wsl2) {
      wslBanner.style.display = "flex";
      wslMessage.textContent = env.warning || "WSL2 environment detected. Physical hardware tables may be virtualized.";
    } else {
      wslBanner.style.display = "none";
    }

  } catch (err) {
    console.warn("Could not fetch hardware summary:", err);
    document.getElementById("card-cpu-model").textContent = "Unavailable";
    document.getElementById("card-ram-val").textContent = "Unavailable";
    document.getElementById("card-gpu-val").textContent = "Unavailable";
    document.getElementById("card-storage-val").textContent = "Unavailable";
    document.getElementById("card-mb-val").textContent = "Unavailable";
  }
}

// Health Check
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      const data = await res.json();
      statusBadge.textContent = "Online";
      statusBadge.className = "badge";
      providerBadge.textContent = `Provider: ${data.llm_provider.toUpperCase()}`;
    } else {
      statusBadge.textContent = "Error";
      statusBadge.className = "badge offline";
    }
  } catch (e) {
    statusBadge.textContent = "Offline";
    statusBadge.className = "badge offline";
  }
}

// Refresh hardware button
refreshHwBtn.addEventListener("click", () => {
  refreshHwBtn.style.transform = "rotate(180deg)";
  setTimeout(() => { refreshHwBtn.style.transform = "rotate(0deg)"; }, 400);
  fetchHardwareSummary();
});

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  fetchHardwareSummary();
});
