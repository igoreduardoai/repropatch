export function pageRows(rows, status, page, size) {
  const filtered = rows.filter(r => r.status === status);
  const start = (page - 1) * size;
  return { rows: filtered.slice(start, start + size), total: filtered.length };
}
