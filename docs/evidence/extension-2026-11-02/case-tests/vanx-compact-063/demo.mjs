import van from "vanjs-core"
import * as vanX from "./x/src/van-x.js"
window.van = van
window.vanX = vanX
class Point {
  constructor(x, y) { this.x = x; this.y = y }
  toJSON() { return `${this.x},${this.y}` }
}
window.Point = Point
const {h2, p, button, ul, li, div, pre} = van.tags
const points = vanX.reactive([new Point(1, 2), new Point(5, 5), new Point(3, 4)])
window.points = points
const exported = van.state("(not exported yet)")
van.add(document.body, div(
  h2("Saved map points"),
  vanX.list(() => ul({id: "points"}), points, (v, deleter) => li(String(v.val.x) + "," + String(v.val.y), " ", button({onclick: deleter}, "delete"))),
  button({id: "export", onclick: () => { exported.val = JSON.stringify(vanX.compact(points)) }}, "Export points (vanX.compact)"),
  p("Expected export uses each Point's own format, e.g. [\"1,2\",\"3,4\"]"),
  pre({id: "exported"}, () => exported.val),
))
