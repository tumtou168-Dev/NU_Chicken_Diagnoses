// Swaps the Khmer/English language without a full page reload.
//
// The site renders all text server-side from a "lang" cookie (see app/i18n.py), so switching
// language really means: set the cookie, then re-render the current page and drop the result
// in place of #appShell. fetch() follows the /lang/<code> -> redirect chain itself and applies
// the Set-Cookie header along the way, so a single request returns the already-translated page.
window.onReady(function () {
  let swapping = false;

  function reexecuteScripts(container) {
    // Scripts inserted via innerHTML never run — clone each into a fresh <script> to force it.
    container.querySelectorAll("script").forEach((old) => {
      const fresh = document.createElement("script");
      for (const attr of old.attributes) fresh.setAttribute(attr.name, attr.value);
      fresh.textContent = old.textContent;
      old.replaceWith(fresh);
    });
  }

  function reinitSharedScripts() {
    window.ThemeUI && window.ThemeUI.init();
    window.PasswordUI && window.PasswordUI.init();
    window.FlashAutoHide && window.FlashAutoHide.init();
    window.AdminTableFilter && window.AdminTableFilter.init();
    window.ChatWidget && window.ChatWidget.init();
  }

  // The freshly-fetched page is a plain GET render, so anything the visitor filled in but hasn't
  // submitted yet (checked symptoms on the diagnose page, a half-typed filter, ...) would come
  // back empty. Snapshot it before the swap and re-apply it after, so in-progress input survives
  // a language switch the same way it would survive nothing happening at all.
  const RESTORABLE_TYPES = ["text", "search", "email", "tel", "url", "number", "checkbox", "radio"];

  function fieldKey(el) {
    return el.name || el.id || null;
  }

  function snapshotFormState(container) {
    const state = [];
    container.querySelectorAll("input, textarea, select").forEach((el) => {
      const key = fieldKey(el);
      if (!key || key === "csrf_token") return;
      const tag = el.tagName.toLowerCase();
      if (tag === "input" && !RESTORABLE_TYPES.includes(el.type)) return;   // skip password/file/hidden/submit/...

      if (el.type === "checkbox" || el.type === "radio") {
        if (el.checked) state.push({ key, value: el.value, kind: el.type });
      } else if (el.value) {
        state.push({ key, value: el.value, kind: tag === "select" ? "select" : "text" });
      }
    });
    return state;
  }

  function restoreFormState(container, state) {
    for (const item of state) {
      let el;
      if (item.kind === "checkbox" || item.kind === "radio") {
        el = container.querySelector(`[name="${CSS.escape(item.key)}"][value="${CSS.escape(item.value)}"]`)
          || container.querySelector(`#${CSS.escape(item.key)}`);
        if (el) { el.checked = true; el.dispatchEvent(new Event("change", { bubbles: true })); }
      } else {
        el = container.querySelector(`[name="${CSS.escape(item.key)}"]`) || container.querySelector(`#${CSS.escape(item.key)}`);
        if (el) { el.value = item.value; el.dispatchEvent(new Event("input", { bubbles: true })); }
      }
    }
  }

  function swapTo(html) {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const newShell = doc.getElementById("appShell");
    const oldShell = document.getElementById("appShell");
    if (!newShell || !oldShell) return false;

    const formState = snapshotFormState(oldShell);

    document.title = doc.title;
    const lang = doc.documentElement.getAttribute("lang");
    if (lang) document.documentElement.setAttribute("lang", lang);

    window.ChatWidget && window.ChatWidget.destroy && window.ChatWidget.destroy();
    oldShell.innerHTML = newShell.innerHTML;
    reexecuteScripts(oldShell);
    reinitSharedScripts();
    restoreFormState(oldShell, formState);
    return true;
  }

  document.addEventListener("click", function (e) {
    const link = e.target.closest(".lang-switch a");
    if (!link || swapping) return;
    e.preventDefault();

    swapping = true;
    const shell = document.getElementById("appShell");
    shell.classList.add("lang-swapping");

    // The diagnose page only shows a result after a POST — a plain GET re-render (what a
    // language switch normally does) would show the blank symptom picker instead of the
    // result the visitor is currently looking at. Detect that case and resubmit the same
    // symptoms so the result comes back translated instead of disappearing.
    const diagnoseForm = shell.querySelector("#diagnoseForm");
    const resultsEl = shell.querySelector("#results");
    const onResultsPage = !!(diagnoseForm && resultsEl);
    const symptomIds = onResultsPage
      ? Array.from(shell.querySelectorAll('input[name="symptoms"]:checked')).map((el) => el.value)
      : [];
    const csrfInput = diagnoseForm && diagnoseForm.querySelector('input[name="csrf_token"]');
    const formAction = diagnoseForm && diagnoseForm.action;
    const existingCaseId = resultsEl && resultsEl.dataset.caseId;

    fetch(link.href, { credentials: "same-origin" })
      .then((r) => {
        if (!r.ok) throw new Error("lang switch failed: " + r.status);
        return r.text();
      })
      .then((html) => {
        if (onResultsPage && symptomIds.length && formAction && csrfInput) {
          const body = new URLSearchParams();
          symptomIds.forEach((id) => body.append("symptoms", id));
          body.set("csrf_token", csrfInput.value);
          // Tell the server this is a re-render, not a new diagnosis, so it reuses the
          // existing case instead of recording a duplicate history entry.
          if (existingCaseId) body.set("reuse_case_id", existingCaseId);
          return fetch(formAction, { method: "POST", credentials: "same-origin", body }).then((r) => r.text());
        }
        return html;
      })
      .then((html) => {
        if (!swapTo(html)) window.location.href = link.href;
      })
      .catch(() => {
        window.location.href = link.href;   // fall back to a normal navigation
      })
      .finally(() => {
        swapping = false;
        const shell = document.getElementById("appShell");
        if (shell) shell.classList.remove("lang-swapping");
      });
  });
});
