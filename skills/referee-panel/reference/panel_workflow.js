// Reusable finding-level mechanical auditor panel over an empirical-economics paper build.
// Borrows the pattern from github.com/Ingar30/reviewer: many single-failure-mode auditors,
// a shared cannot_verify-or-cite finding contract, an adversarial verify pass, an editor synthesis.
//
// Parameterized entirely through `args` (pass real JSON to Workflow, not a stringified blob):
//   {
//     project:   "deterrence",                       // human label for the memo
//     target:    "paper/oe.tex",                     // which build is under review (label only)
//     dir:       "/workspace/projects/deterrence/paper",  // ABSOLUTE dir the sources live in
//     sources:   ["oe.tex","shared/intro_oe.tex","shared/framework.tex","shared/methods.tex",
//                 "shared/results.tex","shared/discussion.tex","shared/si.tex"],  // reading order, relative to dir
//     numbers:   "numbers.json",                     // optional: numerical-claim ledger (relative to dir), or null
//     one_liner: "Accuracy-equivalent model classes have opposite incentive properties...",  // orients every auditor
//     lenses:    null                                // optional array of lens keys to run a subset; null = all 12
//   }
// Returns { counts, confirmed, memo }. The CALLER (skill) persists memo + confirmed to the repo;
// workflow scripts have no filesystem access.

export const meta = {
  name: 'referee-panel',
  description: 'Finding-level mechanical auditor panel over an empirical-economics paper (N lenses -> adversarial verify -> editorial synthesis)',
  phases: [
    { title: 'Audit', detail: 'each auditor lens reads the build and returns structured findings' },
    { title: 'Verify', detail: 'per-lens adversarial skeptic tries to refute each finding' },
    { title: 'Synthesize', detail: 'editor dedups, ranks, writes the memo' },
  ],
}

// ---------------- args ----------------
const A = args || {}
const DIR = A.dir
const SOURCES = Array.isArray(A.sources) ? A.sources : []
if (!DIR || !SOURCES.length) {
  throw new Error('referee-panel: args must include {dir, sources[...]}. See SKILL.md.')
}
const NUMBERS = A.numbers ? `${DIR}/${A.numbers}` : null
const ONELINER = A.one_liner || '(no one-line summary provided; infer the thesis from the abstract and intro)'
const PROJECT = A.project || 'this paper'
const TARGET = A.target || SOURCES[0]
const ABS = SOURCES.map((s) => `${DIR}/${s}`)
const FILE_LINES = [
  ...ABS.map((p) => `- ${p}`),
  ...(NUMBERS ? [`- ${NUMBERS}  (JSON ledger of numerical claims: macro / value / source / interpretation)`] : []),
].join('\n')

// ---------------- shared finding schema (the reviewer_contract discipline) ----------------
const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['finding_id', 'summary', 'claim_text', 'location', 'assessment', 'issue_type', 'severity', 'confidence', 'source_objects'],
        properties: {
          finding_id: { type: 'string', description: 'stable, PREFIX-001, PREFIX-002, ...' },
          summary: { type: 'string', description: 'the defect stated directly, one sentence' },
          claim_text: { type: 'string', description: 'the manuscript assertion being tested, quoted or closely paraphrased' },
          location: { type: 'string', description: 'section name and/or file:line' },
          assessment: { enum: ['supported', 'not_supported', 'partially', 'cannot_verify'] },
          issue_type: { enum: ['manuscript_issue', 'artifact', 'cannot_verify'] },
          severity: { enum: ['blocking', 'major', 'minor'] },
          confidence: { enum: ['high', 'medium', 'low'] },
          source_objects: { type: 'array', items: { type: 'string' }, description: 'repo-relative paths / table / figure / ledger macro used as evidence' },
          cannot_verify_reason: { type: 'string' },
          suggested_fix: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['verdicts'],
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['finding_id', 'verdict', 'reason'],
        properties: {
          finding_id: { type: 'string' },
          verdict: { enum: ['holds', 'refuted', 'uncertain'] },
          reason: { type: 'string', description: 'why it holds or is refuted, citing the paper' },
          revised_severity: { enum: ['blocking', 'major', 'minor'] },
        },
      },
    },
  },
}

