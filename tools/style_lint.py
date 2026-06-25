"""
Style linter for empirical economics writing.

Checks prose against the rules in research-kit/rules/writing_style.md.
Covers the programmatically checkable subset: AI-tell vocabulary, filler
phrases, throat-clearing, editorializing, naked "this", word-choice
violations, forward references (Shapiro robot-body linearity), passive
voice density, sentence length, stacked adjectives, and more.

Usage:
    python style_lint.py paper.tex
    python style_lint.py paper.md
    python style_lint.py paper.tex --format json
    python style_lint.py paper.tex --severity warning  # only warnings+
    python style_lint.py docs/                          # lint all .tex/.md in dir

Exit code 0 if no errors, 1 if any violations found.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    file: str
    line: int
    rule: str
    severity: str          # "error", "warning", "info"
    message: str
    suggestion: Optional[str] = None
    context: Optional[str] = None   # the offending line (trimmed)


SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2}


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

_TEX_COMMAND = re.compile(
    r"\\(?:begin|end|usepackage|documentclass|label|ref|cite\w*|eqref|"
    r"textbf|textit|emph|footnote|section|subsection|subsubsection|"
    r"caption|includegraphics|input|bibliography\w*|newcommand|renewcommand|"
    r"def|let|setlength|addtolength|hspace|vspace|newline|linebreak|"
    r"clearpage|newpage|maketitle|tableofcontents|appendix|"
    r"centering|raggedright|raggedleft|noindent|par|item|"
    r"toprule|midrule|bottomrule|hline|cline"
    r")\b"
)

_TEX_ENV_SKIP = re.compile(
    r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|"
    r"tikzpicture|lstlisting|verbatim|minted|tabular\*?|"
    r"array|matrix|pmatrix|bmatrix|"
    r"quote|quotation|displayquote)\}"
)

_TEX_COMMENT = re.compile(r"(?<!\\)%.*$", re.MULTILINE)


def _strip_tex_markup(text: str) -> str:
    """Remove LaTeX commands, math, and comments to get prose-like text."""
    # Remove comments
    text = _TEX_COMMENT.sub("", text)
    # Remove display math
    text = re.sub(r"\$\$.*?\$\$", " MATH ", text, flags=re.DOTALL)
    text = re.sub(r"\\\[.*?\\\]", " MATH ", text, flags=re.DOTALL)
    # Remove inline math
    text = re.sub(r"\$[^$]+?\$", " MATH ", text)
    # Remove \command{...} but keep the brace content for text commands
    # (formatting + section/caption titles — these are prose worth linting)
    text = re.sub(
        r"\\(?:textbf|textit|emph|textsc|textrm|"
        r"section|subsection|subsubsection|chapter|paragraph|subparagraph|"
        r"title|caption)\*?\{([^}]*)\}",
        r"\1", text,
    )
    # Remove other commands
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])*(?:\{[^}]*\})*", " ", text)
    # Remove remaining braces
    text = text.replace("{", "").replace("}", "")
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _is_math_env(line: str) -> bool:
    """Check if a line opens a math/code environment we should skip."""
    return bool(_TEX_ENV_SKIP.search(line))


def extract_lines(filepath: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_number, raw_line, prose_line) tuples.

    prose_line has TeX markup stripped (for .tex files) or is the raw
    line (for .md files).  Math environments and code blocks are
    replaced with empty strings so pattern checks skip them.
    """
    text = filepath.read_text(errors="replace")
    raw_lines = text.split("\n")
    is_tex = filepath.suffix == ".tex"
    is_md = filepath.suffix == ".md"

    results = []
    in_skip = False  # inside math/code env

    for i, raw in enumerate(raw_lines, 1):
        # Track math/code environments to skip
        if is_tex:
            if _is_math_env(raw):
                in_skip = True
            if in_skip:
                if re.search(r"\\end\{", raw):
                    in_skip = False
                results.append((i, raw, ""))
                continue
            # Skip lines that are block quotes (start with `` or are inside
            # quote environments — already handled by _TEX_ENV_SKIP above)
            stripped_raw = raw.strip()
            if stripped_raw.startswith("``") and stripped_raw.endswith("''"):
                # Entire line is a quotation — skip
                results.append((i, raw, ""))
                continue
            prose = _strip_tex_markup(raw)
        elif is_md:
            # Skip fenced code blocks
            if raw.strip().startswith("```"):
                in_skip = not in_skip
                results.append((i, raw, ""))
                continue
            if in_skip:
                results.append((i, raw, ""))
                continue
            # Skip YAML frontmatter
            if i == 1 and raw.strip() == "---":
                in_skip = True
                results.append((i, raw, ""))
                continue
            if in_skip and raw.strip() == "---":
                in_skip = False
                results.append((i, raw, ""))
                continue
            # Strip markdown formatting but keep text
            prose = re.sub(r"!\[.*?\]\(.*?\)", "", raw)       # images
            prose = re.sub(r"\[([^\]]*)\]\(.*?\)", r"\1", raw)  # links
            prose = re.sub(r"[*_]{1,3}", "", prose)            # bold/italic
            prose = re.sub(r"`[^`]+`", " CODE ", prose)        # inline code
            prose = re.sub(r"^#+\s*", "", prose)               # headings
        else:
            prose = raw

        results.append((i, raw, prose))

    return results


def _get_paragraphs(lines: list[tuple[int, str, str]]) -> list[list[tuple[int, str]]]:
    """Group prose lines into paragraphs (separated by blank lines).

    Returns list of paragraphs, each a list of (line_number, prose_text).
    """
    paragraphs: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for lineno, _raw, prose in lines:
        stripped = prose.strip()
        if not stripped:
            if current:
                paragraphs.append(current)
                current = []
        else:
            current.append((lineno, stripped))
    if current:
        paragraphs.append(current)
    return paragraphs


# ---------------------------------------------------------------------------
# Sentence splitter (lightweight, no dependencies)
# ---------------------------------------------------------------------------

