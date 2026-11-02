import van from "vanjs-core"
import * as vanX from "./x/src/van-x.js"
window.van = van
window.vanX = vanX
const {h2, p, button, ul, li, div, span} = van.tags
const tasks = vanX.reactive([{text: "Write release notes"}, {text: "Add docs"}, {text: "Fix login bug"}])
window.tasks = tasks
van.add(document.body, div(
  h2("Team tasks"),
  vanX.list(() => ul({id: "tasks"}), tasks, v => li(span({class: "label"}, () => v.val.text))),
  button({id: "sort", onclick: () => vanX.replace(tasks, xs => xs.toSorted((a, b) => a.text.localeCompare(b.text)))}, "Sort A to Z"),
  p("Expected after sorting: Add docs, Fix login bug, Write release notes"),
))
