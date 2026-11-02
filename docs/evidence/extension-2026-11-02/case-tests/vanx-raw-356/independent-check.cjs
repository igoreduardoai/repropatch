// Independent checks adapted from the upstream VanJS tests added in commit 17d5ce5 (MIT).
module.exports = async (page, assert) => {
  const r = await page.evaluate(async () => {
    const {van, vanX, Person} = window, sleep = ms => new Promise(r => setTimeout(r, ms)), out = {}
    const {div} = van.tags
    const host = document.createElement('div'); document.body.appendChild(host)
    const printToStr = arr => { let s = ""; for (let i = 0; i < arr.length; ++i) s += `${i ? ", " : ""}${i}: ${arr[i]}`; return s }
    const render = arr => div(div("Length is: ", () => arr.length), div("Elements are: ", () => printToStr(arr)), div("Mapped elements are: ", () => printToStr(arr.map(t => t * 2))))
    try {
      const arr = vanX.reactive([1, 2, 3])
      van.add(host, render(arr), render(vanX.raw(arr)))
      out.a1 = host.innerHTML
      arr.push(4, 5); await sleep(50); out.a2 = host.innerHTML
    } catch (e) { out.aerr = String(e) }
    host.innerHTML = ''
    try {
      const person = vanX.reactive(new Person("Tao", "Xin"))
      van.add(host, div(() => person.fullName()), div(() => vanX.raw(person).fullName()))
      out.p1 = host.innerHTML
      person.firstName = "Van"; person.lastName = "JS"; await sleep(50); out.p2 = host.innerHTML
    } catch (e) { out.perr = String(e) }
    host.remove()
    return out
  })
  const row = (n, xs) => `<div><div>Length is: ${n}</div><div>Elements are: ${xs.map((x, i) => `${i}: ${x}`).join(', ')}</div><div>Mapped elements are: ${xs.map((x, i) => `${i}: ${x * 2}`).join(', ')}</div></div>`
  assert.equal(r.aerr, undefined)
  assert.equal(r.a1, row(3, [1, 2, 3]) + row(3, [1, 2, 3]))
  assert.equal(r.a2, row(5, [1, 2, 3, 4, 5]) + row(3, [1, 2, 3]))
  assert.equal(r.perr, undefined)
  assert.equal(r.p1, '<div>Tao Xin</div><div>Tao Xin</div>')
  assert.equal(r.p2, '<div>Van JS</div><div>Tao Xin</div>')
  assert.equal(await page.locator('#name').textContent(), 'Name: Ada Lovelace')
  assert.equal(await page.locator('#count').textContent(), 'Scores recorded: 3')
  assert.equal(await page.locator('#list').textContent(), 'Scores: 90%, 85%, 77%')
}
