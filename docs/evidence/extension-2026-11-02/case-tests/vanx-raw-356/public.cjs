module.exports = async (page, assert) => {
  assert.equal(await page.locator('h2').textContent(), 'Profile snapshot (vanX.raw)')
  const r = await page.evaluate(async () => {
    const {vanX} = window
    const o = vanX.reactive({a: 1, b: {c: 2}})
    return [vanX.raw(o).a, vanX.raw(o).b.c]
  })
  assert.deepEqual(r, [1, 2])
}
