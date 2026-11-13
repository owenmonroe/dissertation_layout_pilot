// Three Magazines, Sixteen Topics: a small hash-routed site.
//   #/                 the 16 topics
//   #/topic/<id>       a topic's top three articles
//   #/article/<id>     an article: text, figures, closest article, topics in its issue
// Data comes from data/, built by build_site.py.

const app = document.getElementById("app");
let DATA = null;
const articleCache = {};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function cap(s) { return s ? s[0].toUpperCase() + s.slice(1) : s; }
function pct(x) { return `${Math.round(x * 100)}%`; }
// MM-DD-YYYY -> "Feb 4, 1843"; MM-YYYY -> "Aug 1834"
function date(d) {
  const p = String(d || "").split("-");
  if (p.length === 3) return `${MONTHS[+p[0] - 1]} ${+p[1]}, ${p[2]}`;
  if (p.length === 2) return `${MONTHS[+p[0] - 1]} ${p[1]}`;
  return d || "";
}
function topic(id) { return DATA.topics.find(t => t.id === id); }
function topicName(id) { return cap(topic(id).label); }
function source(a) {
  return `<i>${esc(a.magazine)}</i>, No. ${esc(a.issue)}, ${esc(date(a.date))}, ${esc(a.pages)}` +
    (a.us_reprint ? `<span class="badge" title="American reprint of the Edinburgh edition">US reprint</span>` : "");
}

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

// --- Views -------------------------------------------------------------------------

function home() {
  document.title = "Three Magazines, Sixteen Topics";
  const m = DATA.meta;
  const cards = [...DATA.topics].sort((a, b) => b.share - a.share).map(t => `
    <a class="topic-card" href="#/topic/${t.id}">
      <span class="num">TOPIC ${t.id}</span>
      <span class="name">${esc(cap(t.label))}</span>
      <span class="words">${esc(t.words.slice(0, 6).join(", "))}</span>
      <div class="bar" aria-hidden="true"><i style="width:${Math.max(2, t.share / 0.18 * 100)}%"></i></div>
      <span class="stat">${pct(t.share)} of all words · ${t.n_main} article${t.n_main === 1 ? "" : "s"} mainly on it</span>
    </a>`).join("");
  app.innerHTML = `
    <p class="lede">A topic model read ${m.articles.toLocaleString()} articles
      (${(m.words / 1000).toFixed(0)},000 words) from ${m.issues} issues of three magazines,
      ${m.years[0]}–${m.years[1]}, and found sixteen recurring subjects. Choose a topic to see
      the articles that carry it most, then follow the threads from article to article.</p>
    <h2>The sixteen topics, largest first</h2>
    <div class="grid">${cards}</div>`;
}

function topicView(id) {
  const t = topic(id);
  if (!t) return notFound();
  document.title = `${cap(t.label)} · Three Magazines, Sixteen Topics`;
  const items = t.articles.map((a, i) => `
    <a class="article-card" href="#/article/${encodeURIComponent(a.id)}">
      <span class="rank">${i + 1}</span>
      <span class="title">${esc(a.title)}</span>
      <span class="meta">${source(a)}</span>
      <span class="share"><span class="bar"><i style="width:${a.topic_share * 100}%"></i></span>
        ${pct(a.topic_share)} of the article is on this topic</span>
    </a>`).join("");
  app.innerHTML = `
    <nav class="crumbs"><a href="#/">All topics</a></nav>
    <div class="topic-head">
      <p class="kicker">Topic ${t.id}</p>
      <h1>${esc(cap(t.label))}</h1>
      <p class="wordline">${esc(t.words.join(" · "))}</p>
      <p class="meta">${pct(t.share)} of all words · ${t.n_main} article${t.n_main === 1 ? "" : "s"} mainly on this topic</p>
    </div>
    <h2>The articles that carry it most</h2>
    <div class="article-list">${items}</div>`;
}

