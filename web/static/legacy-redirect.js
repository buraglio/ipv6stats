(function () {
  var name = new URLSearchParams(window.location.search).get("page");
  if (!name) return;
  var map = JSON.parse(document.getElementById("legacy-pages").textContent);
  window.location.replace(map[name] || "overview/");
})();