const CONTRACT = `You are a finding-level auditor doing a PRE-SUBMISSION red-team of an empirical-economics
paper build (${PROJECT}; build under review: ${TARGET}).

The paper in one line: ${ONELINER}

Read these source files with Read/Grep (follow \\input into shared/ and build/ where a lens needs it):
${FILE_LINES}

CONTRACT (follow exactly -- this is the reviewer_contract):
- Audit ONLY your assigned remit. If the paper has no material in your remit, return an EMPTY
  findings array. Absence of something outside your remit is not a defect.
- Work from the paper text${NUMBERS ? ' and the numbers ledger' : ''}. For literature/positioning you may use your
  own knowledge, but do NOT invent quotations or citations. Do NOT reconstruct missing data or infer
  numeric values that are not in the artifacts.
- Report ONLY material problems that require correction, each an INDEPENDENTLY FIXABLE defect. Do NOT
  list strengths. Do NOT report wording/style preferences unless they change meaning.
- Preserve exact signs, decimals, units, and labels when you quote.
- When the artifacts do not let you check a claim, set assessment=cannot_verify with a concrete
  cannot_verify_reason -- never guess.
- finding_id must be stable, formatted PREFIX-001, PREFIX-002, ... using YOUR lens prefix.
- location: cite the section name and/or a file:line.
- Return AT MOST your 6 most important findings, most severe first.
- Do NOT include process notes about tooling, skills, or session state.`

// ---------------- the lens catalog (general empirical-econ failure modes) ----------------
const ALL_LENSES = [
  { key: 'identification', prefix: 'ID', focus:
`Identification & causal interpretation. Does causal language match what the design supports? Check
estimand/population/treatment/outcome/timing alignment; the identifying assumptions (stated and
unstated); threats from confounding, selection, spillovers, timing, measurement. Flag mechanism
language ("driven by", "because", "underlying mechanism") where the design does not identify it, and
any gap between what is measured and what is claimed to be affected.` },
  { key: 'claim-evidence', prefix: 'CE', focus:
`Claim-evidence alignment. Every headline/abstract claim must trace to a SPECIFIC result, table,
figure, or ledger number. Flag claims stronger than the evidence, results cited for a claim they do
not establish, and stated effects with no reported number/CI behind them.` },
  { key: 'numerical', prefix: 'NUM', focus:
`Numerical consistency. Cross-check ledger values against how each is stated in the text; check
internal arithmetic (sums, differences, shares, Ns, CIs); verify each ledger entry's stated source
matches its interpretation; catch sign/decimal/unit errors and numbers in text but not the ledger
(or vice versa).` },
  { key: 'model-equation', prefix: 'EQ', focus:
`Model & equation correctness. Check that definitions are internally consistent, derivations valid,
first-order conditions and thresholds correctly follow from the stated objective, and notation is
used consistently across the framework, main text, and appendix.` },
  { key: 'theory-logic', prefix: 'TH', focus:
`Theory-logic. Do the propositions follow from the STATED assumptions? Is each assumption stated
where it is used? Any hidden assumption, gap in a proof, or counterexample to a "coincide" /
"optimal" / "eliminates" / "implies" claim? Are qualitative bridges ("large X implies extreme Y")
non-sequiturs?` },
  { key: 'robustness', prefix: 'RB', focus:
`Robustness & specification sensitivity. Would the headline results flip under reasonable alternative
specifications, sample restrictions, or modelling/measurement choices? Are the robustness checks a
referee will demand present, or is their absence a hole? Small-sample fragility, single-draw or
single-seed dependence, promised-but-missing checks.` },
  { key: 'sample-construction', prefix: 'SC', focus:
`Sample construction & selection. Is the universe defined precisely? Are sample-selection / attrition
/ inclusion rules stated? Does selection into the sample (e.g. litigation, survey response, take-up)
threaten the interpretation? Are the Ns for each analysis stated and consistent, and are "balanced"
or "matched" samples defined by their balancing variable and base rate?` },
  { key: 'abstract-conclusion', prefix: 'AC', focus:
`Abstract-conclusion consistency. Does the abstract promise exactly what the results and discussion
deliver? Flag overclaim in the abstract relative to hedges in the body, headline counts/quantifiers
that the body contradicts, and conclusion statements not supported by a reported result.` },
  { key: 'literature', prefix: 'LIT', focus:
`Literature & positioning. Is the contribution correctly placed against the closest prior work? Any
must-cite work missing, any claim miscited, novelty overstated? Check for bib entries that are
present but cited nowhere (intended-but-unwired positioning) and named results attributed to the
wrong paper.` },
  { key: 'external-validity', prefix: 'EV', focus:
`Limitations & external validity. Flag scope overreach: generalization from the specific setting to
"in general", from a proxy/behavioral measure to the real-world outcome, and any claim of durability
across time / populations / technologies. Are the limitations that bound these claims actually
stated where the claims are made?` },
  { key: 'measurement-validity', prefix: 'MV', focus:
`Measurement & data validity. Are key variables/instruments measured validly and reproducibly? For
any ML- or LLM-derived measure: judge/rater independence, prompt sensitivity, training-data
contamination, number of draws, and whether the measurement procedure is reproducible enough to
support the claims built on it. Flag measures whose construction is asserted but not documented.` },
  { key: 'power-multiple-testing', prefix: 'PW', focus:
`Statistical power & multiple testing. Are KEY NULLS adequately POWERED, or just wide CIs dressed as
evidence of no effect? (A tight, precisely-estimated null is a finding; an underpowered one is not.)
Is inference reported SYMMETRICALLY across the arms of a central contrast, or does one arm get CIs
and the other none? Are CIs reported, correctly interpreted, degenerate-at-display-rounding, and is
multiple-comparison exposure handled or acknowledged?` },
]

