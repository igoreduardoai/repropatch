// Independent checks adapted from the upstream VanJS test added in commit 5d97cff (MIT).
module.exports = async (page, assert) => {
  const sleep = ms => new Promise(r => setTimeout(r, ms))
  const r = await page.evaluate(async () => {
    const {van, vanX} = window, out = {}, sleep = ms => new Promise(r => setTimeout(r, ms))
    const host = document.createElement('div'); document.body.appendChild(host)
    const data = vanX.reactive({func: () => "abc"})
    van.add(host, () => { try { return data.func() } catch (e) { return 'ERR' } })
    out.a = host.innerHTML
    data.func = () => "def"; await sleep(50); out.b = host.innerHTML
    vanX.replace(data, {func: () => "ghi"}); await sleep(50); out.c = host.innerHTML
    const box = vanX.reactive({obj: {x: 1}, list: [{y: 2}]})
    out.objs = JSON.stringify(box)
    host.remove()
    return out
  })
  assert.deepEqual([r.a, r.b, r.c], ["abc", "def", "ghi"])
  assert.equal(r.objs, '{"obj":{"x":1},"list":[{"y":2}]}')
  assert.equal(await page.locator('#greeting').textContent(), 'Hi Ada!')
  await page.click('#formal'); await sleep(100)
  assert.equal(await page.locator('#greeting').textContent(), 'Good evening, Ms. Lovelace.')
}
