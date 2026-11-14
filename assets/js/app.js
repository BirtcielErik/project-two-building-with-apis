// Small site-wide behaviors for One More Chapter.

// How long a success toast stays on screen, in milliseconds.
const TOAST_LIFETIME_MS = 4000;

// Schedule every toast inside `root` to fade out and disappear.
function dismissToastsLater(root) {
  root.querySelectorAll("[data-toast]:not([data-toast-scheduled])").forEach((toast) => {
    toast.setAttribute("data-toast-scheduled", "");
    setTimeout(() => {
      toast.style.transition = "opacity 300ms";
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, TOAST_LIFETIME_MS);
  });
}

// Toasts rendered with the full page.
document.addEventListener("DOMContentLoaded", () => dismissToastsLater(document));

// Toasts that arrive later through HTMX swaps.
document.addEventListener("htmx:load", (event) => dismissToastsLater(event.target));

// --- Book covers -------------------------------------------------------------
// A cover <img data-cover> sits next to a hidden [data-cover-placeholder].
// If the image fails to load, remove it and show the placeholder instead.
function showCoverPlaceholder(img) {
  const placeholder = img.parentElement.querySelector("[data-cover-placeholder]");
  if (placeholder) {
    placeholder.classList.remove("hidden");
    placeholder.classList.add("flex");
  }
  img.remove();
}

// Image errors don't bubble up, so listen in the "capture" phase instead.
document.addEventListener(
  "error",
  (event) => {
    if (event.target instanceof HTMLImageElement && event.target.matches("[data-cover]")) {
      showCoverPlaceholder(event.target);
    }
  },
  true,
);

// Covers that already failed before this script ran.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("img[data-cover]").forEach((img) => {
    if (img.complete && img.naturalWidth === 0) showCoverPlaceholder(img);
  });
});