async function articleView(id, from) {
  app.innerHTML = `<p class="loading">Loading…</p>`;
  let a = articleCache[id];
  if (!a) {
    try { a = articleCache[id] = await getJSON(`data/articles/${encodeURIComponent(id)}.json`); }
    catch { return notFound(); }
  }
  document.title = `${a.title} · Three Magazines, Sixteen Topics`;
  const back = from != null && topic(from) ? from : a.topic;

  const mix = a.mix.map((m, i) => `
    <a class="chip${i === 0 ? " main" : ""}" href="#/topic/${m.topic}">
      <b>${pct(m.weight)}</b> ${esc(topicName(m.topic))}</a>`).join("");

  const figures = a.figures.map(f => `
    <figure>
      <img src="${esc(f.src)}" alt="${esc(f.caption || "Illustration from the page")}" loading="lazy">
      ${f.caption || f.with ? `<figcaption>${esc(f.caption)}
        ${f.with ? `<span class="with">Printed on the same page, with “${esc(f.with)}”</span>` : ""}</figcaption>` : ""}
    </figure>`).join("");

  const text = a.text.map(p => `<p>${esc(p)}</p>`).join("");

  const c = a.closest;
  const near = c ? `
    <section class="panel">
      <h2>Closest article</h2>
      <a class="near" href="#/article/${encodeURIComponent(c.id)}">
        <span class="rel">${esc(c.relation)}</span>
        <span class="title">${esc(c.title)}</span>
        <span class="meta">Topic: ${esc(topicName(c.topic))}</span>
      </a>
    </section>` : "";

  const issue = a.issue_topics.map(t => `
    <li class="${t.topic === a.topic ? "here" : ""}"><a href="#/topic/${t.topic}">
      <span class="row"><span class="label">${esc(topicName(t.topic))}</span><span class="pct">${pct(t.share)}</span></span>
      <span class="bar" aria-hidden="true"><i style="width:${t.share * 100}%"></i></span></a></li>`).join("");

  app.innerHTML = `
    <nav class="crumbs"><a href="#/">All topics</a><span>›</span><a href="#/topic/${back}">${esc(topicName(back))}</a></nav>
    <p class="kicker">${esc(topicName(a.topic))}</p>
    <h1>${esc(a.title)}</h1>
    <p class="meta">${source(a)} · ${a.words.toLocaleString()} words</p>
    <div class="mix" aria-label="Topics in this article">${mix}</div>
    <div class="article-layout">
      <article>${figures}<div class="text">${text}</div></article>
      <aside>
        ${near}
        <section class="panel">
          <h2>Topics in this issue</h2>
          <ul class="issue-topics">${issue}</ul>
          <p class="note" style="margin-top:12px">Share of the issue's words; topics under 5% are left out.
            The issue has ${a.issue_articles} article${a.issue_articles === 1 ? "" : "s"}.</p>
        </section>
        <p class="note">Text as read by OCR from the page scans, uncorrected.</p>
      </aside>
    </div>`;
}

function notFound() {
  app.innerHTML = `<p class="error">Nothing here. <a href="#/">Back to the topics</a>.</p>`;
}

// --- Routing -----------------------------------------------------------------------

let lastTopic = null;
async function route() {
  const [, kind, id] = (location.hash.replace(/^#\/?/, "#/").match(/^#\/([^/]*)\/?(.*)$/) || []);
  if (kind === "topic") { lastTopic = +id; topicView(+id); }
  else if (kind === "article") await articleView(decodeURIComponent(id), lastTopic);
  else { lastTopic = null; home(); }
  window.scrollTo(0, 0);
}

(async () => {
  try { DATA = await getJSON("data/topics.json"); }
  catch {
    app.innerHTML = `<p class="error">The data could not be loaded. If you opened this file directly,
      serve the folder instead: <code>python -m http.server</code> inside <code>docs/</code>.</p>`;
    return;
  }
  window.addEventListener("hashchange", route);
  route();
})();
