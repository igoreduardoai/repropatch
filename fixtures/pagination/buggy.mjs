export function pageRows(rows, status, page, size) {
  // Fixture bug: the filter is incorrectly dropped after the first page.
  const filtered = page === 1 ? rows.filter(r => r.status === status) : rows;
  const start = (page - 1) * size;
  return { rows: filtered.slice(start, start + size), total: filtered.length };
}
