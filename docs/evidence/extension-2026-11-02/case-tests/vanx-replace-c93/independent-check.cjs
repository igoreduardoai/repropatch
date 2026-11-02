// Independent checks adapted from the upstream VanJS tests added in commit c93a153 (MIT).
module.exports = async (page, assert) => {
  const r = await page.evaluate(async () => {
    const {vanX} = window, out = {}
    for (const cb of [false, true]) {
      const rows = vanX.reactive([{text: "B"}, {text: "A"}]); const [b, a] = rows
      const sorted = rows.toSorted((x, y) => x.text.localeCompare(y.text))
      vanX.replace(rows, cb ? xs => xs.toSorted((x, y) => x.text.localeCompare(y.text)) : sorted)
      out['sort' + cb] = [rows.map(x => x.text).join(), rows[0] === a && rows[1] === b, b.text]
    }
    { const rows = vanX.reactive([{text: "B"}, {text: "A"}]); const [b, a] = rows
      vanX.replace(rows, xs => xs.filter(x => x === a)); out.filter = [rows.length, rows[0] === a, b.text] }
    { const rows = vanX.reactive([{text: "B"}, {text: "A"}]); const b = rows[0]
      vanX.replace(rows, [{text: "C"}, b]); out.insert = [rows.map(x => x.text).join(), rows[1] === b, b.text] }
    { const rows = vanX.reactive({k1: {text: "B"}, k2: {text: "A"}}); const {k1: b, k2: a} = rows
      vanX.replace(rows, {k1: a, k2: b}); out.swap = [rows.k1.text + "," + rows.k2.text, rows.k1 === a && rows.k2 === b] }
    { const obj = vanX.reactive({left: {text: "B"}, right: {}}); const b = obj.left, right = obj.right
      vanX.replace(obj, {left: {text: "C"}, right: {saved: b}}); out.move = [obj.left.text, b.text, obj.right.saved === b, obj.right === right] }
    { const rows = vanX.reactive([{text: "B"}, {text: "A"}]); const [b, a] = rows
      vanX.replace(rows, [a, b, a]); const m1 = [rows.map(x => x.text).join(), rows[0] === a && rows[1] === b && rows[2] === a]
      vanX.replace(rows, [b, a]); out.multi = [m1, rows.map(x => x.text).join(), rows[0] === b && rows[1] === a] }
    { const rows = vanX.reactive([{text: "A", done: false}]); const a = rows[0]
      vanX.replace(rows, [{text: "A", done: true}]); out.fresh = [rows[0] === a, a.done] }
    return out
  })
  assert.deepEqual(r.sortfalse, ["A,B", true, "B"])
  assert.deepEqual(r.sorttrue, ["A,B", true, "B"])
  assert.deepEqual(r.filter, [1, true, "B"])
  assert.deepEqual(r.insert, ["C,B", true, "B"])
  assert.deepEqual(r.swap, ["A,B", true])
  assert.deepEqual(r.move, ["C", "B", true, true])
  assert.deepEqual(r.multi, [["A,B,A", true], "B,A", true])
  assert.deepEqual(r.fresh, [true, true])
  await page.click('#sort'); await page.waitForTimeout(100)
  assert.equal((await page.locator('#tasks li').allTextContents()).join('|'), 'Add docs|Fix login bug|Write release notes')
}
