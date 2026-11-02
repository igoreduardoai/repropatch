import van from "vanjs-core"
window.van = van
const {h2, p, a, button, div} = van.tags
const {svg, a: svgA, text} = van.tags("http://www.w3.org/2000/svg")
const status = van.state("Icon link not rendered yet")
const renderIcon = () => {
  try {
    const icon = svg({id: "icon", width: "220", height: "40"},
      svgA({id: "svg-link", href: "#top"}, text({x: "10", y: "25"}, "Back to top (SVG link)")))
    document.getElementById("icon-slot").append(icon)
    status.val = "Rendered SVG link, href=" + icon.querySelector("a").getAttribute("href")
  } catch (e) {
    status.val = "Error: " + e.message
  }
}
van.add(document.body, div(
  h2({id: "top"}, "Docs page"),
  p(a({id: "html-link", href: "https://vanjs.org/"}, "VanJS docs (HTML link)")),
  button({id: "render-icon", onclick: renderIcon}, "Render SVG icon link"),
  div({id: "icon-slot"}),
  p({id: "status"}, () => status.val),
))
