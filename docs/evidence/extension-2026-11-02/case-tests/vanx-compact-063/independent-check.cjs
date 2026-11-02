// Independent checks adapted from the upstream VanJS tests added in commit c9f2dd4 (MIT).
module.exports = async (page, assert) => {
  const r = await page.evaluate(() => {
    const {vanX} = window, out = {}
    class P { constructor(x, y) { this.x = x; this.y = y } toJSON() { return `${this.x},${this.y}` } }
    const pts = vanX.reactive([new P(1, 2), , new P(3, 4)])
    out.before = JSON.stringify(pts)
    out.after = JSON.stringify(vanX.compact(pts))
    const c = vanX.compact(vanX.reactive({p: new P(7, 8)}))
    out.nested = [c.p instanceof P, JSON.stringify(c)]
    const data = vanX.reactive({list: [1, 2, 3, 4, 5], group: {list1: [11, 12, 13]}, listOfLists: [[1], [1, 2]], others: {line1: 'x'}})
    delete data.list[3]; delete data.group.list1[2]; delete data.listOfLists[0][0]
    out.plain = JSON.stringify(vanX.compact(data))
    out.plainProto = Object.getPrototypeOf(vanX.compact({a: 1})) === Object.prototype
    out.arr = Array.isArray(vanX.compact([1, , 2]))
    return out
  })
  assert.equal(r.before, '["1,2",null,"3,4"]')
  assert.equal(r.after, '["1,2","3,4"]')
  assert.deepEqual(r.nested, [true, '{"p":"7,8"}'])
  assert.equal(r.plain, '{"list":[1,2,3,5],"group":{"list1":[11,12]},"listOfLists":[[],[1,2]],"others":{"line1":"x"}}')
  assert.equal(r.plainProto, true)
  assert.equal(r.arr, true)
  await page.locator('#points li').nth(1).locator('button').click(); await page.waitForTimeout(50)
  await page.click('#export'); await page.waitForTimeout(50)
  assert.equal(await page.locator('#exported').textContent(), '["1,2","3,4"]')
}
