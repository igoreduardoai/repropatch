module.exports = async (page, assert) => {
  await page.locator('#sort').click()
  const texts = await page.locator('#tasks li').allTextContents()
  assert.deepEqual(texts, ['Add docs', 'Fix login bug', 'Write release notes'])
  const data = await page.evaluate(() => window.tasks.map(x => x.text).join(','))
  assert.equal(data, 'Add docs,Fix login bug,Write release notes')
}
