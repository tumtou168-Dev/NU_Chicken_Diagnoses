// Client-side row filter for admin tables.
// Usage: <input data-table-filter="#tableId"> filters the tbody rows of that table.
function initAdminTableFilter() {
  document.querySelectorAll("[data-table-filter]").forEach((input) => {
    const table = document.querySelector(input.dataset.tableFilter);
    if (!table) return;

    const rows = Array.from(table.querySelectorAll("tbody tr[data-row]"));
    const empty = table.querySelector("tbody tr[data-empty]");

    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      let visible = 0;
      rows.forEach((row) => {
        const match = row.textContent.toLowerCase().includes(q);
        row.hidden = !match;
        if (match) visible += 1;
      });
      if (empty) empty.hidden = visible !== 0;
    });
  });
}

window.AdminTableFilter = { init: initAdminTableFilter };
window.onReady(initAdminTableFilter);

// Number inputs with a max: a typed value above it is lowered to the max right away,
// instead of only being rejected when the form is submitted.
function initNumberMaxClamp() {
  document.addEventListener("input", (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.type !== "number" || input.max === "") return;
    const max = Number(input.max);
    if (input.value !== "" && Number(input.value) > max) input.value = input.max;
  });
}

window.onReady(initNumberMaxClamp);
