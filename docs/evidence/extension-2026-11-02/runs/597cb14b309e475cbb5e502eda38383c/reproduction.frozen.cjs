module.exports = async (page, assert) => {
  await page.click('#render-icon')
  assert.equal(await page.locator('#svg-link').count(), 1)
  assert.equal(await page.locator('#svg-link').getAttribute('href'), '#top')
  assert.match(await page.locator('#status').innerText(), /Rendered SVG link, href=#top/)
}
