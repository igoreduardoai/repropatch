import van from "vanjs-core"
import * as vanX from "./x/src/van-x.js"
window.van = van
window.vanX = vanX
const {h2, p, button, div} = van.tags
const tasks = vanX.reactive(["Write tests", "Fix bug", "Ship release"])
window.tasks = tasks
const left = van.derive(() => tasks.length)
van.add(document.body, div(
  h2("Release checklist"),
  div({id: "left"}, "Tasks left: ", left),
  button({id: "done", onclick: () => tasks.pop()}, "Finish last task"),
  p("Expected: Tasks left goes 3 → 2 → 1 → 0 as tasks are finished"),
))
