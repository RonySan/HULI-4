"use strict";

const byId = id => document.getElementById(id);
const loginView = byId("loginView");
const chatView = byId("chatView");
const loginForm = byId("loginForm");
const messageForm = byId("messageForm");
const loginButton = byId("loginButton");
const sendButton = byId("sendButton");
const messages = byId("messages");
let token = null;
let recognition = null;
let microphoneConfirmed = false;

function showLogin(message = "") {
  token = null;
  chatView.hidden = true;
  loginView.hidden = false;
  byId("logout").hidden = true;
  byId("password").value = "";
  byId("loginError").textContent = message;
}
function showChat(username) {
  loginView.hidden = true;
  chatView.hidden = false;
  byId("logout").hidden = false;
  byId("displayName").textContent = username;
  byId("messageInput").focus();
}
async function api(path, {method = "GET", body} = {}) {
  const headers = {"Accept": "application/json"};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = "Bearer " + token;
  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    credentials: "omit",
    redirect: "error"
  });
  let data = {};
  try { data = await response.json(); } catch (_) { /* Response can be empty */ }
  if (!response.ok) {
    if (response.status === 401 && token) {
      showLogin("Sua sessão expirou. Entre novamente.");
    }
    throw new Error(typeof data.detail === "string" ? data.detail : "Falha na comunicação (" + response.status + ").");
  }
  return data;
}
function appendMessage(text, role) {
  const empty = messages.querySelector(".welcome");
  if (empty) empty.remove();
  const bubble = document.createElement("div");
  bubble.className = "bubble " + role;
  bubble.textContent = text;
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}
function speak(text) {
  if (!byId("readAloud").checked || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "pt-BR";
  utterance.rate = 1;
  window.speechSynthesis.speak(utterance);
}
async function sendMessage(value) {
  const text = value.trim();
  if (!text || !token || sendButton.disabled) return;
  byId("messageInput").value = "";
  appendMessage(text, "user");
  sendButton.disabled = true;
  byId("helper").textContent = "Huli está processando...";
  try {
    const result = await api("/v1/messages", {method:"POST", body:{text}});
    appendMessage(result.text || "Comando processado.", "assistant");
    speak(result.text || "");
  } catch (error) {
    appendMessage(error.message || "Não consegui responder.", "error");
  } finally {
    sendButton.disabled = false;
    byId("helper").textContent = "Voz opcional; depende do navegador.";
    byId("messageInput").focus();
  }
}
loginForm.addEventListener("submit", async event => {
  event.preventDefault();
  loginButton.disabled = true;
  byId("loginError").textContent = "";
  try {
    const data = await api("/v1/auth/login", {
      method:"POST",
      body:{username:byId("username").value.trim(),password:byId("password").value}
    });
    token = data.access_token;
    showChat(data.user.username);
    if (data.password_upgrade_recommended) {
      appendMessage("Sua senha antiga é curta. Atualize-a no computador principal antes de usar acesso privado.", "assistant");
    }
  } catch (error) {
    byId("loginError").textContent = error.message || "Não foi possível entrar.";
  } finally {
    loginButton.disabled = false;
    byId("password").value = "";
  }
});
messageForm.addEventListener("submit", event => {
  event.preventDefault();
  sendMessage(byId("messageInput").value);
});
byId("suggestions").addEventListener("click", event => {
  const button = event.target.closest("button[data-command]");
  if (button) sendMessage(button.dataset.command);
});
byId("logout").addEventListener("click", async () => {
  if (recognition) recognition.abort();
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  try { await api("/v1/auth/logout", {method:"POST"}); } catch (_) { /* clear locally regardless */ }
  messages.replaceChildren();
  const p = document.createElement("p"); p.className = "welcome";
  p.textContent = "Huli conectada. Envie uma mensagem ou toque no microfone para falar.";
  messages.appendChild(p);
  showLogin();
});
byId("microphone").addEventListener("click", () => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    byId("helper").textContent = "Seu navegador não oferece reconhecimento de voz. Use o teclado.";
    return;
  }
  if (!microphoneConfirmed) {
    if (!window.confirm("O reconhecimento de fala é fornecido pelo navegador e poderá processar áudio em serviços externos. Deseja usar o microfone?")) return;
    microphoneConfirmed = true;
  }
  if (recognition) { recognition.stop(); return; }
  recognition = new Recognition();
  recognition.lang = "pt-BR";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  byId("microphone").classList.add("active");
  byId("helper").textContent = "Ouvindo... toque novamente para parar.";
  recognition.onresult = event => {
    const transcript = event.results[0][0].transcript;
    byId("messageInput").value = transcript;
    sendMessage(transcript);
  };
  recognition.onerror = event => {
    byId("helper").textContent = "Microfone: " + (event.error || "não disponível");
  };
  recognition.onend = () => {
    recognition = null;
    byId("microphone").classList.remove("active");
  };
  try { recognition.start(); } catch (_) {
    recognition = null;
    byId("microphone").classList.remove("active");
    byId("helper").textContent = "Não consegui iniciar o microfone.";
  }
});
(async () => {
  const indicator = document.querySelector(".dot");
  try {
    await api("/health");
    byId("connection").textContent = "Servidor online";
  } catch (_) {
    indicator.classList.add("offline");
    byId("connection").textContent = "Servidor indisponível";
    byId("loginError").textContent = "Não foi possível conectar ao servidor Huli.";
  }
})();
