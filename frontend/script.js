const API_BASE = window.API_BASE || "/api";

const authCard = document.getElementById("auth-card");
const composerCard = document.getElementById("composer-card");
const authMessage = document.getElementById("auth-message");
const composeMessage = document.getElementById("compose-message");
const logoutButton = document.getElementById("logout");

const tabButtons = document.querySelectorAll(".tab-button");
const forms = document.querySelectorAll(".form");

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const composeForm = document.getElementById("compose-form");

let authToken = localStorage.getItem("jmail_token");

function setActiveForm(targetId) {
  forms.forEach((form) => form.classList.remove("active"));
  tabButtons.forEach((button) => button.classList.remove("active"));
  document.getElementById(targetId).classList.add("active");
  document
    .querySelector(`.tab-button[data-target="${targetId}"]`)
    .classList.add("active");
}

tabButtons.forEach((button) => {
  button.addEventListener("click", () => setActiveForm(button.dataset.target));
});

function showMessage(el, message, isError = false) {
  el.textContent = message;
  el.classList.toggle("error", isError);
  if (message) {
    setTimeout(() => {
      el.textContent = "";
      el.classList.remove("error");
    }, 5000);
  }
}

function updateUI() {
  if (authToken) {
    authCard.classList.add("hidden");
    composerCard.classList.remove("hidden");
  } else {
    authCard.classList.remove("hidden");
    composerCard.classList.add("hidden");
  }
}

async function request(endpoint, options = {}) {
  const headers = options.headers || {};
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    const data = await request("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    authToken = data.token;
    localStorage.setItem("jmail_token", authToken);
    showMessage(authMessage, "Logged in successfully!");
    updateUI();
  } catch (error) {
    showMessage(authMessage, error.message, true);
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;
    const display_name = document.getElementById("register-display").value;
    const data = await request("/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    });
    authToken = data.token;
    localStorage.setItem("jmail_token", authToken);
    showMessage(authMessage, "Account created! You are now logged in.");
    updateUI();
  } catch (error) {
    showMessage(authMessage, error.message, true);
  }
});

composeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const to = document.getElementById("compose-to").value;
    const subject = document.getElementById("compose-subject").value;
    const reply_to = document.getElementById("compose-reply").value;
    const body = document.getElementById("compose-body").value;
    await request("/send", {
      method: "POST",
      body: JSON.stringify({ to, subject, reply_to, body }),
    });
    showMessage(composeMessage, "Email sent successfully!");
    composeForm.reset();
  } catch (error) {
    showMessage(composeMessage, error.message, true);
  }
});

logoutButton.addEventListener("click", () => {
  authToken = null;
  localStorage.removeItem("jmail_token");
  composeForm.reset();
  showMessage(composeMessage, "Logged out.");
  updateUI();
});

updateUI();
