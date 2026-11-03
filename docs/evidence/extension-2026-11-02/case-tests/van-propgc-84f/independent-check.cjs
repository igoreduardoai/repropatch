// Independent checks adapted from the upstream VanJS tests added in commit 84f30ae (MIT).
module.exports = async (page, assert) => {
  const r = await page.evaluate(async () => {
    const {van} = window, {div} = van.tags, out = {}
    const hiddenDom = document.createElement('div'); document.body.appendChild(hiddenDom)
    {
      const value = van.state("A"), visible = van.state(true)
      let titleCalls = 0, deriveCalls = 0, childCalls = 0
      const label = van.derive(() => (++deriveCalls, value.val))
      const row = div({title: () => (++titleCalls, value.val)}, "Row")
      const stateRow = div({title: value}), labelRow = div({title: label})
      const childHost = div(() => (++childCalls, value.val))
      van.add(hiddenDom, () => visible.val ? row : null, stateRow, labelRow, childHost)
      value.val = "B"; await Promise.resolve()
      out.first = [titleCalls, deriveCalls, childCalls, row.title, stateRow.title, labelRow.title]
      visible.val = false; await Promise.resolve()
      stateRow.remove(); labelRow.remove(); childHost.firstChild.remove()
      out.after = []
      for (const next of ["C", "D"]) {
        value.val = next; await Promise.resolve()
        out.after.push([titleCalls, childCalls, row.title, stateRow.title, labelRow.title, label.val])
      }
      out.deriveCalls = deriveCalls
    }
    hiddenDom.innerHTML = ''
    {
      const value = van.state("A"); let row, calls = 0
      van.add(hiddenDom, () => div(row = div({title: () => (++calls, value.val)})))
      value.val = "B"; await Promise.resolve()
      out.r1 = calls
      row.remove(); value.val = "C"; await Promise.resolve()
      out.r2 = [calls, row.title, hiddenDom.firstChild.isConnected]
    }
    hiddenDom.remove()
    return out
  })
  assert.deepEqual(r.first, [2, 2, 2, "B", "B", "B"])
  assert.deepEqual(r.after, [[2, 2, "B", "B", "B", "C"], [2, 2, "B", "B", "B", "D"]])
  assert.equal(r.deriveCalls, 4)
  assert.equal(r.r1, 2)
  assert.deepEqual(r.r2, [2, "B", true])
  await page.click('#tick'); await page.waitForTimeout(50)
  const before = await page.evaluate(() => window.getRecomputes())
  await page.click('#close'); await page.waitForTimeout(50)
  for (let i = 0; i < 3; ++i) { await page.click('#tick'); await page.waitForTimeout(50) }
  assert.equal(await page.evaluate(() => window.getRecomputes()), before)
}
