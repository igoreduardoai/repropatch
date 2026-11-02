module.exports = async (page, assert) => {
  assert.equal(await page.locator('h2').textContent(), 'Greeting card')
  const r = await page.evaluate(async () => {
    const {vanX} = window
    const data = vanX.reactive({n: 1, nested: {s: "a"}, list: [1, 2]})
    data.n = 2; data.nested.s = "b"; data.list.push(3)
    return JSON.stringify(data)
  })
  assert.equal(r, '{"n":2,"nested":{"s":"b"},"list":[1,2,3]}')
}
