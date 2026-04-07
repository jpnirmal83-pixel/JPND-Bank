/**
 * JPND Bank — API base URL (must end with /api).
 *
 * Netlify / Vercel static: leave JPND_DEPLOY_API_BASE "" and either:
 *   • add a host proxy so same-origin /api/* hits your FastAPI (see netlify.toml), or
 *   • set a real URL below and allow that origin in backend CORS_ORIGINS.
 */
(function () {
  /**
   * Your public FastAPI base URL, including /api. Example:
   *   "https://my-app.up.railway.app/api"
   * Leave "" if the site proxies /api to the backend (recommended on Netlify).
   */
  var JPND_DEPLOY_API_BASE = "";

  /** Treat tutorial placeholders as “not set” so we fall back to same-origin /api. */
  function isPlaceholderDeployBase(s) {
    var t = (s || "").trim().toLowerCase();
    if (!t) return true;
    return (
      t.indexOf("your-public-fastapi") !== -1 ||
      t.indexOf("your-fastapi-host") !== -1 ||
      t.indexOf("put-your-fastapi") !== -1 ||
      t.indexOf("replace-with-your-fastapi") !== -1 ||
      t.indexOf("your-actual-backend") !== -1 ||
      t.indexOf("replace_me") !== -1 ||
      /^https?:\/\/example\.com\//.test(t)
    );
  }

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

  try {
    var qs = new URLSearchParams(window.location.search);
    var qBase = qs.get("apiBase");
    if (qBase && qBase.trim()) {
      window.JAYDEE_API_BASE_URL = normalizeApiBase(qBase);
      return;
    }
  } catch (e) {
    /* ignore */
  }

  var meta = document.querySelector('meta[name="jpnd-api-base"]');
  var fromMeta = meta && meta.getAttribute("content");
  fromMeta = fromMeta && fromMeta.trim();
  if (fromMeta) {
    window.JAYDEE_API_BASE_URL = normalizeApiBase(fromMeta);
    return;
  }

  if (
    JPND_DEPLOY_API_BASE &&
    JPND_DEPLOY_API_BASE.trim() &&
    !isPlaceholderDeployBase(JPND_DEPLOY_API_BASE)
  ) {
    window.JAYDEE_API_BASE_URL = normalizeApiBase(JPND_DEPLOY_API_BASE);
    return;
  }

  var proto = window.location.protocol || "";
  var host = window.location.hostname || "";
  var isFile = proto === "file:";
  var isLocal =
    isFile ||
    host === "localhost" ||
    host === "127.0.0.1" ||
    host === "[::1]";

  var auto = isLocal
    ? "http://localhost:8000/api"
    : (window.location.origin || "").replace(/\/$/, "") + "/api";

  window.JAYDEE_API_BASE_URL = normalizeApiBase(auto);
})();
