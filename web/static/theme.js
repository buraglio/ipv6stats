(function () {
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem("theme");
    if (saved) root.dataset.theme = saved;
  } catch (e) {}

  function current() {
    if (root.dataset.theme) return root.dataset.theme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function restyleCharts() {
    if (!window.Plotly) return;
    var css = getComputedStyle(root);
    var text = css.getPropertyValue("--text").trim();
    var grid = css.getPropertyValue("--grid").trim();
    var bg = css.getPropertyValue("--bg").trim();
    var border = css.getPropertyValue("--border").trim();
    document.querySelectorAll(".js-plotly-plot").forEach(function (el) {
      window.Plotly.relayout(el, {
        "font.color": text, "xaxis.gridcolor": grid, "yaxis.gridcolor": grid,
        "xaxis.rangeselector.bgcolor": bg, "xaxis.rangeselector.activecolor": border,
        "xaxis.rangeselector.font.color": text
      });
    });
  }

  // Charts drawn while the page is still laying out can size themselves to Plotly's 700px
  // default; re-measure them once everything has loaded.
  window.addEventListener("load", function () {
    if (!window.Plotly) return;
    document.querySelectorAll(".js-plotly-plot").forEach(function (el) { window.Plotly.Plots.resize(el); });
  });

  document.addEventListener("DOMContentLoaded", function () {
    restyleCharts();
    var button = document.getElementById("theme-toggle");
    if (!button) return;
    button.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) {}
      restyleCharts();
    });
  });
})();
