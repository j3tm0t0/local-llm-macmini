/**
 * Minimal click-to-zoom lightbox for .main-content img.
 * - Click image → fullscreen overlay
 * - Click overlay / close button / press Esc → close
 */
(function () {
  function init() {
    const imgs = document.querySelectorAll(".main-content img");
    if (imgs.length === 0) return;

    const overlay = document.createElement("div");
    overlay.id = "lightbox-overlay";
    overlay.innerHTML =
      '<img class="lightbox-img" alt="">' +
      '<button class="lightbox-close" aria-label="Close (Esc)" type="button">&times;</button>';
    document.body.appendChild(overlay);

    const overlayImg = overlay.querySelector(".lightbox-img");
    const closeBtn = overlay.querySelector(".lightbox-close");

    function open(src, alt) {
      overlayImg.src = src;
      overlayImg.alt = alt || "";
      overlay.classList.add("open");
      document.body.style.overflow = "hidden";
    }
    function close() {
      overlay.classList.remove("open");
      document.body.style.overflow = "";
      // Clear src after fade to avoid visual flicker on reopen
      setTimeout(function () { overlayImg.src = ""; }, 220);
    }

    imgs.forEach(function (img) {
      img.style.cursor = "zoom-in";
      img.addEventListener("click", function () {
        open(img.currentSrc || img.src, img.alt);
      });
    });

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay || e.target === closeBtn) close();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && overlay.classList.contains("open")) close();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
