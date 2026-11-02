import van from "vanjs-core"
import * as vanX from "./x/src/van-x.js"
window.van = van
window.vanX = vanX
const {h2, p, div} = van.tags
class Person {
  constructor(firstName, lastName) { this.firstName = firstName; this.lastName = lastName }
  fullName() { return `${this.firstName} ${this.lastName}` }
}
window.Person = Person
const person = vanX.reactive(new Person("Ada", "Lovelace"))
const scores = vanX.reactive([90, 85, 77])
const safe = f => () => { try { return f() } catch (e) { return "Error: " + e.message } }
van.add(document.body, div(
  h2("Profile snapshot (vanX.raw)"),
  div({id: "name"}, "Name: ", safe(() => vanX.raw(person).fullName())),
  div({id: "count"}, "Scores recorded: ", safe(() => vanX.raw(scores).length)),
  div({id: "list"}, "Scores: ", safe(() => vanX.raw(scores).map(s => s + "%").join(", "))),
  p("Expected: Name: Ada Lovelace · Scores recorded: 3 · Scores: 90%, 85%, 77%"),
))
