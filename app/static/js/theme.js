// Light / dark theme. Loaded in <head> (no defer) so the saved theme is applied before first paint.
// Order of precedence: the user's saved choice, then the operating system setting.
(function () {
  var KEY = "idns-theme";
  var root = document.documentElement;
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function read() {
    try {
      var v = window.localStorage.getItem(KEY);
      return v === "dark" || v === "light" ? v : null;
    } catch (e) { return null; }   // storage can be blocked (private mode)
  }
  function write(v) {
    try { window.localStorage.setItem(KEY, v); } catch (e) { /* choice just won't persist */ }
  }
  function system() { return mq && mq.matches ? "dark" : "light"; }
  function current() { return root.getAttribute("data-theme") === "dark" ? "dark" : "light"; }

  function labelButtons() {
    var next = current() === "dark" ? "light" : "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      // labels are translated on the server and handed over as data attributes
      var text = btn.getAttribute(next === "dark" ? "data-label-to-dark" : "data-label-to-light") || "";
      btn.setAttribute("aria-label", text);
      btn.setAttribute("title", text);
      btn.setAttribute("aria-pressed", current() === "dark" ? "true" : "false");
    });
  }
  function apply(theme) {
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-bs-theme", theme);   // Bootstrap 5.3 dark mode
    labelButtons();
  }

  apply(read() || system());

  if (mq) {
    var onSystemChange = function () { if (!read()) apply(system()); };   // follow the OS until the user chooses
    if (mq.addEventListener) mq.addEventListener("change", onSystemChange);
    else if (mq.addListener) mq.addListener(onSystemChange);
  }
  window.addEventListener("storage", function (e) {          // keep other open tabs in sync
    if (e.key === KEY) apply(read() || system());
  });

  document.addEventListener("DOMContentLoaded", function () {
    labelButtons();
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var next = current() === "dark" ? "light" : "dark";
        write(next);
        apply(next);
      });
    });
    // enable colour transitions only after the first paint, so loading never animates
    window.requestAnimationFrame(function () { root.classList.add("theme-ready"); });
  });
})();
