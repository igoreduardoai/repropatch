import van from "vanjs-core"
import * as vanX from "./x/src/van-x.js"
window.van = van
window.vanX = vanX
const {h2, p, button, div} = van.tags
const cart = vanX.reactive({items: ["apple", "pear"]})
window.cart = cart
const safe = f => () => { try { return f() } catch (e) { return "Error: " + e.message } }
const status = van.state("")
van.add(document.body, div(
  h2("Shopping cart"),
  div({id: "summary"}, "Items: ", safe(() => cart.items.length + " (" + cart.items.join(", ") + ")")),
  button({id: "add", onclick: () => { try { cart.items.push("plum"); status.val = "" } catch (e) { status.val = "Error: " + e.message } }}, "Add plum"),
  div({id: "status"}, status),
  p("Expected: Items: 2 (apple, pear), then Items: 3 (apple, pear, plum) after Add plum"),
))
