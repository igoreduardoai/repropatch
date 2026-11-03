module.exports = async (page, assert) => {
  assert.equal(await page.locator('h2').textContent(), 'Shopping cart')
  const r = await page.evaluate(() => {
    const {vanX} = window
    const o = vanX.reactive({a: 1, b: "x"})
    o.a = 2; o.b = "y"
    return [o.a, o.b]
  })
  assert.deepEqual(r, [2, "y"])
}