const LENSES = A.lenses && A.lenses.length
  ? ALL_LENSES.filter((l) => A.lenses.includes(l.key))
  : ALL_LENSES
if (!LENSES.length) throw new Error('referee-panel: args.lenses matched no known lens keys.')

function auditPrompt(lens) {
  return `${CONTRACT}

YOUR LENS: ${lens.key}  (finding_id prefix: ${lens.prefix})
${lens.focus}

Return one JSON object matching the findings schema. Use prefix ${lens.prefix} for finding_id.`
}

function verifyPrompt(lens, findings) {
  return `You are an adversarial skeptic verifying the findings a "${lens.key}" auditor raised on an
empirical-economics paper (${PROJECT}). Your job is to REFUTE, not to polish. For each finding,
re-read the relevant part of the paper and decide whether the defect is REAL.

Read as needed:
${FILE_LINES}

For each finding return a verdict:
- "refuted": the auditor misread the paper, the point is already addressed/hedged in the text, or the
  claimed defect is not actually a defect. Default here when the case is weak.
- "holds": you independently confirmed the defect is real and material.
- "uncertain": genuinely can't tell from the artifacts (say why in reason).
Cite the paper (section or file:line) in every reason. Optionally set revised_severity if the auditor
mis-sized it.

FINDINGS TO VERIFY (JSON):
${JSON.stringify(findings, null, 2)}

Return one JSON object matching the verdicts schema, one verdict per finding_id above.`
}

// ---------------- run: pipeline so each lens verifies as soon as its audit lands ----------------
phase('Audit')
const reviewed = await pipeline(
  LENSES,
  (lens) => agent(auditPrompt(lens), { label: `audit:${lens.key}`, phase: 'Audit', schema: FINDINGS_SCHEMA })
              .then((r) => ({ lens, findings: (r && r.findings) || [] })),
  (rf) => {
    if (!rf || !rf.findings.length) return { ...(rf || {}), verdicts: [] }
    return agent(verifyPrompt(rf.lens, rf.findings), { label: `verify:${rf.lens.key}`, phase: 'Verify', schema: VERDICT_SCHEMA })
             .then((v) => ({ ...rf, verdicts: (v && v.verdicts) || [] }))
  },
)

// ---------------- attach verdicts, drop refuted ----------------
const confirmed = []
let raw = 0, refuted = 0
for (const rf of reviewed) {
  if (!rf || !rf.findings) continue
  const vmap = new Map((rf.verdicts || []).map((v) => [v.finding_id, v]))
  for (const f of rf.findings) {
    raw++
    const v = vmap.get(f.finding_id)
    const verdict = (v && v.verdict) || 'uncertain'
    if (verdict === 'refuted') { refuted++; continue }
    confirmed.push({
      ...f,
      lens: rf.lens.key,
      verdict,
      verify_reason: (v && v.reason) || '',
      severity: (v && v.revised_severity) || f.severity,
    })
  }
}
log(`audited ${LENSES.length} lenses -> ${raw} raw findings, ${refuted} refuted, ${confirmed.length} survive`)

// ---------------- editorial synthesis (free-form markdown, no schema) ----------------
phase('Synthesize')
const editorPrompt = `You are the handling editor assembling a pre-submission audit memo for the paper
"${PROJECT}" (build under review: ${TARGET}). Below are findings from a ${LENSES.length}-lens auditor
panel that already survived an adversarial verify pass.

Write a clean markdown memo. ASCII only (house referee-report style: no smart quotes, em dashes as
"--", no unicode). Structure:

1. "## Editor summary" -- one paragraph: overall read, and the 2-4 issues most likely to sink or
   bounce the paper. Elevate an issue to blocking if multiple independent lenses converged on it.
2. "## Blocking issues", "## Major issues", "## Minor issues" -- ranked within each by confidence.
   MERGE near-duplicate findings that different lenses raised about the same underlying problem (note
   which lenses converged). For each issue give: a bold one-line title; the location; the claim/defect;
   the suggested fix; and a tag line "lens: <lens(es)> (<finding ids>) | confidence: <..> | verdict:
   <holds/uncertain>".
3. "## Cannot verify / open questions" -- the cannot_verify findings, each with what artifact would
   settle it.

Do not invent findings beyond those given. Do not restate this instruction. Output only the memo.

FINDINGS (JSON):
${JSON.stringify(confirmed, null, 2)}`

const memo = await agent(editorPrompt, { label: 'editor', phase: 'Synthesize' })

return {
  counts: { lenses: LENSES.length, raw, refuted, confirmed: confirmed.length },
  confirmed,
  memo,
}
