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
