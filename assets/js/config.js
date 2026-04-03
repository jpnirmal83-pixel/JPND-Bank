/**
 * JPND Bank — single place to aim the frontend at your API.
 *
 * Resolution order:
 *   1) window.JAYDEE_API_BASE_URL if already set (e.g. inline script before this file)
 *   2) <meta name="jpnd-api-base" content="https://your-api.example.com/api">
 *   3) JPND_DEPLOY_API_BASE below (change for production builds)
 *
 * Must resolve to the FastAPI prefix including /api (e.g. https://api.example.com/api).
 */
(function () {
  var JPND_DEPLOY_API_BASE = "http://localhost:8000/api";

  function normalizeApiBase(raw) {
    var u = (raw || "").trim();
    if (!u) return "";
    while (u.endsWith("/")) u = u.slice(0, -1);
    if (!/\/api$/i.test(u)) u += "/api";
    return u;
  }

  if (window.JAYDEE_API_BASE_URL) {
    window.JAYDEE_API_BASE_URL = normalizeApiBase(window.JAYDEE_API_BASE_URL);
    return;
  }

  var meta = document.querySelector('meta[name="jpnd-api-base"]');
  var fromMeta = meta && meta.getAttribute("content");
  fromMeta = fromMeta && fromMeta.trim();

  window.JAYDEE_API_BASE_URL = normalizeApiBase(fromMeta || JPND_DEPLOY_API_BASE);
})();
