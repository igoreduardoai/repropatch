import van from "vanjs-core"
import * as vanX from "./x/src/van-x.js"
window.van = van
window.vanX = vanX
const {h2, p, button, ul, li, div} = van.tags
const items = vanX.reactive(["Milk", "Eggs", "Bread", "Coffee", "Apples"])
window.items = items
van.add(document.body, div(
  h2("Shopping list"),
  p({id: "count"}, "Items in data: ", () => items.length),
  button({id: "keep2", onclick: () => { items.length = 2 }}, "Keep first 2"), " ",
  button({id: "clear", onclick: () => { items.length = 0 }}, "Clear list"), " ",
  button({id: "add", onclick: () => items.push("Tea")}, "Add Tea"),
  vanX.list(() => ul({id: "list"}), items, v => li(v)),
))
