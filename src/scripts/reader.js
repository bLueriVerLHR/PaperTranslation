/* Reader enhancements: theme toggle, back-to-top, TOC scroll-spy.
 * Everything degrades gracefully: with JavaScript disabled the page is still
 * fully readable and the TOC still folds natively via <details>. */
(function () {
  "use strict";

  var STORAGE_KEY = "paper-translation-theme";
  var THEMES = ["auto", "light", "dark"];
  var LABELS = { auto: "跟随系统", light: "浅色", dark: "深色" };
  var root = document.documentElement;
  var activeModal = null;

  function createModal(id, label, content) {
    if (typeof HTMLDialogElement === "undefined" ||
        typeof HTMLDialogElement.prototype.showModal !== "function") { return null; }
    var dialog = document.createElement("dialog");
    dialog.id = id;
    dialog.className = "reader-dialog";
    dialog.setAttribute("aria-labelledby", id + "-title");
    var header = document.createElement("header");
    header.className = "reader-dialog-header";
    var heading = document.createElement("h2");
    heading.id = id + "-title";
    heading.textContent = label;
    var close = document.createElement("button");
    close.type = "button";
    close.className = "reader-dialog-close";
    close.textContent = "关闭";
    close.setAttribute("aria-label", "关闭" + label + "窗口");
    close.setAttribute("autofocus", "");
    header.appendChild(heading);
    header.appendChild(close);
    var body = document.createElement("div");
    body.className = "reader-dialog-body";
    body.appendChild(content);
    dialog.appendChild(header);
    dialog.appendChild(body);
    document.body.appendChild(dialog);
    var position = 0;
    var originalStyle = null;
    var opener = null;
    var destination = null;
    var pressedOutside = false;
    function outside(event) {
      var rect = dialog.getBoundingClientRect();
      return event.clientX < rect.left || event.clientX > rect.right ||
        event.clientY < rect.top || event.clientY > rect.bottom;
    }
    var api = {
      dialog: dialog,
      body: body,
      open: function (trigger) {
        if (activeModal) { return; }
        position = window.scrollY;
        originalStyle = document.body.getAttribute("style");
        opener = trigger;
        destination = null;
        document.body.style.position = "fixed";
        document.body.style.top = -position + "px";
        document.body.style.left = "0";
        document.body.style.right = "0";
        document.body.style.overflow = "hidden";
        dialog.showModal();
        body.scrollTop = 0;
        activeModal = api;
      },
      close: function (target) {
        destination = target || null;
        dialog.close();
      }
    };
    close.addEventListener("click", function () { api.close(); });
    dialog.addEventListener("keydown", function (event) {
      if (event.key !== "Tab") { return; }
      // Keep both directions in the card, including browsers that otherwise tab to chrome.
      var controls = Array.from(dialog.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"))
        .filter(function (element) { return element.getClientRects().length && !element.closest("[inert]"); });
      var first = controls[0];
      var last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    });
    dialog.addEventListener("pointerdown", function (event) {
      pressedOutside = event.target === dialog && outside(event);
    });
    dialog.addEventListener("click", function (event) {
      if (pressedOutside && event.target === dialog && outside(event)) { api.close(); }
      pressedOutside = false;
    });
    dialog.addEventListener("close", function () {
      if (originalStyle === null) { document.body.removeAttribute("style"); }
      else { document.body.setAttribute("style", originalStyle); }
      window.scrollTo({ top: position, behavior: "instant" });
      if (opener && opener.isConnected) { opener.focus({ preventScroll: true }); }
      activeModal = null;
      if (destination) {
        var target = destination;
        destination = null;
        target.scrollIntoView({ block: "start", behavior: "instant" });
        var tabIndex = target.getAttribute("tabindex");
        if (tabIndex === null) {
          target.setAttribute("tabindex", "-1");
          target.addEventListener("blur", function () {
            if (target.getAttribute("tabindex") === "-1") { target.removeAttribute("tabindex"); }
          }, { once: true });
        }
        target.focus({ preventScroll: true });
        try { window.history.pushState(null, "", "#" + encodeURIComponent(target.id)); }
        catch (err) { window.location.hash = target.id; }
      }
    });
    return api;
  }

  // Shared by the library, article TOC and citation cards; one scroll-lock implementation.
  window.PaperReader = { createModal: createModal };

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
      window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    });
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  function initFootnotes() {
    var links = document.querySelectorAll("a.footnote-ref[href^='#']");
    if (!links.length) { return; }
    var modal = createModal("footnote-dialog", "注释", document.createElement("div"));
    if (!modal) { return; }
    links.forEach(function (link) {
      var id;
      try { id = decodeURIComponent(link.getAttribute("href").slice(1)); }
      catch (_) { return; }
      var target = document.getElementById(id);
      if (!target) { return; }
      link.addEventListener("click", function (event) {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || activeModal) { return; }
        var detail = document.createElement("div");
        detail.className = "footnote-detail";
        Array.from(target.childNodes).forEach(function (node) { detail.appendChild(node.cloneNode(true)); });
        detail.querySelectorAll("[id]").forEach(function (node) { node.removeAttribute("id"); });
        detail.querySelectorAll(".footnote-backref, .footnote-back").forEach(function (node) { node.remove(); });
        modal.body.replaceChildren(detail);
        event.preventDefault();
        modal.open(link);
      });
    });
  }

  function initToc() {
    var toc = document.getElementById("toc");
    var toolbar = document.querySelector(".toolbar");
    if (!toc || !toolbar) { return; }
    var nav = toc.querySelector("nav");
    if (!nav || !nav.querySelector("a")) { toc.hidden = true; return; }
    // One default-closed TOC at every width; move the canonical tree, never clone it.
    // Keep native details unchanged when the dialog enhancement is unavailable.
    var modal = createModal("toc-dialog", "文内目录", document.createElement("div"));
    if (!modal) { return; }
    nav.classList.add("toc-content");
    modal.body.replaceChildren(nav);
    var trigger = document.createElement("button");
    trigger.id = "toc-toggle";
    trigger.type = "button";
    trigger.textContent = "目录";
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-controls", "toc-dialog");
    trigger.addEventListener("click", function () {
      modal.open(trigger);
      var current = nav.querySelector(".active");
      if (current) { current.scrollIntoView({ block: "nearest", behavior: "instant" }); }
    });
    nav.addEventListener("click", function (event) {
      var link = event.target.closest("a[href^='#']");
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) { return; }
      var target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
      if (!target) { return; }
      event.preventDefault();
      modal.close(target);
    });
    toolbar.appendChild(trigger);
    toc.remove();
  }

  function initCitations() {
    var links = document.querySelectorAll("a.citation[data-citations]");
    if (!links.length) { return; }
    var content = document.createElement("div");
    var modal = createModal("citation-dialog", "引用详情", content);
    if (!modal) { return; }
    links.forEach(function (link) {
      link.addEventListener("click", function (event) {
        // Inside an answer card, retain the real source link instead of trying to
        // stack dialogs (or swallowing the click while another modal is active).
        if (activeModal) {
          if (link.closest(".qa-card-content") && /^https?:\/\//i.test(link.href)) {
            link.target = "_blank";
            link.rel = "noopener noreferrer";
          }
          return;
        }
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) { return; }
        var records;
        try { records = JSON.parse(link.getAttribute("data-citations")); }
        catch (err) { return; }
        event.preventDefault();
        content.replaceChildren();
        records.forEach(function (record) {
          var item = document.createElement("section");
          item.className = "citation-detail";
          var text = document.createElement("p");
          text.textContent = (record.label ? record.label + " · " : "") + record.text;
          item.appendChild(text);
          if (record.url && /^https?:\/\//i.test(record.url)) {
            var source = document.createElement("a");
            source.href = record.url;
            source.target = "_blank";
            source.rel = "noopener noreferrer";
            source.textContent = record.fallback ? "查看论文原文（未保存此条直达链接）" : "查看引用来源";
            item.appendChild(source);
          }
          content.appendChild(item);
        });
        modal.open(link);
      });
    });
  }

  var LEVELS = { basic: "基础", principle: "原理", scenario: "场景" };

  function levelLabel(item) {
    return LEVELS[item.getAttribute("data-level")] || "";
  }

  function questionNodes(pair) {
    // A question holds no stable IDs or handlers, so a display copy cannot duplicate an
    // anchor or a citation listener. Answers are always moved, never cloned.
    return Array.from((pair.trigger || pair.question).childNodes).map(function (node) {
      var copy = node.cloneNode(true);
      if (copy.querySelectorAll) {
        copy.querySelectorAll("[id]").forEach(function (element) { element.removeAttribute("id"); });
      }
      return copy;
    });
  }

  // Random practice stays opt-in and topic-scoped: the reader picks one question from the
  // selected themes, keeps its canonical answer folded, and never writes study state.
  function initRandomPractice(modalId, trigger, container, groups) {
    container.className = "body qa-card-content";
    var modal = createModal(modalId, "随机抽题", container);
    if (!modal) { return; }
    trigger.setAttribute("aria-controls", modal.dialog.id);
    trigger.addEventListener("click", function () {
      if (activeModal) { return; }
      modal.open(trigger);
    });
    var scopeTitle = document.createElement("p");
    scopeTitle.className = "qa-random-scope-title";
    scopeTitle.textContent = "主题范围（可多选）";
    var scopeList = document.createElement("div");
    scopeList.className = "qa-random-scope-list";
    scopeList.setAttribute("role", "group");
    scopeList.setAttribute("aria-label", "选择随机抽题的主题范围");
    var boxes = [];
    var printed = "";
    groups.forEach(function (group) {
      if (group.part && group.part !== printed) {
        var head = document.createElement("p");
        head.className = "qa-random-part";
        head.textContent = group.part;
        scopeList.appendChild(head);
        printed = group.part;
      }
      var label = document.createElement("label");
      label.className = "qa-random-topic";
      var box = document.createElement("input");
      box.type = "checkbox";
      box.checked = true;
      var name = document.createElement("span");
      name.className = "qa-random-topic-name";
      name.textContent = group.label;
      var count = document.createElement("span");
      count.className = "qa-random-count";
      count.textContent = group.items.length + " 题";
      label.append(box, name, count);
      scopeList.appendChild(label);
      boxes.push({ box: box, group: group });
    });
    function button(label, className) {
      var element = document.createElement("button");
      element.type = "button";
      element.textContent = label;
      if (className) { element.className = className; }
      return element;
    }
    var actions = document.createElement("div");
    actions.className = "qa-random-actions";
    var selectAll = button("全选");
    var selectNone = button("清空");
    var draw = button("抽一题", "qa-random-draw");
    actions.append(selectAll, selectNone, draw);
    var status = document.createElement("p");
    status.className = "qa-random-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    var result = document.createElement("div");
    result.className = "qa-random-result";
    var answerRegion = document.createElement("div");
    answerRegion.className = "qa-random-answer";
    container.append(scopeTitle, scopeList, actions, status, result);
    var revealed = null;
    var printedAnswer = null;
    function pool() {
      var found = [];
      boxes.forEach(function (entry) {
        if (!entry.box.checked) { return; }
        entry.group.items.forEach(function (pair) {
          if (!pair.item.hidden) { found.push(pair); }
        });
      });
      return found;
    }
    function restore() {
      if (revealed) { revealed.item.appendChild(revealed.answer); revealed = null; }
      answerRegion.replaceChildren();
    }
    function render(pair, size) {
      restore();
      result.replaceChildren();
      var meta = document.createElement("p");
      meta.className = "qa-random-meta";
      var level = levelLabel(pair.item);
      meta.textContent = pair.topic + (level ? " · " + level : "");
      var question = document.createElement("p");
      question.className = "qa-random-question";
      question.append.apply(question, questionNodes(pair));
      var buttons = document.createElement("div");
      buttons.className = "qa-random-actions";
      var toggleAnswer = button("查看答案");
      var jump = button("跳到原题");
      toggleAnswer.addEventListener("click", function () {
        if (revealed === pair) {
          restore();
          toggleAnswer.textContent = "查看答案";
        } else {
          restore();
          revealed = pair;
          answerRegion.replaceChildren(pair.answer);
          toggleAnswer.textContent = "收起答案";
        }
        updateMathLayout();
      });
      jump.addEventListener("click", function () {
        restore();
        modal.close(pair.item);
      });
      buttons.append(toggleAnswer, jump);
      result.append(meta, question, buttons, answerRegion);
      status.textContent = "已从 " + size + " 道可选题目中抽到一题" +
        (level ? "（" + level + "）" : "") + "，答案默认折叠。";
      draw.textContent = "再抽一题";
      updateMathLayout();
    }
    draw.addEventListener("click", function () {
      var found = pool();
      if (!found.length) {
        restore();
        result.replaceChildren();
        status.textContent = boxes.some(function (entry) { return entry.box.checked; })
          ? "所选主题在当前搜索条件下没有可抽的题目。"
          : "请至少选择一个主题。";
        return;
      }
      render(found[Math.floor(Math.random() * found.length)], found.length);
    });
    selectAll.addEventListener("click", function () {
      boxes.forEach(function (entry) { entry.box.checked = true; });
    });
    selectNone.addEventListener("click", function () {
      boxes.forEach(function (entry) { entry.box.checked = false; });
    });
    modal.dialog.addEventListener("close", function () {
      restore();
      result.replaceChildren();
      status.textContent = "";
      draw.textContent = "抽一题";
    });
    window.addEventListener("beforeprint", function () {
      printedAnswer = revealed;
      restore();
    });
    window.addEventListener("afterprint", function () {
      if (printedAnswer && modal.dialog.open) {
        revealed = printedAnswer;
        answerRegion.replaceChildren(printedAnswer.answer);
      }
      printedAnswer = null;
    });
  }

  function initQuestions() {
    document.querySelectorAll(".body .qa-bank").forEach(function (bank) {
      var pairs = Array.from(bank.children).filter(function (node) {
        return node.classList.contains("qa-item");
      }).map(function (item) {
        return { item: item, question: item.querySelector(".qa-question"), answer: item.querySelector(".qa-answer") };
      });
      if (!pairs.length || pairs.some(function (pair) { return !pair.question || !pair.answer; })) { return; }
      // Topic scope for random practice: the deepest heading that precedes an item, with
      // its parent heading as the part label. Banks without headings stay one scope.
      var byItem = new Map();
      pairs.forEach(function (pair) { byItem.set(pair.item, pair); });
      var groups = [];
      var seen = new Map();
      var part = "";
      var topic = "";
      Array.from(bank.children).forEach(function (node) {
        if (/^H[2-6]$/.test(node.tagName)) {
          if (node.tagName === "H2" || node.tagName === "H3") { part = node.textContent.trim(); topic = ""; }
          else { topic = node.textContent.trim(); }
          return;
        }
        var item = byItem.get(node);
        if (!item) { return; }
        var label = topic || part || "全部题目";
        var key = part + "\u0000" + label;
        var group = seen.get(key);
        if (!group) {
          group = { part: topic ? part : "", label: label, items: [] };
          seen.set(key, group);
          groups.push(group);
        }
        group.items.push(item);
        item.topic = label;
      });
      var content = document.createElement("div");
      content.className = "body qa-card-content";
      var modalId = "qa-dialog-" + bank.id;
      while (document.getElementById(modalId) || document.getElementById(modalId + "-title")) { modalId += "-card"; }
      var modal = createModal(modalId, "参考回答", content);
      // No dialog support: do not hide answers or expose non-working controls.
      if (!modal) { return; }
      var current = null;
      function restoreAnswer() {
        if (current) { current.item.appendChild(current.answer); }
      }
      modal.dialog.addEventListener("close", function () {
        restoreAnswer(); current = null;
      });
      content.addEventListener("click", function (event) {
        var link = event.target.closest("a[href^='#']");
        if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) { return; }
        var target;
        try { target = document.getElementById(decodeURIComponent(link.hash.slice(1))); }
        catch (err) { return; }
        if (!target) { return; }
        event.preventDefault();
        if (modal.dialog.contains(target)) { target.scrollIntoView({ block: "start", behavior: "instant" }); }
        else { modal.close(target); }
      });
      // Move the one canonical answer, never clone IDs or detach citation handlers.
      // Print always uses the original inline answer, even with its card still open.
      window.addEventListener("beforeprint", restoreAnswer);
      window.addEventListener("afterprint", function () {
        if (current && modal.dialog.open) { content.replaceChildren(current.answer); updateMathLayout(); }
      });
      var controls = document.createElement("div");
      controls.className = "qa-controls";
      var toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "qa-mode-toggle";
      toggle.setAttribute("aria-pressed", "false");
      var label = document.createElement("label");
      label.textContent = "搜索问题 ";
      var search = document.createElement("input");
      search.type = "search";
      search.placeholder = "问题关键词";
      label.appendChild(search);
      var randomTrigger = document.createElement("button");
      randomTrigger.type = "button";
      randomTrigger.className = "qa-random-toggle";
      randomTrigger.textContent = "随机抽题";
      randomTrigger.setAttribute("aria-haspopup", "dialog");
      var status = document.createElement("p");
      status.className = "qa-status";
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      controls.append(toggle, label, randomTrigger, status);
      bank.prepend(controls);
      bank.dataset.qaMode = "read";
      function updateStatus() {
        var visible = pairs.filter(function (pair) { return !pair.item.hidden; }).length;
        status.textContent = (bank.dataset.qaMode === "test" ? "答题自测 · 点击问题查看回答" : "问答阅读 · 全部回答展开") +
          " · " + visible + " / " + pairs.length + " 题" + (visible ? "" : " · 没有匹配的问题");
      }
      function setMode(test) {
        bank.dataset.qaMode = test ? "test" : "read";
        toggle.textContent = test ? "展开全部回答" : "折叠全部回答 · 自测";
        toggle.setAttribute("aria-pressed", String(test));
        pairs.forEach(function (pair) {
          pair.trigger.disabled = !test;
          var level = levelLabel(pair.item);
          if (test) {
            pair.trigger.setAttribute("aria-haspopup", "dialog");
            pair.trigger.setAttribute("aria-controls", modalId);
            if (level) { pair.trigger.setAttribute("aria-label", level + "：" + pair.question.textContent); }
          } else {
            pair.trigger.removeAttribute("aria-haspopup");
            pair.trigger.removeAttribute("aria-controls");
            pair.trigger.removeAttribute("aria-label");
          }
        });
        updateStatus(); updateMathLayout();
      }
      pairs.forEach(function (pair) {
        var trigger = document.createElement("button");
        trigger.type = "button";
        trigger.className = "qa-question-button";
        trigger.append.apply(trigger, Array.from(pair.question.childNodes));
        pair.question.appendChild(trigger);
        pair.trigger = trigger;
        trigger.addEventListener("click", function () {
          if (bank.dataset.qaMode !== "test" || activeModal) { return; }
          current = pair;
          document.getElementById(modalId + "-title").textContent = pair.question.textContent;
          content.replaceChildren(pair.answer);
          modal.open(trigger);
          updateMathLayout();
        });
      });
      toggle.addEventListener("click", function () { setMode(bank.dataset.qaMode !== "test"); });
      function filter() {
        var query = search.value.trim().toLocaleLowerCase();
        pairs.forEach(function (pair) {
          pair.item.hidden = pair.question.textContent.toLocaleLowerCase().indexOf(query) < 0;
        });
        updateStatus();
      }
      search.addEventListener("input", filter);
      initRandomPractice("qa-random-" + bank.id, randomTrigger, document.createElement("div"), groups);
      setMode(false);
    });
  }

  function initScrollSpy() {
    var links = document.querySelectorAll(".toc nav a[href^='#'], .toc-content a[href^='#']");
    if (!links.length || !("IntersectionObserver" in window)) { return; }
    var byId = new Map();
    var targets = [];
    var current = null;
    links.forEach(function (link) {
      var id;
      try { id = decodeURIComponent(link.getAttribute("href").slice(1)); }
      catch (_) { return; }
      var heading = document.getElementById(id);
      if (heading) { byId.set(id, link); targets.push(heading); }
    });

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) {
            return;
          }
          if (current) {
            current.classList.remove("active");
            current.removeAttribute("aria-current");
          }
          current = byId.get(entry.target.id);
          current.classList.add("active");
          current.setAttribute("aria-current", "location");
        });
      },
      { rootMargin: "-10% 0px -75% 0px", threshold: 0 }
    );
    targets.forEach(function (heading) {
      observer.observe(heading);
    });
  }

  function updateMathLayout() {
    document.querySelectorAll(".body math").forEach(function (element) {
      if (!element.getClientRects().length) { return; }
      var block = element.getAttribute("display") === "block" ||
        element.querySelector("mtable") || element.closest(".equation");
      var wrapper = element.parentElement;
      var wrapped = wrapper.classList.contains("math-scroll");
      var container = (wrapped ? wrapper.parentElement : element.parentElement)
        .closest("p, li, td, th, blockquote, .body");
      if (!container) { return; }
      var style = window.getComputedStyle(container);
      var available = container.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
      var wide = element.getBoundingClientRect().width > available + 1;
      if (block || wide) {
        if (!wrapped) {
          wrapper = document.createElement("span");
          wrapper.className = "math-scroll";
          element.before(wrapper);
          wrapper.appendChild(element);
        }
        wrapper.setAttribute("role", "region");
        wrapper.setAttribute("aria-label", "公式");
        var overflow = wrapper.scrollWidth > wrapper.clientWidth + 1;
        wrapper.classList.toggle("has-overflow", overflow);
        if (overflow) {
          wrapper.tabIndex = 0;
          wrapper.setAttribute("aria-label", "公式，可横向滚动");
        } else {
          wrapper.removeAttribute("tabindex");
          wrapper.setAttribute("aria-label", "公式");
        }
        var hint = wrapper.nextElementSibling;
        if (!hint || !hint.classList.contains("math-overflow-note")) {
          hint = document.createElement("span");
          hint.className = "math-overflow-note";
          hint.textContent = "左右滑动查看完整公式 ↔";
          hint.setAttribute("aria-hidden", "true");
          wrapper.after(hint);
        }
        hint.hidden = !overflow;
      } else if (wrapped) {
        var oldHint = wrapper.nextElementSibling;
        if (oldHint && oldHint.classList.contains("math-overflow-note")) { oldHint.remove(); }
        wrapper.replaceWith(element);
      }
    });
  }

  function initSourceExcerpts() {
    document.querySelectorAll(".source-excerpt").forEach(function (card) {
      var code = card.querySelector("pre code");
      if (!code) { return; }
      var original = code.textContent;
      var indents = original.split("\n").filter(function (line) { return line.trim(); })
        .map(function (line) { return (line.match(/^ */) || [""])[0].length; });
      var common = indents.length ? Math.min.apply(null, indents) : 0;
      if (common > 0) {
        var walker = document.createTreeWalker(code, NodeFilter.SHOW_TEXT);
        var nodes = [];
        while (walker.nextNode()) { nodes.push(walker.currentNode); }
        var column = 0;
        nodes.forEach(function (node) {
          var fragment = document.createDocumentFragment();
          var buffer = "", hidden = false;
          function flush() {
            if (!buffer) { return; }
            if (hidden) {
              var span = document.createElement("span");
              span.className = "code-indent";
              span.textContent = buffer;
              fragment.appendChild(span);
            } else { fragment.appendChild(document.createTextNode(buffer)); }
            buffer = "";
          }
          Array.from(node.data).forEach(function (character) {
            var hide = character === " " && column < common;
            if (hide !== hidden) { flush(); hidden = hide; }
            buffer += character;
            column = character === "\n" ? 0 : column + 1;
          });
          flush();
          node.replaceWith(fragment);
        });
        var note = card.querySelector(".source-indent-note");
        if (note) { note.hidden = false; }
      }
      var copy = card.querySelector("[data-copy-code]");
      if (copy) {
        copy.hidden = false;
        copy.addEventListener("click", function () {
          function selectOriginal() {
            // Never silently copy dedented/line-numbered display text.
            var previous = card.querySelector(".source-copy-fallback");
            if (previous) { previous.remove(); }
            var textarea = document.createElement("textarea");
            textarea.value = original;
            textarea.setAttribute("aria-label", "源码原文，请复制后按 Escape 关闭");
            textarea.className = "source-copy-fallback";
            card.appendChild(textarea);
            textarea.focus();
            textarea.select();
            textarea.addEventListener("keydown", function (event) {
              if (event.key === "Escape") { textarea.remove(); copy.focus(); }
            });
            copy.textContent = "已选中原文";
          }
          if (!navigator.clipboard || !navigator.clipboard.writeText) { selectOriginal(); return; }
          navigator.clipboard.writeText(original).then(function () {
            copy.textContent = "已复制原文";
          }, selectOriginal);
        });
      }
    });
  }

  function initReadingTools() {
    var toolbar = document.querySelector(".toolbar");
    if (!toolbar || !document.querySelector(".body")) { return; }
    var scale = 1;
    try { scale = Number(window.localStorage.getItem("paper-reading-scale")) || 1; } catch (err) { /* Optional storage. */ }
    scale = Math.max(.9, Math.min(1.3, scale));
    function applyScale() {
      root.style.setProperty("--reading-scale", scale);
      updateMathLayout();
    }
    applyScale();
    [-.1, .1].forEach(function (step) {
      var button = document.createElement("button");
      button.type = "button";
      button.textContent = step < 0 ? "A−" : "A+";
      button.setAttribute("aria-label", step < 0 ? "减小正文字号" : "增大正文字号");
      button.addEventListener("click", function () {
        scale = Math.max(.9, Math.min(1.3, Math.round((scale + step) * 10) / 10));
        applyScale();
        try { window.localStorage.setItem("paper-reading-scale", scale); } catch (err) { /* Optional storage. */ }
      });
      toolbar.appendChild(button);
    });
    if (document.fonts) { document.fonts.ready.then(updateMathLayout); }
    window.addEventListener("resize", updateMathLayout);
    document.querySelectorAll(".table-wrap, .equation, .body pre").forEach(function (element) {
      element.tabIndex = 0;
      element.setAttribute("role", "region");
      element.setAttribute("aria-label", element.classList.contains("table-wrap") ? "表格，可横向滚动" : "代码或公式，可横向滚动");
    });
  }

  function init() {
    // Remove the native no-script width cap before measuring true formula widths.
    root.classList.add("reader-enhanced");
    initReadingTools();
    initSourceExcerpts();
    initToc();
    initCitations();
    initFootnotes();
    initQuestions();
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
