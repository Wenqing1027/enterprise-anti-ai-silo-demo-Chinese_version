(() => {
  const root = document.getElementById("dept-flow");
  if (!root) return;

  const edges = root.querySelectorAll(".flow-edge");
  const nodes = root.querySelectorAll(".flow-node");
  const buttons = root.querySelectorAll(".line-dot");

  function apply(line) {
    const showAll = line === "all";
    edges.forEach((el) => {
      if (showAll) {
        el.classList.add("is-dim");
        el.classList.remove("is-on", "is-off");
      } else {
        const match = el.dataset.line === line;
        el.classList.toggle("is-on", match);
        el.classList.toggle("is-off", !match);
        el.classList.remove("is-dim");
      }
    });
    nodes.forEach((el) => {
      const lines = el.dataset.lines || "";
      const match = showAll || lines.includes(line);
      el.classList.toggle("is-on", match);
      el.classList.toggle("is-dim", !match);
    });
    buttons.forEach((btn) => {
      const on = btn.dataset.line === line;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => apply(btn.dataset.line || "a"));
  });

  apply("a");
})();
