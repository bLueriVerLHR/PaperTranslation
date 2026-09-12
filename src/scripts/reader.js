/* Reader enhancements: theme toggle, back-to-top, TOC scroll-spy.
 * Everything degrades gracefully: with JavaScript disabled the page is still
 * fully readable and the TOC still folds natively via <details>. */
(function () {
  "use strict";

  var STORAGE_KEY = "paper-translation-theme";
  var THEMES = ["auto", "light", "dark"];
  var LABELS = { auto: "跟随系统", light: "浅色", dark: "深色" };
  var root = document.documentElement;

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    var button = document.getElementById("theme-toggle");
    if (button) {
      button.textContent = LABELS[theme];
      button.setAttribute("aria-label", "切换主题，当前：" + LABELS[theme]);
    }
  }

  function initTheme() {
    var stored = null;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      stored = null;
    }
    var theme = THEMES.indexOf(stored) >= 0 ? stored : "auto";
    applyTheme(theme);

    var button = document.getElementById("theme-toggle");
    if (!button) {
      return;
    }
    button.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") || "auto";
      var next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length];
      applyTheme(next);
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch (err) {
        /* Storage unavailable (private mode); the theme still applies. */
      }
    });
  }

  function initTopButton() {
    var button = document.getElementById("top-button");
    if (!button) {
      return;
    }
    function update() {
      button.hidden = window.scrollY < 600;
    }
    button.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  function initScrollSpy() {
    var links = Array.prototype.slice.call(document.querySelectorAll(".toc a[href^='#']"));
    if (!links.length || !("IntersectionObserver" in window)) {
      return;
    }
    var byId = {};
    var targets = [];
    links.forEach(function (link) {
      var id = decodeURIComponent(link.getAttribute("href").slice(1));
      var heading = document.getElementById(id);
      if (heading) {
        byId[id] = link;
        targets.push(heading);
      }
    });

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) {
            return;
          }
          links.forEach(function (link) {
            link.classList.remove("active");
          });
          var link = byId[entry.target.id];
          if (link) {
            link.classList.add("active");
          }
        });
      },
      { rootMargin: "-10% 0px -75% 0px", threshold: 0 }
    );
    targets.forEach(function (heading) {
      observer.observe(heading);
    });
  }

  function init() {
    initTheme();
    initTopButton();
    initScrollSpy();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
