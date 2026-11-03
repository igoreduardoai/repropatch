module.exports = async (page, assert) => {
  assert.equal(await page.locator('h2').textContent(), 'Playlist')
  assert.equal(await page.locator('#count').textContent(), 'Songs: 4')
  const r = await page.evaluate(() => {
    const {vanX} = window
    const data = vanX.reactive([1, 2])
    vanX.replace(data, _ => [3, 4, 5])
    return JSON.stringify(data)
  })
  assert.equal(r, '[3,4,5]')
}
