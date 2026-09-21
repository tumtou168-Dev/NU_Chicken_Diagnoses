// Client-side row filter for admin tables.
// Usage: <input data-table-filter="#tableId"> filters the tbody rows of that table.
document.addEventListener("DOMContentLoaded", () => {
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
});
