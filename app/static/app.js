/* The only script on the site. Four small behaviours, no framework:
   scroll reveal, catch-wheel hover, the wheel/grid switch, and the lab's
   tick-all buttons. Every page works without it. */

(function () {
  "use strict";

  var reduced =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── scroll reveal ─────────────────────────────────────────── */

  var sections = document.querySelectorAll(".reveal");
  if (reduced || !("IntersectionObserver" in window)) {
    sections.forEach(function (el) {
      el.classList.add("shown");
    });
  } else {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("shown");
            io.unobserve(e.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px" }
    );
    sections.forEach(function (el) {
      io.observe(el);
    });
  }

  /* ── catch wheel ───────────────────────────────────────────── */

  document.querySelectorAll(".wheel-box").forEach(function (box) {
    var hub = box.querySelector(".hub");
    var caption = box.parentNode.querySelector(".wheel-caption");
    var hubIdle = hub ? hub.textContent : "";
    var capIdle = caption ? caption.textContent : "";

    function paint(id) {
      if (id) {
        box.setAttribute("data-hover", id);
      } else {
        box.removeAttribute("data-hover");
      }
      box.querySelectorAll(".arc").forEach(function (arc) {
        arc.classList.toggle("on", !!id && arc.dataset.defect === id);
      });
      box.querySelectorAll(".spokes span").forEach(function (s) {
        s.classList.toggle("on", !!id && s.dataset.defect === id);
      });
      if (hub) hub.textContent = id || hubIdle;
      if (caption) {
        var arc = id ? box.querySelector('.arc[data-defect="' + id + '"]') : null;
        caption.textContent = arc ? arc.dataset.caption : capIdle;
      }
    }

    box.querySelectorAll(".arc").forEach(function (arc) {
      arc.addEventListener("mouseenter", function () {
        paint(arc.dataset.defect);
      });
      arc.addEventListener("mouseleave", function () {
        paint(null);
      });
      if (arc.dataset.href) {
        arc.addEventListener("click", function () {
          window.location.href = arc.dataset.href;
        });
      }
    });
  });

  /* ── wheel / grid switch ───────────────────────────────────── */

  document.querySelectorAll(".switch[data-switch]").forEach(function (sw) {
    sw.querySelectorAll("button[data-view]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var view = btn.dataset.view;
        sw.querySelectorAll("button[data-view]").forEach(function (b) {
          b.setAttribute("aria-pressed", String(b === btn));
        });
        document.querySelectorAll("[data-board]").forEach(function (panel) {
          panel.hidden = panel.dataset.board !== view;
        });
      });
    });
  });

  /* ── lab: tick every box in a scope ────────────────────────── */

  document.querySelectorAll("[data-set]").forEach(function (button) {
    button.addEventListener("click", function () {
      var parts = button.dataset.set.split(":");
      var only = button.dataset.only;
      var scope = only
        ? document.querySelector('.toggles[data-target="' + only + '"]')
        : document;
      var name = 'input[name="' + parts[0] + '"]';
      if (only) {
        document.querySelectorAll(name).forEach(function (input) {
          input.checked = false;
        });
      }
      scope.querySelectorAll(name).forEach(function (input) {
        input.checked = parts[1] === "1";
      });
      document.querySelectorAll(".toggle").forEach(function (label) {
        var input = label.querySelector("input");
        if (input) label.classList.toggle("on", input.checked);
      });
    });
  });

  document.querySelectorAll(".toggle input").forEach(function (input) {
    input.addEventListener("change", function () {
      input.closest(".toggle").classList.toggle("on", input.checked);
    });
  });
})();
