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

// --- Clean URLs for filter forms ---------------------------------------------
// A form marked [data-drop-empty-params] leaves blank fields out of its HTMX
// request, so the pushed URL is "/shelf/?status=finished" rather than
// "/shelf/?q=&status=finished&min_rating=&rated=&ordering=".
document.addEventListener("htmx:configRequest", (event) => {
  if (!event.detail.elt.matches("[data-drop-empty-params]")) return;
  const data = event.detail.formData || event.detail.parameters;
  for (const key of new Set(data.keys())) {
    if (data.getAll(key).every((value) => value === "")) data.delete(key);
  }
});

// --- My Shelf ----------------------------------------------------------------
// "Clear filters" links: empty the search box, pick the "any" choice of every
// filter (the radio whose value is ""), and re-run the form through HTMX.
// The chosen sort order is kept. Without JavaScript the link just opens /shelf/.
document.addEventListener("click", (event) => {
  const link = event.target.closest("[data-clear-filters]");
  const form = document.getElementById("shelf-filters");
  if (!link || !form) return;
  event.preventDefault();
  form.querySelectorAll('input[type="search"]').forEach((input) => (input.value = ""));
  form.querySelectorAll('input[type="radio"][value=""]').forEach((radio) => (radio.checked = true));
  form.requestSubmit();
});

// The phone "Filters" button shows or hides the filter sidebar.
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-toggle-filters]");
  if (!button) return;
  const sidebar = document.getElementById(button.getAttribute("aria-controls"));
  const hidden = sidebar.classList.toggle("hidden");
  button.setAttribute("aria-expanded", String(!hidden));
});

// --- Book detail page ----------------------------------------------------------
// The rating's "Clear" button picks the hidden "no rating" star (value ""),
// so the next Save removes the rating.
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear-rating]");
  if (!button) return;
  const noRating = button.form.querySelector('input[name="rating"][value=""]');
  if (noRating) noRating.checked = true;
});

// A form marked [data-confirm-dialog="<dialog id>"] asks first: submitting it
// opens that <dialog> instead. The dialog's button marked [data-confirmed]
// submits the form for real. Without JavaScript the form just submits.
document.addEventListener("submit", (event) => {
  const form = event.target;
  const dialogId = form.getAttribute("data-confirm-dialog");
  if (!dialogId || event.submitter?.hasAttribute("data-confirmed")) return;
  event.preventDefault();
  document.getElementById(dialogId).showModal();
});

// Covers that already failed before this script ran.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("img[data-cover]").forEach((img) => {
    if (img.complete && img.naturalWidth === 0) showCoverPlaceholder(img);
  });
});
