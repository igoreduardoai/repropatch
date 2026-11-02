module.exports = async (page, assert) => {
  await page.click('#render-icon')
  assert.equal(await page.locator('#status').innerText(), 'Rendered SVG link, href=#top')
  assert.equal(await page.locator('#svg-link').getAttribute('href'), '#top')
}
