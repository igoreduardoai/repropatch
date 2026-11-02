module.exports = async (page, assert) => {
  const texts = await page.evaluate(() => [
    document.querySelector('#name').textContent,
    document.querySelector('#count').textContent,
    document.querySelector('#list').textContent,
  ])
  assert.match(texts[0], /Ada Lovelace/)
  assert.match(texts[1], /3/)
  assert.match(texts[2], /90%, 85%, 77%/)
  const r = await page.evaluate(async () => {
    const {vanX, van, Person} = window
    const person = vanX.reactive(new Person("Grace", "Hopper"))
    const scores = vanX.reactive([1, 2])
    let runs = 0, seen
    van.derive(() => { runs++; seen = vanX.raw(scores).length })
    const before = runs
    scores.push(3)
    return {name: vanX.raw(person).fullName(), len: vanX.raw(scores).length, mapped: vanX.raw(scores).map(x => x * 10), before, runs, seen}
  })
  assert.equal(r.name, "Grace Hopper")
  assert.equal(r.len, 3)
  assert.deepEqual(r.mapped, [10, 20, 30])
  assert.equal(r.runs, r.before)
}