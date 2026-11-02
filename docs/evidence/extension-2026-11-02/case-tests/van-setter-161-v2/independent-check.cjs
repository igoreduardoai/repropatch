// Independent checks adapted from the upstream VanJS tests added in commit 52a3696 (MIT).
module.exports = async (page, assert) => {
  const r = await page.evaluate(() => {
    const {van} = window, out = {}
    const safe = f => { try { return f() } catch (e) { return 'THREW ' + e.name } }
    out.svg = safe(() => { van.tags.a({href: 'https://vanjs.org/'}); const {a: svgA} = van.tags('http://www.w3.org/2000/svg'); return svgA({href: '#icon'}).getAttribute('href') })
    out.auto = safe(() => { const name = 'rp-element-x'; const t = van.tags[name]; t({customValue: 'before registration'})
      class E extends HTMLElement { constructor() { super(); this._v = '' } get customValue() { return this._v } set customValue(v) { this._v = v } }
      customElements.define(name, E); return t({customValue: 'after registration'}).customValue })
    out.builtin = safe(() => { van.tags.button({customValue: 'ordinary button'})
      class B extends HTMLButtonElement { constructor() { super(); this._v = '' } get customValue() { return this._v } set customValue(v) { this._v = v } }
      customElements.define('rp-button-x', B, {extends: 'button'}); return van.tags.button({is: 'rp-button-x', customValue: 'customized button'}).customValue })
    out.html = safe(() => { const a = van.tags.a({href: 'https://example.com/x'}); const i = van.tags.input({value: 'v'}); return [a.getAttribute('href'), i.value] })
    out.svgOther = safe(() => { const {circle} = van.tags('http://www.w3.org/2000/svg'); return circle({cx: '5', r: '2'}).outerHTML })
    return out
  })
  assert.equal(r.svg, '#icon')
  assert.equal(r.auto, 'after registration')
  assert.equal(r.builtin, 'customized button')
  assert.deepEqual(r.html, ['https://example.com/x', 'v'])
  assert.equal(r.svgOther, '<circle cx="5" r="2"></circle>')
  await page.click('#render-icon'); await page.waitForTimeout(50)
  assert.equal(await page.locator('#svg-link').getAttribute('href'), '#top')
}
