module.exports = async (page, assert) => {
  await page.click('#render-icon')
  await page.waitForFunction(() => document.querySelector('#status')?.textContent.includes('Rendered') || document.querySelector('#status')?.textContent.includes('Error'))
  assert.equal(await page.locator('#status').textContent(), 'Rendered SVG link, href=#top')
  assert.equal(await page.locator('#svg-link').getAttribute('href'), '#top')
  assert.equal(await page.locator('#html-link').getAttribute('href'), 'https://vanjs.org/')
}