_SENT_END = re.compile(
    r'(?<=[.!?])'           # after sentence-ending punctuation
    r'(?:\s*["\u201d)]*)'   # optional closing quotes/parens
    r'\s+'                  # whitespace
    r'(?=[A-Z"\u201c(])'    # next sentence starts with cap, quote, or paren
)

# Patterns that look like sentence ends but aren't
_FALSE_ENDS = re.compile(
    r"(?:"
    r"(?:Dr|Mr|Mrs|Ms|Prof|Jr|Sr|St|vs|etc|al|ed|vol|no|pp|Fig|Eq|Sec|Ch)\."
    r"|[A-Z]\."             # initials like "J."
    r"|e\.g\."
    r"|i\.e\."
    r"|\d\."                # numbered lists
    r")"
)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Good enough for linting; not perfect."""
    # Protect false ends
    protected = _FALSE_ENDS.sub(lambda m: m.group().replace(".", "\x00"), text)
    parts = _SENT_END.split(protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Check functions
#
# Each returns a list of Violation objects.  They receive the full
# file context so they can do cross-line analysis where needed.
# ---------------------------------------------------------------------------

def check_ai_tell(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§4: AI-tell vocabulary."""
    WORDS = [
        r"\bdelve(?:s|d)?\s+into\b",
        r"\bnavigate[sd]?\b",
        r"\bunderscore[sd]?\b",
        r"\bmultifaceted\b",
        r"\bparadigm\b",
        r"\bseamless(?:ly)?\b",
        r"\bpivotal\b",
        r"\bintricate(?:ly)?\b",
        r"\bholistic(?:ally)?\b",
        r"\bdynamic landscape\b",
        r"\bin today'?s world\b",
        r"\bit is important to note that\b",
        r"\bit'?s worth mentioning that\b",
    ]
    # "comprehensive", "robust", and "leverage" only when used as filler
    # (not in technical contexts like "robust standard errors" or
    # statistical "high-leverage observation")
    FILLER_ADJ = [
        (r"\bcomprehensive\b", ["comprehensive income", "comprehensive school"]),
        (r"\brobust\b", ["robust standard error", "robust se", "robust variance",
                         "robust inference", "robust optimization", "robust control",
                         "robust to", "robust against"]),
        (r"\bleverage[sd]?\b", ["high-leverage", "low-leverage", "leverage point",
                                "leverage statistic", "leverage diagnostic",
                                "leverage score", "leverage and cell"]),
    ]
    pattern = re.compile("|".join(WORDS), re.IGNORECASE)
    violations = []
    for lineno, _raw, prose in lines:
        if not prose.strip():
            continue
        for m in pattern.finditer(prose):
            violations.append(Violation(
                file=filepath, line=lineno, rule="ai-tell",
                severity="warning",
                message=f"AI-tell vocabulary: \"{m.group()}\"",
                suggestion="Replace with plain alternative (see §4 word table)",
                context=prose.strip()[:120],
            ))
        lower = prose.lower()
        for pat, exceptions in FILLER_ADJ:
            if re.search(pat, lower):
                if not any(exc in lower for exc in exceptions):
                    violations.append(Violation(
                        file=filepath, line=lineno, rule="ai-tell",
                        severity="info",
                        message=f"Possible AI-tell filler adjective (check context): \"{re.search(pat, lower).group()}\"",
                        context=prose.strip()[:120],
                    ))
    return violations


