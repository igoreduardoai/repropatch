module.exports = async (page, assert) => {
  await page.waitForSelector('#points li')
  await page.evaluate(() => { delete window.points[1] })
  await page.evaluate(() => document.querySelector('#export').click())
  assert.equal(await page.locator('#exported').textContent(), '["1,2","3,4"]')
  const r = await page.evaluate(() => {
    const data = window.vanX.reactive({list: [1, 2, 3], group: {a: [1, 2]}})
    delete data.list[1]
    return JSON.stringify(window.vanX.compact(data))
  })
  assert.equal(r, '{"list":[1,3],"group":{"a":[1,2]}}')
}
