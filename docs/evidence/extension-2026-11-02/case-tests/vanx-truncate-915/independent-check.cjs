// Independent checks adapted from the upstream VanJS tests added in commit 915f0e2 (MIT).
module.exports = async (page, assert) => {
  const r = await page.evaluate(async () => {
    const {van, vanX} = window, {ul, ol, li, p, div} = van.tags
    const out = {}
    const tick = () => new Promise(r => setTimeout(r, 20))
    // clear
    { const host = document.body.appendChild(div()); const items = vanX.reactive(["A", "B"])
      van.add(host, p(() => JSON.stringify(items)), vanX.list(ul, items, v => li(v)))
      items.length = 0; await tick(); out.clear1 = host.innerHTML
      items.push("C"); await tick(); out.clear2 = host.innerHTML
      items.length = 0; items.push("D"); await tick(); out.clear3 = host.innerHTML; host.remove() }
    // truncate keeps surviving row identity
    { const host = document.body.appendChild(div()); const items = vanX.reactive(["A", "B", "C", "D", "E"])
      const dom = host.appendChild(vanX.list(ul, items, v => li(v))); const [a, b, c, d, e] = dom.childNodes
      items.length = 3; await tick(); out.t1 = dom.innerHTML
      out.t1same = dom.childNodes[0] === a && dom.childNodes[1] === b && dom.childNodes[2] === c && !d.isConnected && !e.isConnected
      --items.length; await tick(); out.t2 = dom.innerHTML; out.t2c = !c.isConnected
      out.pop = items.pop(); await tick(); out.t3 = dom.innerHTML; out.t3same = dom.firstChild === a; host.remove() }
    // sparse + two bindings
    { const host = document.body.appendChild(div()); const items = vanX.reactive(["A"]); items[4] = "E"
      const u = host.appendChild(vanX.list(ul, items, v => li(v))), o = host.appendChild(vanX.list(ol, items, v => li(v)))
      items.length = 10; await tick(); out.s1 = [u.innerHTML, o.innerHTML]
      items.length = 3; await tick(); out.s2 = [u.innerHTML, o.innerHTML, items.length, Object.keys(items).toString()]
      items[2] = "C"; items[1] = "B"; await tick(); out.s3 = [u.innerHTML, o.innerHTML]
      items.length = 0; await tick(); out.s4 = [u.childNodes.length, o.childNodes.length]; host.remove() }
    // invalid lengths throw RangeError and change nothing
    { const host = document.body.appendChild(div()); const items = vanX.reactive(["A", "B"])
      van.add(host, vanX.list(ul, items, v => li(v))); out.inv = []
      for (const len of [-1, 1.5, NaN, 2 ** 32]) { let err = null; try { items.length = len } catch (e) { err = e }
        await tick(); out.inv.push([err instanceof RangeError, JSON.stringify(items), host.innerHTML]) }
      host.remove() }
    return out
  })
  assert.equal(r.clear1, '<p>[]</p><ul></ul>')
  assert.equal(r.clear2, '<p>["C"]</p><ul><li>C</li></ul>')
  assert.equal(r.clear3, '<p>["D"]</p><ul><li>D</li></ul>')
  assert.equal(r.t1, '<li>A</li><li>B</li><li>C</li>'); assert.equal(r.t1same, true)
  assert.equal(r.t2, '<li>A</li><li>B</li>'); assert.equal(r.t2c, true)
  assert.equal(r.pop, 'B'); assert.equal(r.t3, '<li>A</li>'); assert.equal(r.t3same, true)
  assert.deepEqual(r.s1, ['<li>A</li><li>E</li>', '<li>A</li><li>E</li>'])
  assert.deepEqual(r.s2, ['<li>A</li>', '<li>A</li>', 3, '0'])
  assert.deepEqual(r.s3, ['<li>A</li><li>B</li><li>C</li>', '<li>A</li><li>B</li><li>C</li>'])
  assert.deepEqual(r.s4, [0, 0])
  for (const x of r.inv) assert.deepEqual(x, [true, '["A","B"]', '<ul><li>A</li><li>B</li></ul>'])
  // the demo itself
  await page.click('#keep2'); await page.waitForTimeout(50)
  assert.equal(await page.locator('#list li').count(), 2)
  await page.click('#clear'); await page.waitForTimeout(50)
  assert.equal(await page.locator('#list li').count(), 0)
}
