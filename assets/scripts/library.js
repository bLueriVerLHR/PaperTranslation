/* Progressive directory search and native modal page lists.
 * Without dialog support or JS, the original details/links remain accessible. */
(function () {
  "use strict";
  var input = document.getElementById("library-search");
  if (!input) { return; }
  var cards = Array.from(document.querySelectorAll(".library-card"));
  var status = document.getElementById("search-status");
  // Capture detail titles before moving their list into the top-layer dialog.
  var searchable = cards.map(function (card) {
    return card.textContent.toLocaleLowerCase();
  });

  if (typeof HTMLDialogElement !== "undefined" &&
      typeof HTMLDialogElement.prototype.showModal === "function") {
    cards.forEach(function (card, index) {
      var details = card.querySelector(".library-pages");
      if (!details) { return; }
      var list = details.querySelector("ul");
      var trigger = document.createElement("button");
      trigger.type = "button";
      trigger.className = "library-more";
      trigger.textContent = details.querySelector("summary").textContent;
      trigger.setAttribute("aria-haspopup", "dialog");
      trigger.setAttribute("aria-controls", "library-dialog-" + index);

      var dialog = document.createElement("dialog");
      dialog.id = "library-dialog-" + index;
      dialog.className = "library-dialog";
      dialog.setAttribute("aria-labelledby", dialog.id + "-title");
      var header = document.createElement("header");
      header.className = "library-dialog-header";
      var title = document.createElement("h2");
      title.id = dialog.id + "-title";
      title.textContent = card.querySelector("h2").textContent + " · 更多页面";
      var close = document.createElement("button");
      close.type = "button";
      close.className = "library-dialog-close";
      close.textContent = "关闭";
      close.setAttribute("aria-label", "关闭更多页面窗口");
      close.setAttribute("autofocus", "");
      header.appendChild(title);
      header.appendChild(close);
      var scroller = document.createElement("div");
      scroller.className = "library-dialog-list";
      scroller.appendChild(list);
      dialog.appendChild(header);
      dialog.appendChild(scroller);
      document.body.appendChild(dialog);
      details.replaceWith(trigger);

      var scrollY = 0;
      var bodyStyle = null;
      trigger.addEventListener("click", function () {
        scrollY = window.scrollY;
        bodyStyle = document.body.getAttribute("style");
        // A fixed body also prevents scroll bleed on iOS. Restore exactly on close.
        document.body.style.position = "fixed";
        document.body.style.top = -scrollY + "px";
        document.body.style.left = "0";
        document.body.style.right = "0";
        document.body.style.overflow = "hidden";
        scroller.scrollTop = 0;
        dialog.showModal();
      });
      close.addEventListener("click", function () { dialog.close(); });
      dialog.addEventListener("close", function () {
        if (bodyStyle === null) { document.body.removeAttribute("style"); }
        else { document.body.setAttribute("style", bodyStyle); }
        window.scrollTo({ top: scrollY, behavior: "instant" });
        trigger.focus({ preventScroll: true });
      });
      function outside(event) {
        var rect = dialog.getBoundingClientRect();
        return event.clientX < rect.left || event.clientX > rect.right ||
          event.clientY < rect.top || event.clientY > rect.bottom;
      }
      var pressedOutside = false;
      dialog.addEventListener("pointerdown", function (event) {
        pressedOutside = event.target === dialog && outside(event);
      });
      dialog.addEventListener("click", function (event) {
        if (pressedOutside && event.target === dialog && outside(event)) {
          dialog.close();
        }
        pressedOutside = false;
      });
      // Native showModal traps focus and closes on Escape; close restores the page.
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
