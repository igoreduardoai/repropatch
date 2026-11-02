module.exports = async (page, assert) => {
  assert.equal(await page.locator('#points li').count(), 3)
  const r = await page.evaluate(() => {
    const data = window.vanX.reactive({list: [1, 2, 3], group: {a: [1, 2]}})
    delete data.list[1]
    return JSON.stringify(window.vanX.compact(data))
  })
  assert.equal(r, '{"list":[1,3],"group":{"a":[1,2]}}')
}
