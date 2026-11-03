import van from "vanjs-core"
window.van = van
const {h2, p, button, div, span} = van.tags
const price = van.state(100)
let recomputes = 0
const shown = van.state(0)
const host = div({id: "panel"})
let badge = div({id: "badge", title: () => (++recomputes, "Price " + price.val)}, "Price badge")
van.add(host, badge)
van.add(document.body, div(
  h2("Price ticker"),
  host,
  button({id: "close", onclick: () => badge.remove()}, "Close badge"),
  button({id: "tick", onclick: async () => { price.val++; await Promise.resolve(); shown.val = recomputes }}, "Price tick"),
  div({id: "calls"}, "Badge title computations: ", shown),
  p("Expected: after the badge is closed, price ticks no longer recompute its title (count stays put)"),
))
window.getRecomputes = () => recomputes