def check_filler_phrases(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§17 quick reference: phrases to delete on final pass."""
    PHRASES = [
        (r"\bit is worth noting that\b", "Cut or rewrite the claim to stand alone"),
        (r"\bit is important to note that\b", "Cut or rewrite"),
        (r"\bin order to\b", "\"to\""),
        (r"\bdue to the fact that\b", "\"because\""),
        (r"\ba wide variety of\b", "\"many\", or name them"),
        (r"\ba vast array of\b", "\"many\", or name them"),
        (r"\barguably\b", "Usually cuttable"),
        (r"\bit could be argued\b", "Cut — either argue it or don't"),
        (r"\bwe leave .{0,60}for future research\b", "Strike entirely"),
    ]
    violations = []
    for lineno, _raw, prose in lines:
        lower = prose.lower()
        for pat, fix in PHRASES:
            if re.search(pat, lower):
                violations.append(Violation(
                    file=filepath, line=lineno, rule="filler-phrase",
                    severity="warning",
                    message=f"Filler phrase: \"{re.search(pat, lower).group()}\"",
                    suggestion=fix,
                    context=prose.strip()[:120],
                ))
    return violations


def check_throat_clearing(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§2: Aspirational/hedging meta-talk."""
    PATTERNS = [
        (r"\bthis paper aims to\b", "Just state what the paper does"),
        (r"\bthis study seeks to\b", "Just state what the study does"),
        (r"\bwe attempt to\b", "\"We\" + direct verb"),
        (r"\bthe contribution of this paper is to\b", "Just make the contribution"),
        (r"\bin this study,? we will discuss\b", "Cut — just discuss"),
        (r"\bthis paper contributes by\b", "Rephrase: \"We show/find/develop...\""),
        (r"\bwe aim to\b", "\"We\" + direct verb"),
        (r"\bwe seek to\b", "\"We\" + direct verb"),
    ]
    violations = []
    for lineno, _raw, prose in lines:
        lower = prose.lower()
        for pat, fix in PATTERNS:
            if re.search(pat, lower):
                violations.append(Violation(
                    file=filepath, line=lineno, rule="throat-clearing",
                    severity="warning",
                    message=f"Throat-clearing: \"{re.search(pat, lower).group()}\"",
                    suggestion=fix,
                    context=prose.strip()[:120],
                ))
    return violations


def check_editorializing(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§2: Don't editorialize the data."""
    WORDS = [
        r"\bstarkest\b",
        r"\bmost compelling\b",
        r"\bremarkable\b",
        r"\bremarkably\b",
        r"\bstriking(?:ly)?\b",
        r"\bnotable\b",
        r"\bnotably\b",
    ]
    pattern = re.compile("|".join(WORDS), re.IGNORECASE)
    violations = []
    for lineno, _raw, prose in lines:
        for m in pattern.finditer(prose):
            violations.append(Violation(
                file=filepath, line=lineno, rule="editorializing",
                severity="warning",
                message=f"Editorializing adjective: \"{m.group()}\"",
                suggestion="State the finding and cite the number; let the reader judge",
                context=prose.strip()[:120],
            ))
    return violations


def check_naked_this(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§4: Clothe the naked 'this'."""
    # "This shows/implies/suggests/means/indicates/demonstrates/highlights/reveals"
    pattern = re.compile(
        r"\bThis\s+(?:shows?|implies?|suggests?|means?|indicates?|"
        r"demonstrates?|highlights?|reveals?|confirms?|proves?|"
        r"illustrates?|establishes?)\b"
    )
    violations = []
    for lineno, _raw, prose in lines:
        for m in pattern.finditer(prose):
            violations.append(Violation(
                file=filepath, line=lineno, rule="naked-this",
                severity="warning",
                message=f"Naked \"this\": \"{m.group()}\"",
                suggestion="Name what \"this\" refers to: \"This result shows...\", \"This pattern implies...\"",
                context=prose.strip()[:120],
            ))
    return violations


def check_word_choice(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§4: Prefer plain words."""
    # (pattern, plain alternative, notes)
    TABLE = [
        (r"\bdemonstrate[sd]?\b", "show/find", None),
        (r"\buncover(?:s|ed)?\b", "find", None),
        (r"\breveal(?:s|ed)?\b", "show/find", None),
        (r"\billustrate[sd]?\b", "show", None),
        (r"\butilize[sd]?\b", "use", None),
        (r"\bemploy(?:s|ed)?\b", "use", ["employ(?:ee|er|ment)"]),
        (r"\binvestigate[sd]?\b", "study", None),
        (r"\bexamine[sd]?\b", "study", None),
        (r"\bexplore[sd]?\b", "study", None),
        (r"\binterrogate[sd]?\b", "test", None),
        (r"\bprobe[sd]?\b", "test", None),
        (r"\bimpact(?:s|ed|ing)?\b", "affect/change", ["impact assessment", "impact evaluation",
                                                         "impact factor"]),
        (r"\bfacilitate[sd]?\b", "help", None),
        (r"\benable[sd]?\b", "let", None),
        (r"\badditionally\b", "also", None),
        (r"\bmoreover\b", "also (or cut)", None),
        (r"\bnumerous\b", "many", None),
        (r"\bmultitude\b", "many", None),
        (r"\bfrequently\b", "often", None),
        (r"\bwith respect to\b", "about", None),
        (r"\bconcerning\b", "about", None),
    ]
    violations = []
    for lineno, _raw, prose in lines:
        if not prose.strip():
            continue
        lower = prose.lower()
        for pat, alt, exceptions in TABLE:
            m = re.search(pat, lower)
            if m:
                if exceptions and any(re.search(exc, lower) for exc in exceptions):
                    continue
                violations.append(Violation(
                    file=filepath, line=lineno, rule="word-choice",
                    severity="info",
                    message=f"Prefer \"{alt}\" over \"{m.group()}\"",
                    suggestion=f"See §4 word table: {m.group()} → {alt}",
                    context=prose.strip()[:120],
                ))
    return violations


def check_self_categorizing(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§13: No self-categorizing prefaces."""
    PATTERNS = [
        r"\bthis is a descriptive paper\b",
        r"\bthis study is theoretical\b",
        r"\bin this paper,? we provide (?:a|an) (?:comprehensive )?overview\b",
        r"\bthis paper provides (?:a|an) (?:comprehensive )?overview\b",
    ]
    pattern = re.compile("|".join(PATTERNS), re.IGNORECASE)
    violations = []
    for lineno, _raw, prose in lines:
        m = pattern.search(prose)
        if m:
            violations.append(Violation(
                file=filepath, line=lineno, rule="self-categorizing",
                severity="warning",
                message=f"Self-categorizing preface: \"{m.group()}\"",
                suggestion="Drop — the reader can tell from the content",
                context=prose.strip()[:120],
            ))
    return violations


def check_forward_references(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§16 robot body: Be linear — no forward references."""
    PATTERNS = [
        (r"\bas we (?:will|shall) (?:show|see|discuss|demonstrate|argue|explain)\b",
         "State the claim now or restructure so forward reference is unnecessary"),
        (r"\bas (?:discussed|shown|described|explained|detailed) below\b",
         "Present the material here instead of pointing ahead"),
        (r"\bwe (?:will )?return to this (?:point |issue |question )?in\b",
         "Present the material where it's needed"),
        (r"\bwe (?:will )?defer (?:this|the)\b",
         "Present it now or cut"),
        (r"\bwe postpone\b",
         "Present it now or cut"),
        (r"\bwe (?:will )?come back to\b",
         "Present it now"),
        (r"\b(?:this|the) (?:point|issue|question) is (?:taken up|addressed|discussed) (?:later|below|in Section)\b",
         "Address it here"),
    ]
    violations = []
    for lineno, _raw, prose in lines:
        lower = prose.lower()
        for pat, fix in PATTERNS:
            m = re.search(pat, lower)
            if m:
                violations.append(Violation(
                    file=filepath, line=lineno, rule="forward-reference",
                    severity="warning",
                    message=f"Forward reference (robot-body linearity): \"{m.group()}\"",
                    suggestion=fix,
                    context=prose.strip()[:120],
                ))
    return violations


def check_hedging_openers(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§7: Don't open sentences/paragraphs with weak hedges."""
    PATTERNS = [
        r"^It is possible that\b",
        r"^Perhaps\b",
        r"^It could be argued that\b",
        r"^One might argue that\b",
        r"^It may be the case that\b",
    ]
    pattern = re.compile("|".join(PATTERNS), re.IGNORECASE)
    violations = []
    for lineno, _raw, prose in lines:
        stripped = prose.strip()
        if pattern.match(stripped):
            violations.append(Violation(
                file=filepath, line=lineno, rule="hedging-opener",
                severity="info",
                message=f"Weak hedging opener",
                suggestion="Show it's possible with evidence, or cut",
                context=stripped[:120],
            ))
    return violations


def check_sentence_length(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§3: Flag sentences over 40 words or with 3+ subordinate clauses."""
    MAX_WORDS = 45
    MAX_COMMAS = 3  # proxy for clause count
    violations = []
    for lineno, _raw, prose in lines:
        stripped = prose.strip()
        if not stripped:
            continue
        sentences = split_sentences(stripped)
        for sent in sentences:
            words = sent.split()
            n_commas = sent.count(",")
            if len(words) > MAX_WORDS:
                violations.append(Violation(
                    file=filepath, line=lineno, rule="sentence-length",
                    severity="info",
                    message=f"Long sentence ({len(words)} words, max ~{MAX_WORDS})",
                    suggestion="Consider splitting into two sentences",
                    context=sent[:120],
                ))
            elif n_commas >= MAX_COMMAS and len(words) > 25:
                violations.append(Violation(
                    file=filepath, line=lineno, rule="clause-stacking",
                    severity="info",
                    message=f"Possible clause stacking ({n_commas} commas, {len(words)} words)",
                    suggestion="Check if subordinate clauses can be split out",
                    context=sent[:120],
                ))
    return violations


def check_passive_voice(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§2: Flag high passive-voice density (aggregate check)."""
    # Rough heuristic: "is/are/was/were/been/being + past participle"
    passive_pat = re.compile(
        r"\b(?:is|are|was|were|been|being)\s+(?:\w+ly\s+)?(\w+ed|shown|found|given|taken|"
        r"seen|known|made|done|built|run|set|put|held|told|sold|bought|thought|brought|"
        r"taught|caught|sought|written|driven|chosen|spoken|broken|frozen|stolen|"
        r"forgotten|hidden|risen|fallen|grown|drawn|thrown|blown|worn|torn|borne)\b",
        re.IGNORECASE,
    )
    total_sentences = 0
    passive_sentences = 0
    passive_lines: list[tuple[int, str]] = []

    for lineno, _raw, prose in lines:
        stripped = prose.strip()
        if not stripped:
            continue
        sentences = split_sentences(stripped)
        for sent in sentences:
            total_sentences += 1
            if passive_pat.search(sent):
                passive_sentences += 1
                passive_lines.append((lineno, sent[:100]))

    violations = []
    if total_sentences >= 10:
        ratio = passive_sentences / total_sentences
        if ratio > 0.35:
            violations.append(Violation(
                file=filepath, line=0, rule="passive-density",
                severity="warning",
                message=f"High passive voice density: {passive_sentences}/{total_sentences} "
                        f"sentences ({ratio:.0%})",
                suggestion="Prefer active voice (§2); rewrite the worst offenders",
            ))
        elif ratio > 0.25:
            violations.append(Violation(
                file=filepath, line=0, rule="passive-density",
                severity="info",
                message=f"Moderate passive voice density: {passive_sentences}/{total_sentences} "
                        f"sentences ({ratio:.0%})",
                suggestion="Review passives — is the actor genuinely irrelevant in each?",
            ))
    return violations


def check_connective_openers(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§9: Don't open too many paragraphs with connectives."""
    paragraphs = _get_paragraphs(lines)
    CONNECTIVES = re.compile(
        r"^(?:Furthermore|Moreover|Additionally|However|Thus|Therefore|"
        r"Consequently|In contrast|Importantly|Note that|In addition|"
        r"Indeed|Nonetheless|Nevertheless)\b",
        re.IGNORECASE,
    )
    openers = []
    for para in paragraphs:
        if not para:
            continue
        first_line = para[0][1]
        if CONNECTIVES.match(first_line):
            openers.append(para[0])

    if len(paragraphs) >= 4:
        ratio = len(openers) / len(paragraphs)
        if ratio > 0.3:
            violations = [Violation(
                file=filepath, line=0, rule="connective-opener",
                severity="info",
                message=f"{len(openers)}/{len(paragraphs)} paragraphs open with connectives ({ratio:.0%})",
                suggestion="Vary paragraph openings; don't start every paragraph with a connective (§9)",
            )]
            return violations
    return []


def check_stacked_adjectives(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§4: No stacked adjectives (3+ comma-separated adjectives before a noun)."""
    # Heuristic: "adj, adj, adj noun" or "adj, adj, and adj noun"
    pattern = re.compile(
        r"\b(\w+),\s+(\w+),\s+(?:and\s+)?(\w+)\s+(?:analysis|design|approach|method|"
        r"framework|model|estimate|result|finding|study|paper|dataset|sample|"
        r"strategy|specification|test|evidence|effect|impact|pattern|"
        r"structure|system|process|mechanism)\b",
        re.IGNORECASE,
    )
    violations = []
    for lineno, _raw, prose in lines:
        m = pattern.search(prose)
        if m:
            violations.append(Violation(
                file=filepath, line=lineno, rule="stacked-adjectives",
                severity="info",
                message=f"Possible stacked adjectives: \"{m.group()}\"",
                suggestion="Pick one adjective (§4)",
                context=prose.strip()[:120],
            ))
    return violations


def check_synonym_piling(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§17: Synonym piling — e.g. 'examine, investigate, and explore'."""
    # Known synonym clusters
    CLUSTERS = [
        [r"examine", r"investigate", r"explore", r"study", r"analyze"],
        [r"comprehensive", r"in-depth", r"rigorous", r"thorough", r"detailed"],
        [r"show", r"demonstrate", r"illustrate", r"reveal"],
    ]
    violations = []
    for lineno, _raw, prose in lines:
        lower = prose.lower()
        for cluster in CLUSTERS:
            found = [w for w in cluster if re.search(r"\b" + w + r"\b", lower)]
            if len(found) >= 3:
                violations.append(Violation(
                    file=filepath, line=lineno, rule="synonym-piling",
                    severity="warning",
                    message=f"Synonym piling: {', '.join(found)}",
                    suggestion="Pick one verb/adjective",
                    context=prose.strip()[:120],
                ))
    return violations


def check_non_statistical_significantly(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§17: 'Significantly' used non-statistically."""
    violations = []
    for lineno, _raw, prose in lines:
        lower = prose.lower()
        if "significantly" not in lower:
            continue
        # If nearby words suggest statistical context, skip
        stat_context = any(w in lower for w in [
            "statistically", "p-value", "p value", "standard error",
            "coefficient", "percent", "confidence", "t-stat", "z-stat",
            "significant at", "insignificant",
        ])
        if not stat_context:
            violations.append(Violation(
                file=filepath, line=lineno, rule="non-stat-significantly",
                severity="info",
                message="\"Significantly\" may be non-statistical here",
                suggestion="Cut, or replace with a number (§17)",
                context=prose.strip()[:120],
            ))
    return violations


def check_decimal_precision(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§10: Flag numbers with >3 decimal places (outside math environments)."""
    pattern = re.compile(r"\b\d+\.\d{4,}\b")
    # Case/docket numbers: digit sequences with dots and dashes (e.g. 0025538-98.2013.4.01.3900)
    docket_pattern = re.compile(r"\d{5,}-[\d.]+")
    violations = []
    for lineno, _raw, prose in lines:
        # Skip lines that look like case/docket number tables
        if docket_pattern.search(prose):
            continue
        for m in pattern.finditer(prose):
            # Skip if it looks like a p-value specification (0.001, 0.0001)
            val = m.group()
            if val in ("0.0001", "0.00001"):  # conventional p-value thresholds
                continue
            # Skip year-like patterns (e.g. 2013.4012 from concatenated IDs)
            if re.match(r"(?:19|20)\d{2}\.", val):
                continue
            violations.append(Violation(
                file=filepath, line=lineno, rule="decimal-precision",
                severity="info",
                message=f"Excessive decimal precision: {val}",
                suggestion="2–3 significant digits are plenty for most econ applications (§10)",
                context=prose.strip()[:120],
            ))
    return violations


def check_abstract_first_sentence(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§13: The first sentence of the abstract should state the question."""
    # Try to find the abstract
    in_abstract = False
    abstract_text = ""

    for lineno, raw, prose in lines:
        lower_raw = raw.lower().strip()
        if "\\begin{abstract}" in lower_raw or lower_raw == "## abstract" or lower_raw == "# abstract":
            in_abstract = True
            continue
        if in_abstract:
            if "\\end{abstract}" in raw.lower() or (raw.startswith("#") and "abstract" not in raw.lower()):
                break
            if prose.strip():
                abstract_text += " " + prose.strip()

    if not abstract_text.strip():
        return []

    first_sent = split_sentences(abstract_text.strip())
    if not first_sent:
        return []

    sent = first_sent[0].strip()
    violations = []

    # Check for bad openings
    bad_openers = [
        (r"^(?:A |The )?(?:large|growing|extensive|rich|vast) (?:body of )?literature\b",
         "Don't open with the literature gap"),
        (r"^We (?:construct|develop|propose|build|introduce|present|design)\b",
         "Don't open with the contribution — state the question first"),
        (r"^This (?:paper|study|article) (?:constructs|develops|proposes|presents)\b",
         "Don't open with the contribution — state the question first"),
    ]
    for pat, msg in bad_openers:
        if re.search(pat, sent, re.IGNORECASE):
            # Find the line number of the abstract
            for lineno, raw, prose in lines:
                if prose.strip() and prose.strip() in abstract_text:
                    break
            violations.append(Violation(
                file=filepath, line=lineno, rule="abstract-opening",
                severity="error",
                message=msg,
                suggestion="The first sentence of the abstract states the question (§13)",
                context=sent[:120],
            ))
            break

    return violations


def check_cute_quotation(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§14: Don't open with a cute quotation / epigraph."""
    # Look for epigraph environments or quotation marks in the first ~20
    # non-empty prose lines
    violations = []
    prose_count = 0
    for lineno, raw, prose in lines:
        if not prose.strip():
            continue
        prose_count += 1
        if prose_count > 20:
            break
        if re.search(r"\\begin\{epigraph\}", raw, re.IGNORECASE):
            violations.append(Violation(
                file=filepath, line=lineno, rule="cute-quotation",
                severity="warning",
                message="Opening epigraph",
                suggestion="Don't open with a cute quotation (§14)",
                context=raw.strip()[:120],
            ))
    return violations


def check_greek_in_prose(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """Workspace overlay: don't refer to coefficients by Greek letter in prose.

    Catches inline math that's just a Greek letter used as a noun
    (`$\\beta$`, `$\\beta_c$`, `$\\hat\\beta$`) and bare Greek unicode in
    prose. Severity is `info` because legitimate equation references on
    a prose line will also match.
    """
    GREEK_CMDS = (r"\\(?:alpha|beta|gamma|delta|epsilon|zeta|eta|theta|"
                  r"iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|phi|chi|psi|omega)")
    GREEK_UNICODE = r"[α-ωΑ-Ω]"
    inline_greek_only = re.compile(
        r"\$\s*(?:\\hat\s*)?" + GREEK_CMDS +
        r"(?:_(?:\{[^}]+\}|[a-zA-Z0-9]))?\s*\$"
    )
    bare_greek = re.compile(GREEK_UNICODE)
    violations = []
    for lineno, raw, prose in lines:
        if not prose.strip():
            continue  # math env / comment / blank
        if inline_greek_only.search(raw):
            violations.append(Violation(
                file=filepath, line=lineno, rule="greek-in-prose",
                severity="info",
                message="Greek letter used as a coefficient name in prose",
                suggestion="Describe what the number measures (e.g., 'within-firm bias') "
                           "instead of naming it by Greek letter",
                context=raw.strip()[:120],
            ))
            continue
        m = bare_greek.search(raw)
        if m:
            violations.append(Violation(
                file=filepath, line=lineno, rule="greek-in-prose",
                severity="info",
                message=f"Greek letter in prose: \"{m.group()}\"",
                suggestion="Replace with plain-English description of the quantity",
                context=raw.strip()[:120],
            ))
    return violations


def _is_inside_parens(text: str, pos: int) -> bool:
    """True if `pos` falls inside an unclosed `(` on the same line."""
    return text[:pos].count("(") > text[:pos].count(")")


_ITALICS_TEMPLATE = r"\\(?:emph|textit|textsl)\*?\{{[^}}]*{token}[^}}]*\}}"


def _is_inside_italics(raw: str, token: str) -> bool:
    """True if `token` appears inside `\\emph{{...}}` / `\\textit{{...}}` on `raw`."""
    pat = re.compile(_ITALICS_TEMPLATE.format(token=re.escape(token)), re.IGNORECASE)
    return bool(pat.search(raw))


def check_foreign_language(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§6: foreign-language terms outside paren-gloss / italics.

    Catches Portuguese tokens (and tokens carrying Portuguese diacritics)
    used in body prose. The rule allows: gloss-on-first-use (`comarca
    (judicial district)`), italicized first-use (`\\emph{comarca}`), and
    a small carve-out list for institutional roles with no English
    equivalent (`relator`). Hybrid compounds (`comarca-level`,
    `câmara level`) are always wrong and flagged at warning severity.
    """
    # Trimmed to high-signal institutional Portuguese terms that are
    # rarely proper-noun parts or citation titles. Project-specific
    # bans (e.g., `plano amostral`, `pesquisa eleitoral` as a sub-genre
    # term) belong in the workspace overlay banned-phrases table.
    PT_TOKENS = re.compile(
        r"(?<![A-Za-zÀ-ÿ\\])"
        r"(comarcas?|câmaras?|varas?|"
        r"munic[ií]pios?|"
        r"prefeit(?:o|ura)s?|vereadores?|"
        r"sentenças?|improbidade|intimaç(?:ão|ões)|"
        r"desembargadores?)"
        r"(?![A-Za-zÀ-ÿ])",
        re.IGNORECASE,
    )
    WHITELIST = {"relator", "relatores"}  # §6 carve-out: no clean English equivalent
    HYBRID = re.compile(
        r"\b(comarca|câmara|vara|município|cartório|cidade)[- ]levels?\b",
        re.IGNORECASE,
    )
    violations = []
    for lineno, raw, prose in lines:
        if not prose.strip():
            continue
        for m in HYBRID.finditer(prose):
            violations.append(Violation(
                file=filepath, line=lineno, rule="foreign-language",
                severity="warning",
                message=f"Foreign-language hybrid: \"{m.group()}\"",
                suggestion="Use English equivalent: \"district level\", \"courtroom level\", etc. (§6)",
                context=prose.strip()[:120],
            ))
        for m in PT_TOKENS.finditer(prose):
            token = m.group()
            if token.lower() in WHITELIST:
                continue
            if _is_inside_parens(prose, m.start()):
                continue
            if _is_inside_italics(raw, token):
                continue
            violations.append(Violation(
                file=filepath, line=lineno, rule="foreign-language",
                severity="info",
                message=f"Foreign-language term outside paren-gloss: \"{token}\"",
                suggestion="Gloss in parens on first use, English thereafter (§6)",
                context=prose.strip()[:120],
            ))
    return violations


def check_participle_tail(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§4: present-participle tail clauses (AI-cadence)."""
    pattern = re.compile(
        r",\s+(providing|ensuring|reflecting|emphasizing|highlighting|"
        r"showcasing|fostering|underscoring|contributing to|reinforcing|"
        r"signaling|demonstrating|illustrating)\b[^.!?]{0,120}[.!?]",
        re.IGNORECASE,
    )
    violations = []
    for lineno, _raw, prose in lines:
        for m in pattern.finditer(prose):
            violations.append(Violation(
                file=filepath, line=lineno, rule="participle-tail",
                severity="warning",
                message=f"Present-participle tail clause: \"{m.group()[:50].rstrip()}…\"",
                suggestion="Replace with a separate sentence or cut — the substance usually survives (§4)",
                context=prose.strip()[:120],
            ))
    return violations


def check_illustrative(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """Quick-ref: \"illustrative test/work\" — do real empirical work or none."""
    pattern = re.compile(
        r"\billustrative\s+(empirical work|test|exercise|analysis|evidence)\b",
        re.IGNORECASE,
    )
    violations = []
    for lineno, _raw, prose in lines:
        for m in pattern.finditer(prose):
            violations.append(Violation(
                file=filepath, line=lineno, rule="illustrative",
                severity="warning",
                message=f"\"{m.group()}\" — do real empirical work or none (Cochrane)",
                suggestion="Drop \"illustrative\" or rewrite to claim what the work actually does",
                context=prose.strip()[:120],
            ))
    return violations


def check_em_dash_density(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§11: at most one em-dash per paragraph."""
    paragraphs = _get_paragraphs(lines)
    violations = []
    for para in paragraphs:
        first_lineno = para[0][0]
        total = sum(text.count("---") for _lineno, text in para)
        # Also count unicode em-dashes that survived markup strip
        total += sum(text.count("—") for _lineno, text in para)
        if total >= 2:
            violations.append(Violation(
                file=filepath, line=first_lineno, rule="em-dash-density",
                severity="info",
                message=f"{total} em-dashes in this paragraph (max 1)",
                suggestion="Reserve em-dash for the genuinely parenthetical case; use comma or colon where they work (§11)",
                context=para[0][1][:120],
            ))
    return violations


def check_math_in_prose(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§11: don't use math symbols (×, ÷, ≤, ≥, ⊆, ∈, …) in narrative prose."""
    pattern = re.compile(r"[×÷≤≥⊆⊇⊂⊃∈∉∪∩∧∨≠≈±]")
    violations = []
    for lineno, _raw, prose in lines:
        if not prose.strip():
            continue
        m = pattern.search(prose)
        if m:
            violations.append(Violation(
                file=filepath, line=lineno, rule="math-in-prose",
                severity="info",
                message=f"Math symbol in prose: \"{m.group()}\"",
                suggestion="Spell out: × → \"by\" / \"-by-\"; ≥ → \"at least\"; ⊆ → \"a subset of\" (§11)",
                context=prose.strip()[:120],
            ))
    return violations


def check_pseudocode_inline(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§4: don't paste pseudocode parentheticals like `(matched share = 1)`."""
    # Matches `(identifier = 0/1)` and `(identifier == "...")` in prose.
    pattern = re.compile(
        r"\(\s*[a-z_][a-z0-9_ \-]{0,40}\s*(?:==?|!=)\s*"
        r"(?:[01]|\".{0,40}\"|'.{0,40}')\s*\)"
    )
    violations = []
    for lineno, _raw, prose in lines:
        for m in pattern.finditer(prose):
            violations.append(Violation(
                file=filepath, line=lineno, rule="pseudocode-inline",
                severity="warning",
                message=f"Inline pseudocode: \"{m.group()}\"",
                suggestion="State the condition in words: \"polls where every candidate matched\", \"the treated cohort\" (§4)",
                context=prose.strip()[:120],
            ))
    return violations


def check_coding_vocab(filepath: str, lines: list[tuple[int, str, str]]) -> list[Violation]:
    """§4: data-engineering vocabulary in published prose."""
    PATTERNS = [
        (r"\bwithin-cell\b", "name the comparison directly (e.g., \"within race × week\")"),
        (r"\bcell-level\b", "name the level of observation"),
        (r"\bsame cell\b", "name the cell explicitly (\"same race-week\")"),
        (r"\bpanel grid\b", "describe the panel layout in words"),
        (r"\bgrain\b(?! of (?:salt|truth|sand|rice|sugar|wheat))",
         "name the level of observation (\"one row per …\")"),
        (r"\bbucket(?:s|ed|ing)?\b", "name the group or bin"),
        (r"\b(?:left|inner|outer|cross)\s+join\b", "\"link\" or \"merge\""),
        (r"\bjoin key\b", "\"matching variable\""),
        (r"\bassemble layer\b", "describe what the layer does"),
        (r"\bintermediate layer\b", "describe what the layer does"),
    ]
    violations = []
    for lineno, _raw, prose in lines:
        lower = prose.lower()
        for pat, fix in PATTERNS:
            for m in re.finditer(pat, lower):
                violations.append(Violation(
                    file=filepath, line=lineno, rule="coding-vocab",
                    severity="warning",
                    message=f"Pipeline vocabulary in prose: \"{m.group()}\"",
                    suggestion=fix + " (§4)",
                    context=prose.strip()[:120],
                ))
    return violations


# ---------------------------------------------------------------------------
# Workspace overlay: banned-phrases table
# ---------------------------------------------------------------------------

def _find_overlay(start: Path) -> Optional[Path]:
    """Walk up from `start` looking for research/rules/writing_style.md."""
    cur = start.resolve()
    cur = cur.parent if cur.is_file() else cur
    while cur != cur.parent:
        candidate = cur / "research" / "rules" / "writing_style.md"
        if candidate.is_file():
            return candidate
        cur = cur.parent
    return None


_PAREN_RE = re.compile(r"\(([^)]*)\)")


def _extract_banned_phrases_from_cell(cell: str) -> list[str]:
    """Pull banned-phrase backticks out of a "Don't write" cell.

    Top-level backticks (outside parens) are always banned. Backticks
    inside `(incl. ...)` or `(and ...)` parens are also banned — those
    are variants of the headline phrase. Backticks inside other parens
    (`(as a noun ...)`, `(in poll context)`, `(meaning a .csv ...)`) are
    explanatory and dropped, so things like `.csv` / `.parquet` don't
    get treated as bans on their own.
    """
    phrases = list(re.findall(r"`([^`]+)`", _PAREN_RE.sub("", cell)))
    for m in _PAREN_RE.finditer(cell):
        inner = m.group(1).strip().lower()
        if inner.startswith(("incl", "and ")):
            phrases.extend(re.findall(r"`([^`]+)`", m.group(1)))
    return phrases


def _parse_banned_phrases(overlay_path: Path) -> list[tuple[re.Pattern, str, str]]:
    """Parse the banned-phrases markdown table from a workspace overlay.

    Returns list of (compiled_pattern, plain_phrase, suggestion).
    Entries that are too context-dependent for mechanical matching
    (e.g. the bare word `file`) are skipped entirely.
    """
    SKIP = {"file"}
    text = overlay_path.read_text(errors="replace")
    m = re.search(r"##\s+Banned phrases\b(.*?)(?=\n##\s|\Z)", text, re.DOTALL)
    if not m:
        return []
    section = m.group(1)
    rows: list[tuple[re.Pattern, str, str]] = []
    for line in section.split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("|--") or line.startswith("| Don't write"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        dont_cell, use_cell = cells[0], cells[1]
        phrases = _extract_banned_phrases_from_cell(dont_cell)
        suggestion = re.sub(r"`([^`]+)`", r"\1", use_cell)
        for phrase in phrases:
            if phrase.strip().lower() in SKIP:
                continue
            esc = re.escape(phrase)
            left = r"(?<!\w)" if phrase[0].isalnum() else ""
            right = r"(?!\w)" if phrase[-1].isalnum() else ""
            try:
                pat = re.compile(left + esc + right, re.IGNORECASE)
            except re.error:
                continue
            rows.append((pat, phrase, suggestion))
    return rows


def check_banned_phrases(filepath: str, lines: list[tuple[int, str, str]],
                         banned: list[tuple[re.Pattern, str, str]]) -> list[Violation]:
    """Workspace overlay: banned phrases. All emit at warning severity."""
    if not banned:
        return []
    violations = []
    for lineno, _raw, prose in lines:
        if not prose.strip():
            continue
        for pat, phrase, suggestion in banned:
            m = pat.search(prose)
            if m:
                violations.append(Violation(
                    file=filepath, line=lineno, rule="banned-phrase",
                    severity="warning",
                    message=f"Banned phrase: \"{m.group()}\"",
                    suggestion=f"Use instead: {suggestion}",
                    context=prose.strip()[:120],
                ))
    return violations


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    check_ai_tell,
    check_filler_phrases,
    check_throat_clearing,
    check_editorializing,
    check_naked_this,
    check_word_choice,
    check_self_categorizing,
    check_forward_references,
    check_hedging_openers,
    check_sentence_length,
    check_passive_voice,
    check_connective_openers,
    check_stacked_adjectives,
    check_synonym_piling,
    check_non_statistical_significantly,
    check_decimal_precision,
    check_abstract_first_sentence,
    check_cute_quotation,
    check_greek_in_prose,
    check_foreign_language,
    check_participle_tail,
    check_illustrative,
    check_em_dash_density,
    check_math_in_prose,
    check_pseudocode_inline,
    check_coding_vocab,
]


def lint_file(filepath: Path, overlay_phrases=None) -> list[Violation]:
    """Run all checks on a single file."""
    lines = extract_lines(filepath)
    violations = []
    for check in ALL_CHECKS:
        violations.extend(check(str(filepath), lines))
    if overlay_phrases:
        violations.extend(check_banned_phrases(str(filepath), lines, overlay_phrases))
    violations.sort(key=lambda v: (v.line, SEVERITY_RANK.get(v.severity, 0)))
    return violations


def format_text(violations: list[Violation]) -> str:
    """Human-readable output."""
    if not violations:
        return "No style violations found."

    out = []
    current_file = None
    for v in violations:
        if v.file != current_file:
            current_file = v.file
            out.append(f"\n{'='*60}")
            out.append(f"  {current_file}")
            out.append(f"{'='*60}")
        loc = f"L{v.line}" if v.line else "file"
        sev = v.severity.upper()
        out.append(f"  {loc:>6}  [{sev:7}]  {v.rule}")
        out.append(f"          {v.message}")
        if v.suggestion:
            out.append(f"          → {v.suggestion}")
        if v.context:
            out.append(f"          | {v.context}")
        out.append("")

    # Summary
    by_sev = {}
    for v in violations:
        by_sev[v.severity] = by_sev.get(v.severity, 0) + 1
    summary = ", ".join(f"{count} {sev}" for sev, count in
                        sorted(by_sev.items(), key=lambda x: SEVERITY_RANK.get(x[0], 0), reverse=True))
    out.append(f"  Total: {len(violations)} violations ({summary})")
    return "\n".join(out)


def format_json(violations: list[Violation]) -> str:
    return json.dumps([asdict(v) for v in violations], indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Style linter for empirical economics writing",
        epilog="Rules: research-kit/rules/writing_style.md",
    )
    parser.add_argument("path", nargs="+",
                        help="Files or directories to lint (.tex, .md)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--severity", choices=["info", "warning", "error"],
                        default="info",
                        help="Minimum severity to report (default: info)")
    parser.add_argument("--rule", action="append", default=None,
                        help="Only check these rules (repeatable)")
    parser.add_argument("--overlay", default=None,
                        help="Path to a workspace overlay (research/rules/writing_style.md) "
                             "whose banned-phrases table will be enforced. If omitted, "
                             "auto-detected by walking up from the first linted file.")
    parser.add_argument("--no-overlay", action="store_true",
                        help="Disable workspace overlay auto-detection.")
    args = parser.parse_args()

    min_rank = SEVERITY_RANK[args.severity]

    # Collect files
    files: list[Path] = []
    for p in args.path:
        path = Path(p)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.tex")))
            files.extend(sorted(path.rglob("*.md")))
        elif path.is_file():
            files.append(path)
        else:
            print(f"Warning: {p} not found, skipping", file=sys.stderr)

    if not files:
        print("No files to lint.", file=sys.stderr)
        sys.exit(0)

    # Resolve workspace overlay (banned-phrases table)
    overlay_phrases: list = []
    if not args.no_overlay:
        overlay_path: Optional[Path] = None
        if args.overlay:
            overlay_path = Path(args.overlay)
            if not overlay_path.is_file():
                print(f"Warning: overlay {args.overlay} not found, skipping",
                      file=sys.stderr)
                overlay_path = None
        else:
            overlay_path = _find_overlay(files[0])
        if overlay_path:
            overlay_phrases = _parse_banned_phrases(overlay_path)

    all_violations: list[Violation] = []
    for f in files:
        vs = lint_file(f, overlay_phrases=overlay_phrases)
        # Filter by severity
        vs = [v for v in vs if SEVERITY_RANK.get(v.severity, 0) >= min_rank]
        # Filter by rule
        if args.rule:
            vs = [v for v in vs if v.rule in args.rule]
        all_violations.extend(vs)

    if args.format == "json":
        print(format_json(all_violations))
    else:
        print(format_text(all_violations))

    sys.exit(1 if all_violations else 0)


if __name__ == "__main__":
    main()
