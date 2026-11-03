module.exports = async (page, assert) => {
  assert.equal(await page.locator('#left').textContent(), 'Tasks left: 3')
  for (const expected of ['Tasks left: 2', 'Tasks left: 1', 'Tasks left: 0']) {
    await page.locator('#done').click()
    await page.waitForFunction(e => document.querySelector('#left').textContent === e, expected, {timeout: 1000}).catch(() => {})
    assert.equal(await page.locator('#left').textContent(), expected)
  }
  const r = await page.evaluate(() => {
    const {van, vanX} = window
    const data = vanX.reactive([1, 2])
    const len = van.derive(() => data.length)
    const out = []
    data.pop(); out.push(len.val)
    data.push(3); out.push(len.val)
    data.push(4); out.push(len.val)
    data.pop(); out.push(len.val)
    data[5] = 9; out.push(len.val, JSON.stringify(data))
    return out
  })
  assert.deepEqual(r, [1, 2, 3, 2, 6, '[1,3,null,null,null,9]'])
}
