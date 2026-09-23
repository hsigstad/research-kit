"""In-page table of contents — ships on the paper page only.

A single self-contained block (CSS + JS) appended to the nav injection when
``inject_nav(..., include_toc=True)``. Only the paper content page opts in
(see ``paper._render_paper_html``); doc pages and other pages leave it off.
The JS builds the TOC client-side from the headings inside ``<main>``
(assigning slug ids where missing), so it needs nothing from the LaTeX/make4ht
or markdown pipelines.

Layout follows the spec:
- **Wide screens (>=1200px):** a fixed sidebar living in the empty left margin
  (``main`` is centered at ``max-width: 42rem``, leaving room in the gutter).
- **Narrow / phones:** a bottom-left floating button toggles an off-canvas
  panel with a backdrop. The same panel element is reused for both.

It stays out of the way: if a page has fewer than two headings the whole thing
removes itself, so short pages (index, stubs) show nothing.
"""

from __future__ import annotations

# NOTE: kept as one string so nav.py can append it verbatim after NAV_JS.
# Uses the CSS custom properties every template defines (--card, --border,
# --accent, --muted, --fg) so it inherits each project's palette.
TOC_BLOCK = """\
<style id="site-toc-css">
  #site-toc-panel {
    position: fixed; z-index: 95; overflow-y: auto;
    background: var(--card); -webkit-overflow-scrolling: touch;
  }
  #site-toc {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  #site-toc .toc-title {
    font-size: .68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: var(--muted); padding: 0 .6rem .45rem;
  }
  #site-toc ol { list-style: none; margin: 0; padding: 0; }
  #site-toc li { margin: 0; }
  #site-toc a {
    display: block; padding: .17rem .6rem; color: var(--muted);
    text-decoration: none; font-size: .82rem; line-height: 1.35;
    border-left: 2px solid transparent;
  }
  #site-toc a:hover { color: var(--fg); }
  #site-toc a.toc-d0 { font-weight: 600; color: var(--fg); }
  #site-toc a.toc-d1 { padding-left: 1.5rem; font-size: .8rem; }
  #site-toc a.toc-d2 { padding-left: 2.4rem; font-size: .78rem; }
  #site-toc a.active {
    color: var(--accent); border-left-color: var(--accent);
    background: rgba(37, 99, 235, .07);
  }
  .toc-close {
    float: right; background: none; border: none; font-size: 1.4rem;
    line-height: 1; color: var(--muted); cursor: pointer; padding: 0 .2rem;
  }

  /* Narrow / phones: off-canvas panel from the left + bottom-left button. */
  @media (max-width: 1199.98px) {
    #site-toc-panel {
      left: 0; top: 0; bottom: 0; width: min(20rem, 82vw);
      padding: 3.4rem .7rem 2rem; border-right: 1px solid var(--border);
      box-shadow: 4px 0 22px rgba(0, 0, 0, .18);
      transform: translateX(-100%); transition: transform .22s ease;
    }
    body.toc-open #site-toc-panel { transform: none; }
    body.toc-open #site-toc-backdrop { opacity: 1; pointer-events: auto; }
  }
  #site-toc-backdrop {
    position: fixed; inset: 0; z-index: 94; background: rgba(0, 0, 0, .35);
    opacity: 0; pointer-events: none; transition: opacity .2s;
  }
  #site-toc-fab {
    position: fixed; left: 1rem; bottom: 1rem; z-index: 90;
    display: inline-flex; align-items: center; gap: .4rem;
    background: #212529; color: #fff; border: none; border-radius: 2rem;
    padding: .6rem .95rem; font-size: .8rem; font-family: inherit;
    cursor: pointer; box-shadow: 0 3px 12px rgba(0, 0, 0, .25);
  }
  #site-toc-fab:hover { background: #343a40; }

  /* Wide screens: fixed sidebar in the left gutter, always visible. */
  @media (min-width: 1200px) {
    #site-toc-panel {
      top: 3rem; left: 0; width: calc((100vw - 42rem) / 2 - 1rem);
      min-width: 12rem; max-width: 17rem; max-height: calc(100vh - 4rem);
      padding: 1.2rem .6rem 1.2rem 1rem; transform: none !important;
    }
    #site-toc-fab, #site-toc-backdrop, .toc-close { display: none !important; }
  }
</style>
<script>
(function () {
  function slug(t) {
    return t.toLowerCase().trim().replace(/[^\\w\\s-]/g, '')
      .replace(/\\s+/g, '-').replace(/-+/g, '-').slice(0, 60) || 'sec';
  }
  document.addEventListener('DOMContentLoaded', function () {
    var main = document.querySelector('main');
    if (!main) return;
    function lvl(h) { return +h.tagName.slice(1); }
    var hs = Array.prototype.slice.call(main.querySelectorAll('h1, h2, h3, h4'))
      .filter(function (h) { return h.textContent.trim().length; });
    if (hs.length < 2) return;  // short page: no clutter
    // Drop a leading page title (a unique heading above the section level), so
    // TOC depth is relative: sections sit at depth 0 whether they are h2 or h3.
    if (lvl(hs[1]) > lvl(hs[0]) &&
        hs.filter(function (h) { return lvl(h) === lvl(hs[0]); }).length === 1) {
      hs = hs.slice(1);
    }
    if (hs.length < 2) return;
    var levels = hs.map(lvl).filter(function (v, i, a) { return a.indexOf(v) === i; })
      .sort(function (a, b) { return a - b; });

    var nav = document.createElement('nav');
    nav.id = 'site-toc';
    nav.setAttribute('aria-label', 'Table of contents');
    var title = document.createElement('div');
    title.className = 'toc-title';
    title.textContent = 'On this page';
    nav.appendChild(title);
    var ol = document.createElement('ol');
    nav.appendChild(ol);

    var byId = {};
    hs.forEach(function (h) {
      if (!h.id) {
        var base = slug(h.textContent), s = base, i = 2;
        while (document.getElementById(s)) { s = base + '-' + (i++); }
        h.id = s;
      }
      var a = document.createElement('a');
      a.href = '#' + h.id;
      a.textContent = h.textContent.trim();
      a.className = 'toc-d' + Math.min(levels.indexOf(lvl(h)), 2);
      a.dataset.target = h.id;
      var li = document.createElement('li');
      li.appendChild(a);
      ol.appendChild(li);
      byId[h.id] = a;
    });

    var panel = document.createElement('aside');
    panel.id = 'site-toc-panel';
    var close = document.createElement('button');
    close.className = 'toc-close';
    close.setAttribute('aria-label', 'Close table of contents');
    close.innerHTML = '&times;';
    panel.appendChild(close);
    panel.appendChild(nav);

    var backdrop = document.createElement('div');
    backdrop.id = 'site-toc-backdrop';
    var fab = document.createElement('button');
    fab.id = 'site-toc-fab';
    fab.setAttribute('aria-label', 'Table of contents');
    fab.setAttribute('aria-expanded', 'false');
    fab.innerHTML = '<span aria-hidden="true">&#9776;</span> Contents';

    document.body.appendChild(panel);
    document.body.appendChild(backdrop);
    document.body.appendChild(fab);

    function open() {
      document.body.classList.add('toc-open');
      fab.setAttribute('aria-expanded', 'true');
    }
    function shut() {
      document.body.classList.remove('toc-open');
      fab.setAttribute('aria-expanded', 'false');
    }
    fab.addEventListener('click', function () {
      document.body.classList.contains('toc-open') ? shut() : open();
    });
    backdrop.addEventListener('click', shut);
    close.addEventListener('click', shut);
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') shut();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') shut();
    });

    // Scrollspy: highlight the section nearest the top of the viewport.
    var current = null;
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var a = byId[en.target.id];
        if (!a || a === current) return;
        if (current) current.classList.remove('active');
        a.classList.add('active');
        current = a;
      });
    }, { rootMargin: '0px 0px -75% 0px', threshold: 0 });
    hs.forEach(function (h) { spy.observe(h); });
  });
})();
</script>
"""
