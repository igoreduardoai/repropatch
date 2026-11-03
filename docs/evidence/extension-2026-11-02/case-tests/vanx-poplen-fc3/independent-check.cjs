// Independent checks adapted from the upstream VanX test reactive_arrayLength added in commit fc3ee4c (MIT).
module.exports = async (page, assert) => {
  const r = await page.evaluate(async () => {
    const {van, vanX} = window, out = []
    const data = vanX.reactive([])
    const length = van.derive(() => data.length)
    out.push(length.val)
    for (let i = 1; i <= 5; ++i) { data.push(i); out.push(length.val) }
    data[5] = 6; out.push(length.val)
    for (let i = 0; i < 6; ++i) { data.pop(); out.push(length.val) }
    return out
  })
  assert.deepEqual(r, [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1, 0])
  await page.click('#done'); await page.waitForTimeout(100)
  assert.equal(await page.locator('#left').textContent(), 'Tasks left: 2')
  await page.click('#done'); await page.waitForTimeout(100)
  assert.equal(await page.locator('#left').textContent(), 'Tasks left: 1')
}
