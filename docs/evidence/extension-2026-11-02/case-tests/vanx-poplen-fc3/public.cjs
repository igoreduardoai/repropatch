module.exports = async (page, assert) => {
  assert.equal(await page.locator('h2').textContent(), 'Release checklist')
  assert.equal(await page.locator('#left').textContent(), 'Tasks left: 3')
  const r = await page.evaluate(() => {
    const {van, vanX} = window
    const data = vanX.reactive([1, 2])
    const len = van.derive(() => data.length)
    data.push(3); data.push(4)
    return [len.val, JSON.stringify(data)]
  })
  assert.deepEqual(r, [4, '[1,2,3,4]'])
}
