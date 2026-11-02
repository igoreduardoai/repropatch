import van from "vanjs-core"
import * as vanX from "./x/src/van-x.js"
window.van = van
window.vanX = vanX
const {h2, p, button, div} = van.tags
const card = vanX.reactive({greet: () => "Hi Ada!"})
window.card = card
const shown = () => { try { return card.greet() } catch (e) { return "Error: " + e.message } }
van.add(document.body, div(
  h2("Greeting card"),
  div({id: "greeting"}, shown),
  button({id: "formal", onclick: () => { card.greet = () => "Good evening, Ms. Lovelace." }}, "Use formal greeting"),
  p("Expected: the card shows \"Hi Ada!\", and \"Good evening, Ms. Lovelace.\" after the button is clicked"),
))
