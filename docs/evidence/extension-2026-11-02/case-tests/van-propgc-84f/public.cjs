module.exports = async (page, assert) => {
  assert.equal(await page.locator('h2').textContent(), 'Price ticker')
  const r = await page.evaluate(async () => {
    const {van} = window, {div} = van.tags
    const host = document.createElement('div'); document.body.appendChild(host)
    const s = van.state("a")
    const d = div({title: () => "t-" + s.val}, () => "c-" + s.val)
    van.add(host, d)
    s.val = "b"; await new Promise(r => setTimeout(r, 30))
    const out = [d.title, d.textContent]; host.remove(); return out
  })
  assert.deepEqual(r, ["t-b", "c-b"])
}
