// Password fields: show/hide toggle, live strength meter, live "passwords match" check.
// Markup comes from the password_field() macro in layouts/_admin_macros.html.
function initPasswordUI() {
  document.querySelectorAll("[data-pw-toggle]").forEach((btn) => {
    const input = btn.parentElement.querySelector("input[data-pw-input]");
    if (!input) return;
    btn.addEventListener("click", () => {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.querySelector("i").className = showing ? "bi bi-eye" : "bi bi-eye-slash";
    });
  });

  const LEVELS = ["weak", "weak", "fair", "good", "strong", "strong"];

  function scorePassword(value) {
    let score = 0;
    if (value.length >= 8) score += 1;
    if (value.length >= 12) score += 1;
    if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
    if (/[0-9]/.test(value)) score += 1;
    if (/[^A-Za-z0-9]/.test(value)) score += 1;
    return score;
  }

  document.querySelectorAll("[data-pw-meter]").forEach((meter) => {
    const input = meter.closest(".mb-3").querySelector("input[data-pw-input]");
    const bars = meter.querySelectorAll(".pw-meter-bars span");
    const text = meter.querySelector("[data-pw-meter-text]");
    if (!input || !text) return;
    const labels = {
      weak: meter.dataset.labelWeak,
      fair: meter.dataset.labelFair,
      good: meter.dataset.labelGood,
      strong: meter.dataset.labelStrong,
    };

    input.addEventListener("input", () => {
      const value = input.value;
      meter.hidden = value.length === 0;
      if (!value) return;

      const score = scorePassword(value);
      const level = LEVELS[score];
      const filled = { weak: 1, fair: 2, good: 3, strong: 4 }[level];

      bars.forEach((bar, i) => {
        bar.className = i < filled ? `is-filled pw-${level}` : "";
      });
      text.textContent = labels[level];
      text.className = `pw-meter-text pw-${level}`;
    });
  });

  document.querySelectorAll("[data-pw-match]").forEach((el) => {
    const target = document.getElementById(el.dataset.pwMatchTarget);
    const input = el.closest(".mb-3").querySelector("input[data-pw-input]");
    if (!target || !input) return;

    const update = () => {
      if (!input.value) {
        el.hidden = true;
        return;
      }
      el.hidden = false;
      const match = input.value === target.value;
      el.textContent = match ? el.dataset.labelMatch : el.dataset.labelMismatch;
      el.className = "pw-match " + (match ? "text-success" : "text-danger");
    };
    input.addEventListener("input", update);
    target.addEventListener("input", update);
  });
}

window.PasswordUI = { init: initPasswordUI };
window.onReady(initPasswordUI);

// Success / info flash messages ("Logged in successfully", "Saved", ...) show as a snackbar at the
// top center and close themselves after 5s; hovering holds one open. Warnings and errors are
// inline alerts that stay until dismissed.
const FLASH_AUTOHIDE_MS = 5000;

function initFlashAutoHide() {
  // Drop in just below the top bar — its height varies (long titles wrap), so measure it.
  const header = document.querySelector(".page-header");
  document.querySelectorAll(".snackbar-stack").forEach((stack) => {
    if (header) stack.style.top = `${Math.round(header.getBoundingClientRect().bottom) + 12}px`;
  });
  document.querySelectorAll(".snackbar[data-autohide]:not([data-autohide-armed])").forEach((bar) => {
    bar.setAttribute("data-autohide-armed", "");
    let hovered = false;
    let expired = false;
    const close = () => {
      if (!bar.isConnected || bar.classList.contains("is-leaving")) return;
      bar.classList.add("is-leaving");
      bar.addEventListener("animationend", () => bar.remove(), { once: true });
      setTimeout(() => bar.remove(), 400);   // in case animations are disabled
    };
    bar.querySelector(".snackbar-close")?.addEventListener("click", close);
    bar.addEventListener("mouseenter", () => { hovered = true; });
    bar.addEventListener("mouseleave", () => { hovered = false; if (expired) close(); });
    setTimeout(() => { expired = true; if (!hovered) close(); }, FLASH_AUTOHIDE_MS);
  });
}

window.FlashAutoHide = { init: initFlashAutoHide };
window.onReady(initFlashAutoHide);
