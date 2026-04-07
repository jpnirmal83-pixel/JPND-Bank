exports.handler = async (event) => {
  const origin = (process.env.JPND_API_ORIGIN || "").trim().replace(/\/+$/, "");
  if (!origin) {
    return {
      statusCode: 500,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        detail:
          "Netlify API proxy is not configured. Set JPND_API_ORIGIN to your backend origin (example: https://api.yourdomain.com).",
      }),
    };
  }

  const path = (event.path || "").replace(/^\/\.netlify\/functions\/api-proxy\/?/, "");
  const query = event.rawQuery || "";
  const target = `${origin}/api/${path}${query ? `?${query}` : ""}`;

  try {
    const headers = { ...(event.headers || {}) };
    delete headers.host;
    delete headers["x-forwarded-for"];
    delete headers["x-forwarded-proto"];
    delete headers["x-nf-client-connection-ip"];
    delete headers["content-length"];

    const init = {
      method: event.httpMethod || "GET",
      headers,
    };

    if (event.body && !["GET", "HEAD"].includes(init.method)) {
      init.body = event.isBase64Encoded
        ? Buffer.from(event.body, "base64")
        : event.body;
    }

    const res = await fetch(target, init);
    const bodyBuffer = Buffer.from(await res.arrayBuffer());
    const contentType = res.headers.get("content-type") || "application/json";

    return {
      statusCode: res.status,
      headers: {
        "content-type": contentType,
      },
      body: bodyBuffer.toString("base64"),
      isBase64Encoded: true,
    };
  } catch (err) {
    return {
      statusCode: 502,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        detail: "Unable to reach backend API from Netlify proxy.",
        error: String((err && err.message) || err || "unknown"),
      }),
    };
  }
};
