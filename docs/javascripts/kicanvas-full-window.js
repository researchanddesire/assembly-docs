(function () {
  function setFullWindow(wrapper, expanded) {
    const button = wrapper.querySelector(".pcb-kicanvas-full-window");

    wrapper.classList.toggle("is-full-window", expanded);
    document.body.classList.toggle("pcb-kicanvas-full-window-active", expanded);

    if (button) {
      button.setAttribute("aria-expanded", expanded ? "true" : "false");
      button.textContent = expanded ? "Exit full window" : "Full window";
    }
  }

  function bindKicanvasFullWindow(root) {
    root.querySelectorAll(".pcb-kicanvas").forEach((wrapper) => {
      const button = wrapper.querySelector(".pcb-kicanvas-full-window");
      if (!button || button.dataset.bound === "true") return;

      button.dataset.bound = "true";
      button.addEventListener("click", () => {
        setFullWindow(wrapper, !wrapper.classList.contains("is-full-window"));
      });
    });
  }

  function exitActiveViewer() {
    const active = document.querySelector(".pcb-kicanvas.is-full-window");
    if (active) setFullWindow(active, false);
  }

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") exitActiveViewer();
  }, true);

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(bindKicanvasFullWindow);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => bindKicanvasFullWindow(document));
  } else {
    bindKicanvasFullWindow(document);
  }
})();
