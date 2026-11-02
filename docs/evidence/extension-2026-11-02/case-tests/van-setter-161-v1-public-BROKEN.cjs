module.exports = async (page, assert) => {
  assert.equal(await page.locator('#html-link').getAttribute('href'), 'https://vanjs.org/')
  const r = await page.evaluate(() => {
    const {div, input, button} = window.van.tags
    const i = input({type: 'text', value: 'abc'}), b = button({disabled: true, onclick: () => window.__n = (window.__n || 0) + 1}, 'x')
    const s = window.van.state('red'), d = div({style: () => 'color: ' + s.val})
    return [i.value, b.disabled, d.getAttribute('style')]
  })
  assert.deepEqual(r, ['abc', true, 'color: red'])
}
