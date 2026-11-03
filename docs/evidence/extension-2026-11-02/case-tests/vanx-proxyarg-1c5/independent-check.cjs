// Independent checks for the upstream fix in commit 1c580f0 (MIT): non-state properties (length, array methods) must be readable through the reactive proxy.
module.exports = async (page, assert) => {
  const r = await page.evaluate(() => {
    const {van, vanX} = window, out = {}
    try {
      const arr = vanX.reactive([1, 2, 3])
      arr.push(4)
      out.arr = [arr.length, arr.map(x => x * 2).join(","), JSON.stringify(arr)]
    } catch (e) { out.err = "threw: " + e.message }
    return out
  })
  assert.equal(r.err, undefined)
  assert.deepEqual(r.arr, [4, "2,4,6,8", "[1,2,3,4]"])
  assert.equal(await page.locator('#summary').textContent(), 'Items: 2 (apple, pear)')
  await page.click('#add'); await page.waitForTimeout(150)
  assert.equal(await page.locator('#status').textContent(), '')
  assert.equal(await page.locator('#summary').textContent(), 'Items: 3 (apple, pear, plum)')
}
