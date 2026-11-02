module.exports = async (page, assert) => {
  assert.equal(await page.locator('#points li').count(), 3)
  await page.locator('#points li').nth(1).getByRole('button', {name: 'delete'}).click()
  assert.equal(await page.locator('#points li').count(), 2)
  const exported = await page.evaluate(() => JSON.stringify(window.vanX.compact(window.points)))
  assert.equal(exported, '["1,2","3,4"]')
  const r = await page.evaluate(() => {
    const data = window.vanX.reactive({list: [1, 2, 3], group: {a: [1, 2]}})
    delete data.list[1]
    return JSON.stringify(window.vanX.compact(data))
  })
  assert.equal(r, '{"list":[1,3],"group":{"a":[1,2]}}')
}
