/* Non-module: runs on all pages. Makes clear this is not a real bank (helps reviewers & users). */
(function () {
  if (document.getElementById("jpnd-demo-site-banner")) return;

  var bar = document.createElement("div");
  bar.id = "jpnd-demo-site-banner";
  bar.className = "demo-site-banner";
  bar.setAttribute("role", "banner");
  bar.innerHTML =
    "<p class=\"demo-site-banner__inner\"><strong>Educational demo only.</strong> " +
    "This site is a student / portfolio project (fictional &ldquo;JPND Bank&rdquo;). " +
    "It is <strong>not</strong> a real bank or financial institution. " +
    "Do not use real passwords, card numbers, government IDs, or banking credentials.</p>";

  document.body.insertBefore(bar, document.body.firstChild);

  if (document.getElementById("jpnd-demo-jsonld")) return;
  var ld = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "JPND Bank (educational demo)",
    description:
      "Non-commercial educational and portfolio website simulating banking UI. Not a real bank; no regulated financial services; no real funds.",
    url: window.location.origin || "",
  };
  var script = document.createElement("script");
  script.id = "jpnd-demo-jsonld";
  script.type = "application/ld+json";
  script.textContent = JSON.stringify(ld);
  document.head.appendChild(script);
})();
