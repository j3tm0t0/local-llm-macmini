/**
 * Replace the just-the-docs left sidebar's site-nav with a TOC of the
 * current page's h2 / h3 headings. Keeps a "Top" link at the top.
 * Active heading is highlighted on scroll via IntersectionObserver.
 */
(function () {
  function buildToc() {
    const main = document.querySelector(".main-content");
    const navList = document.querySelector(".side-bar .nav-list");
    if (!main || !navList) return;

    const headings = Array.from(main.querySelectorAll("h2[id], h3[id]"));
    if (headings.length === 0) return;

    // Wipe the existing nav (page list)
    navList.innerHTML = "";

    // "Top" link
    const topItem = document.createElement("li");
    topItem.className = "nav-list-item page-toc-item";
    const topLink = document.createElement("a");
    topLink.href = "#";
    topLink.className = "nav-list-link page-toc-link page-toc-top";
    topLink.textContent = "▲ Top";
    topLink.addEventListener("click", function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
      history.replaceState(null, "", window.location.pathname);
    });
    topItem.appendChild(topLink);
    navList.appendChild(topItem);

    const anchors = [];

    headings.forEach(function (h) {
      const li = document.createElement("li");
      li.className = "nav-list-item page-toc-item page-toc-" + h.tagName.toLowerCase();

      const a = document.createElement("a");
      a.href = "#" + h.id;
      a.className = "nav-list-link page-toc-link";
      a.textContent = h.textContent.replace(/^[#\s]+/, "").trim();
      a.dataset.target = h.id;

      li.appendChild(a);
      navList.appendChild(li);
      anchors.push(a);
    });

    // Highlight the heading currently in viewport.
    const linkById = new Map(anchors.map(function (a) { return [a.dataset.target, a]; }));
    let lastActive = null;
    const setActive = function (a) {
      if (lastActive === a) return;
      if (lastActive) lastActive.classList.remove("active");
      if (a) a.classList.add("active");
      lastActive = a;
    };

    if ("IntersectionObserver" in window) {
      const obs = new IntersectionObserver(function (entries) {
        // Pick the top-most heading currently intersecting.
        const visible = entries
          .filter(function (e) { return e.isIntersecting; })
          .map(function (e) { return e.target; });
        if (visible.length > 0) {
          visible.sort(function (a, b) {
            return a.getBoundingClientRect().top - b.getBoundingClientRect().top;
          });
          const link = linkById.get(visible[0].id);
          if (link) setActive(link);
        }
      }, { rootMargin: "-10% 0px -70% 0px", threshold: 0 });
      headings.forEach(function (h) { obs.observe(h); });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildToc);
  } else {
    buildToc();
  }
})();
