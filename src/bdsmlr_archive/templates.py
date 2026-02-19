# src/bdsmlr_archive/templates.py

BASE_CSS = """
:root { color-scheme: dark; }
body {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  background: #0b0f14;
  color: #e6edf3;
}
header {
  padding: 24px;
  border-bottom: 1px solid #1f2a37;
  background: #070a0f;
  position: sticky;
  top: 0;
  z-index: 5;
}
h1 {
  margin: 0 0 8px 0;
  font-size: 18px;
  letter-spacing: .4px;
}
.small { opacity: .8; font-size: 12px; }
main { padding: 18px; }
.controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 12px 0 18px;
  align-items: center;
}
input, select {
  background: #0f1620;
  color: #e6edf3;
  border: 1px solid #253244;
  border-radius: 10px;
  padding: 10px 12px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.card {
  border: 1px solid #1f2a37;
  border-radius: 16px;
  padding: 14px;
  background: #0a1018;
  overflow: hidden;
}
a { color: #7dd3fc; text-decoration: none; }
a:hover { text-decoration: underline; }
.tags { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
.tag {
  font-size: 12px;
  padding: 4px 8px;
  border: 1px solid #253244;
  border-radius: 999px;
  opacity: .9;
}
.notice {
  border: 1px dashed #2b3a4f;
  padding: 12px;
  border-radius: 14px;
  opacity: .9;
}
hr { border: 0; border-top: 1px solid #1f2a37; margin: 18px 0; }

.thumb {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 12px;
  border: 1px solid #1f2a37;
  background: #06080c;
}
.media-img {
  width: 100%;
  height: auto;
  border-radius: 12px;
  border: 1px solid #1f2a37;
  background: #06080c;
}
"""

INDEX_JS = r"""
const state = { q: "", tag: "" };
const $ = (sel) => document.querySelector(sel);

function render() {
  const posts = window.__POSTS__ || [];
  const q = state.q.toLowerCase().trim();
  const tag = state.tag;

  const filtered = posts.filter((p) => {
    const hay = (p.id + " " + p.url + " " + (p.tags || []).join(" ")).toLowerCase();
    const okQ = !q || hay.includes(q);
    const okT = !tag || (p.tags || []).includes(tag);
    return okQ && okT;
  });

  $("#count").textContent = `${filtered.length} posts`;

  $("#grid").innerHTML = filtered.map((p) => {
    const tagHtml = (p.tags || []).slice(0, 8).map((t) => `<span class="tag">${t}</span>`).join("");
    const thumb = (p.thumb && p.thumb.length)
      ? `<a href="posts/${p.id}.html"><img class="thumb" src="${p.thumb}" alt="" loading="lazy" /></a>`
      : "";

    return `
      <div class="card">
        ${thumb}
        <div class="small" style="margin-top:${thumb ? "10px" : "0"}">${p.when || ""}</div>
        <div style="margin:8px 0 10px">
          <a href="posts/${p.id}.html">post/${p.id}</a>
        </div>
        <div class="small">
          <a href="${p.url}" target="_blank" rel="noreferrer">original link</a>
        </div>
        <div class="tags">${tagHtml}</div>
      </div>
    `;
  }).join("");

  if (!posts.length) {
    $("#grid").innerHTML = `<div class="notice">No posts loaded.</div>`;
  }
}

$("#search").addEventListener("input", (e) => { state.q = e.target.value; render(); });
$("#tag").addEventListener("change", (e) => { state.tag = e.target.value; render(); });

render();
"""