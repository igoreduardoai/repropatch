module.exports = async (page, assert) => {
  assert.equal(await page.locator('#tasks li').count(), 3)
  const r = await page.evaluate(async () => {
    const {vanX} = window
    const rows = vanX.reactive([{text: "x"}, {text: "y"}])
    vanX.replace(rows, [{text: "p"}, {text: "q"}, {text: "r"}])
    const obj = vanX.reactive({a: 1, b: {c: 2}})
    vanX.replace(obj, {b: {c: 3}, d: 4})
    return [rows.map(x => x.text).join(), JSON.stringify(obj)]
  })
  assert.deepEqual(r, ["p,q,r", '{"b":{"c":3},"d":4}'])
}
