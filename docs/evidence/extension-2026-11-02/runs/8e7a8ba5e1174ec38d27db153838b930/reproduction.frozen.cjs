module.exports = async (page, assert) => {
  await page.click('#close')
  await page.click('#tick')
  await page.waitForTimeout(50)
  const afterOne = await page.evaluate(() => window.getRecomputes())
  await page.click('#tick')
  await page.waitForTimeout(50)
  const afterTwo = await page.evaluate(() => window.getRecomputes())
  assert.equal(afterTwo, afterOne, `recomputes increased after removal: ${afterOne} -> ${afterTwo}`)
}
