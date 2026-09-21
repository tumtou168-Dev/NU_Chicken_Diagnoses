// Dashboard charts: hover/focus tooltips and the chart <-> table toggle.
// Labels come from the database, so they are inserted with textContent only.
document.addEventListener("DOMContentLoaded", () => {
  const tip = document.createElement("div");
  tip.className = "viz-tooltip";
  tip.hidden = true;
  const value = document.createElement("div");
  value.className = "viz-tooltip-value";
  const label = document.createElement("div");
  label.className = "viz-tooltip-label";
  tip.append(value, label);
  document.body.appendChild(tip);

  const place = (x, y) => {
    const pad = 12;
    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    let left = x + pad;
    let top = y - h - pad;
    if (left + w > window.innerWidth - 8) left = x - w - pad;
    if (top < 8) top = y + pad;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = top + "px";
  };
  const show = (el, x, y) => {
    value.textContent = el.dataset.value;
    label.textContent = el.dataset.label;
    tip.hidden = false;
    place(x, y);
  };
  const hide = () => { tip.hidden = true; };

  document.querySelectorAll("[data-tip]").forEach((el) => {
    el.addEventListener("pointermove", (e) => show(el, e.clientX, e.clientY));
    el.addEventListener("pointerleave", hide);
    el.addEventListener("focus", () => {
      const r = el.getBoundingClientRect();
      show(el, r.left + r.width / 2, r.top);
    });
    el.addEventListener("blur", hide);
  });

  document.querySelectorAll("[data-viz-toggle]").forEach((btn) => {
    const card = document.querySelector(btn.dataset.vizToggle);
    if (!card) return;
    const text = btn.querySelector("span");
    btn.addEventListener("click", () => {
      const chart = card.querySelector(".viz-chart");
      const table = card.querySelector(".viz-table");
      if (!chart || !table) return;
      const showTable = table.hidden;
      table.hidden = !showTable;
      chart.hidden = showTable;
      hide();
      text.textContent = showTable ? btn.dataset.labelChart : btn.dataset.labelTable;
    });
  });
});
