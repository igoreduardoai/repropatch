module.exports = async (page, assert) => {
  assert.equal(await page.locator('#summary').textContent(), 'Items: 2 (apple, pear)')
  await page.locator('#add').click()
  await page.waitForTimeout(100)
  assert.equal(await page.locator('#summary').textContent(), 'Items: 3 (apple, pear, plum)')
  assert.equal(await page.locator('#status').textContent(), '')
  // Non-state properties must be readable through proxy
  const r = await page.evaluate(() => {
    const o = window.vanX.reactive({items: ['a','b']})
    return [o.items.length, typeof o.items.push, typeof o.items.map, o.items.join('-')]
  })
  assert.deepEqual(r, [2, 'function', 'function', 'a-b'])
}
