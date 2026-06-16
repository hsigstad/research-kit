# Pseudocode block

Optional `pseudocode: str | None` field on `DatasetConfig`. Renders as a
`<pre class="pseudocode">` block near the top of the dataset page; the
template rewrites bracketed `[name]` tokens to hyperlinks to
`data/<name>.html`. Lets the description / notes blocks stay short — the
construction logic lives in one canonical place where every input is a
clickable link to its own page.

## Add to source/summary/config.py

On `DatasetConfig`:

```python
# Pseudocode summary of how the dataset is built. Bracketed names
# like [poll_2024] are rewritten to hyperlinks to data/<name>.html.
pseudocode: str | None = None
```

## Add to source/summary/compute.py

In the returned summary dict:

```python
"pseudocode": getattr(config, "pseudocode", None),
```

## CSS — add to templates/dataset.html

```css
.pseudocode { background: var(--card); border: 1px solid var(--border);
              border-radius: 6px; padding: .9rem 1.1rem;
              font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
              font-size: .82rem; line-height: 1.55;
              white-space: pre; overflow-x: auto; margin: 0 0 1rem; }
.pseudocode a { color: var(--accent); text-decoration: none;
                background: #f0ede6; padding: 0 .25em; border-radius: 2px; }
.pseudocode a:hover { text-decoration: underline; }
```

## Placeholder — add to templates/dataset.html

Above the existing notes section:

```html
<!-- Pseudocode (how this dataset is built) -->
<div id="pseudocode-section"></div>
```

## JS block — add to templates/dataset.html

```js
// Pseudocode — render DATA.pseudocode as a <pre> with [name] tokens
// rewritten to hyperlinks to data/<name>.html. Skipped when no
// pseudocode is set.
(function() {
  if (!DATA.pseudocode) return;
  var section = document.getElementById('pseudocode-section');
  var h2 = document.createElement('h2');
  h2.className = 'section-title';
  h2.textContent = 'How this dataset is built';
  section.appendChild(h2);
  var pre = document.createElement('pre');
  pre.className = 'pseudocode';
  var esc = function(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  };
  var html = esc(DATA.pseudocode).replace(
    /\[([A-Za-z][A-Za-z0-9_-]*)\]/g,
    function(_, name) {
      return '<a href="' + name + '.html">' + name + '</a>';
    }
  );
  pre.innerHTML = html;
  section.appendChild(pre);
})();
```

## Style for the prose

Keep it readable; one block, ~15-25 lines:

- Lead with input datasets in `[brackets]`, one block per input.
- Indent operations under each input.
- End with derived fields, grain assertions, or similar.

Example (poll-sponsor-bias cand_poll):

```
from [poll_2024]:
    filter scenario_type == "estimulado"
    drop aggregate candidate names (BRANC, NULO, NSNR, …)
    filter match_score ≥ 2
    per protocol, pick canonical scenario:
        the scenario_label with the most distinct candidates

from [poll_sponsor_2024_candidate]:
    pull (protocol, politico_id, route_used) sponsor links
    sponsored_by, opponent_sponsored flags

from candidato.csv (TSE):
    final_share, final_rank, race_margin, prior_prefeito_runs

from [poll]:
    join sponsor_types, pollster_cnpj, st_pesquisa_propria,
         field_period_week, ...

dedup on (protocol, politico_id) keeping max match_score
assert unique on (protocol, politico_id)
```

When the description + pseudocode together tell the construction story,
the `notes` field can usually be emptied.
