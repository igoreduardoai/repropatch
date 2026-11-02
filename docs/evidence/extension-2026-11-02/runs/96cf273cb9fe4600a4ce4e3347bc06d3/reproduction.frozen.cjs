module.exports = async (page, assert) => {
  assert.match(await page.locator('#name').textContent(), /Ada Lovelace/)
  assert.match(await page.locator('#count').textContent(), /3/)
  assert.match(await page.locator('#list').textContent(), /90%, 85%, 77%/)
  const r = await page.evaluate(async () => {
    const {van, vanX, Person} = window
    const person = vanX.reactive(new Person("Ada", "Lovelace"))
    const scores = vanX.reactive([90, 85, 77])
    let runs = 0, seen
    van.derive(() => { runs++; seen = vanX.raw(scores).length + ":" + vanX.raw(person).fullName() })
    const before = runs
    scores.push(60); person.firstName = "Grace"
    return {len: vanX.raw(scores).length, mapped: vanX.raw(scores).map(s => s + "%"), name: vanX.raw(person).fullName(), before, runs, seen}
  })
  assert.equal(r.len, 4)
  assert.deepEqual(r.mapped, ["90%","85%","77%","60%"])
  assert.equal(r.name, "Grace Lovelace")
  assert.equal(r.runs, r.before) // raw reads must not subscribe
}
