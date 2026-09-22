// Runs fn immediately if the document has already finished parsing, otherwise waits for
// DOMContentLoaded. Needed because DOMContentLoaded only ever fires once per page: after an
// AJAX content swap (see lang-switch.js) readyState is already "complete", so a script that
// re-registers a plain DOMContentLoaded listener would never run again.
window.onReady = function (fn) {
  if (document.readyState !== "loading") fn();
  else document.addEventListener("DOMContentLoaded", fn);
};
