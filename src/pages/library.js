/* Progressive search: the complete directory remains usable without JavaScript. */
(function () {
  "use strict";
  var input = document.getElementById("library-search");
  if (!input) { return; }
  var cards = Array.from(document.querySelectorAll(".library-card"));
  var status = document.getElementById("search-status");
  input.addEventListener("input", function () {
    var query = input.value.trim().toLocaleLowerCase();
    var visible = 0;
    cards.forEach(function (card) {
      card.hidden = !card.textContent.toLocaleLowerCase().includes(query);
      if (!card.hidden) { visible += 1; }
      var details = card.querySelector("details");
      if (details) { details.open = Boolean(query) && !card.hidden; }
    });
    status.textContent = visible ? "找到 " + visible + " 个项目" : "没有匹配项目，请尝试其他关键词。";
  });
})();
