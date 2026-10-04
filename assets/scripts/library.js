/* Progressive directory search; the shared reader owns modal/scroll-lock behavior. */
(function () {
  "use strict";
  var input = document.getElementById("library-search");
  if (!input) { return; }
  var cards = Array.from(document.querySelectorAll(".library-card"));
  var status = document.getElementById("search-status");
  var searchable = cards.map(function (card) {
    return card.textContent.toLocaleLowerCase();
  });
  if (window.PaperReader) {
    cards.forEach(function (card, index) {
      var details = card.querySelector(".library-pages");
      if (!details) { return; }
      // Only move the canonical list once native dialog support is confirmed.
      var modal = window.PaperReader.createModal("library-dialog-" + index,
        card.querySelector("h2").textContent + " · 更多页面", document.createElement("div"));
      if (!modal) { return; }
      modal.dialog.classList.add("library-dialog");
      modal.body.classList.add("library-dialog-list");
      modal.body.replaceChildren(details.querySelector("ul"));
      var trigger = document.createElement("button");
      trigger.type = "button";
      trigger.className = "library-more";
      trigger.textContent = details.querySelector("summary").textContent;
      trigger.setAttribute("aria-haspopup", "dialog");
      trigger.setAttribute("aria-controls", modal.dialog.id);
      trigger.addEventListener("click", function () { modal.open(trigger); });
      details.replaceWith(trigger);
    });
  }
  input.addEventListener("input", function () {
    var query = input.value.trim().toLocaleLowerCase();
    var visible = 0;
    cards.forEach(function (card, index) {
      card.hidden = !searchable[index].includes(query);
      if (!card.hidden) { visible += 1; }
      var fallback = card.querySelector(".library-pages");
      if (fallback) { fallback.open = Boolean(query) && !card.hidden; }
    });
    status.textContent = visible ? "找到 " + visible + " 个项目" : "没有匹配项目，请尝试其他关键词。";
  });
})();
