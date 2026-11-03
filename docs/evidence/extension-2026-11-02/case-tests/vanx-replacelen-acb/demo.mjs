import van from "vanjs-core"
import * as vanX from "./x/src/van-x.js"
window.van = van
window.vanX = vanX
const {h2, p, button, div} = van.tags
const songs = vanX.reactive(["Blue", "Gold", "Red", "Teal"])
window.songs = songs
van.add(document.body, div(
  h2("Playlist"),
  div({id: "count"}, "Songs: ", () => songs.length),
  div({id: "json"}, "Saved as: ", () => JSON.stringify(songs)),
  button({id: "top2", onclick: () => vanX.replace(songs, l => l.slice(0, 2))}, "Keep top 2"),
  p("Expected after Keep top 2: Songs: 2 · Saved as: [\"Blue\",\"Gold\"]"),
))
