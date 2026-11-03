// Independent checks adapted from the upstream VanX test added in commit acb8ba8 (MIT).
module.exports = async (page, assert) => {
  const r = await page.evaluate(() => {
    const {vanX} = window, out = []
    const data = vanX.reactive([1, 2, 3])
    vanX.replace(data, _ => [1, 2, 3, 4]); out.push(JSON.stringify(data))
    vanX.replace(data, _ => [1, 2]); out.push(JSON.stringify(data))
    vanX.replace(data, _ => []); out.push(JSON.stringify(data))
    return out
  })
  assert.deepEqual(r, ['[1,2,3,4]', '[1,2]', '[]'])
  await page.click('#top2'); await page.waitForTimeout(150)
  assert.equal(await page.locator('#count').textContent(), 'Songs: 2')
  assert.equal(await page.locator('#json').textContent(), 'Saved as: ["Blue","Gold"]')
}
