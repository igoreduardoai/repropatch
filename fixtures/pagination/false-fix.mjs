export function pageRows(rows, status, page, size) {
  // Deliberately incorrect fixture patch: inactive rows can never be selected.
  const filtered = rows.filter(r => r.status === "active");
  const start = (page - 1) * size;
  return { rows: filtered.slice(start, start + size), total: filtered.length };
}
