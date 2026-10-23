"""Bounded technical-answer checks; never executes or compiles generated code."""
import ast
import os
import re

_BLOCK = re.compile(r"(?ms)^\s*(`{3,}|~{3,})([\w+#.-]*)[^\n]*\n(.*?)^\s*\1\s*$")
_DETAIL = re.compile(r"\b(?:advanced|pitfalls?|syntax|programming|coding|api|sdk)\b", re.I)
_EXAMPLES = re.compile(r"\b(?:examples?|code|syntax)\b", re.I)
# This strips Java literals/comments for a narrow grammar check, not a compiler.
_JAVA_LITERAL = re.compile(r'""".*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/', re.S)


def automatic_verification():
    mode = os.getenv("AI_TECHNICAL_VERIFICATION", "auto").strip().lower()
    if mode not in {"auto", "off"}:
        raise ValueError("AI_TECHNICAL_VERIFICATION must be auto or off.")
    return mode == "auto"


def needs_reference_review(question, content=None):
    """Use request detail or generated explanatory code, never topic answers.

    Pure lists and code-only artifacts do not gain unwanted prose/citations.
    Source-sensitive and private tasks retain their existing evidence policies;
    the caller enables this only for public general-learning requests.
    """
    if not automatic_verification():
        return False
    if content is None:
        return bool(_DETAIL.search(question) and _EXAMPLES.search(question))
    return bool(_BLOCK.search(content) and _BLOCK.sub("", content).strip())


def syntax_issue(content):
    """Report only definite narrow syntax defects; this is not execution proof."""
    prose = _BLOCK.sub("", content)
    if re.search(r"(?m)^\s*\|[^\n]*```[\w+#.-]+", prose):
        return "A fenced code example is embedded inside a Markdown table. Move code into separate properly fenced blocks, outside the table, with actual line breaks."
    all_complete=bool(re.search(r"all\s+(?:the\s+)?(?:code\s+)?(?:snippets|examples|blocks)\s+(?:are|below are)\s+(?:self[-\u2010-\u2015 ]contained|complete|standalone)",prose,re.I))
    for match in _BLOCK.finditer(content):
        language, code = match.group(2).lower(), match.group(3)
        if all_complete and language=="java" and not re.search(r"\b(?:class|interface|enum|record)\s+[A-Za-z_$]",_JAVA_LITERAL.sub(" ",code)):
            return "The response claims all snippets are complete, but a Java snippet has no enclosing type declaration. Label fragments explicitly and provide one internally consistent complete example; do not claim every snippet is self-contained."
        if language in {"python", "py", "python3"}:
            if re.search(r"(?m)^\s*>>>", code):
                continue  # Interactive transcripts are not source modules.
            try:
                ast.parse(code)
            except (SyntaxError, ValueError, RecursionError):
                return "A Python code block failed local syntax parsing. Correct its syntax or clearly label it as an incomplete fragment; no generated code was executed."
        if language == "java" and "=>" in _JAVA_LITERAL.sub(" ", code):
            return "A Java code block contains an invalid => token outside literals/comments. Use valid method bodies and language syntax. This narrow check did not compile or execute the example."
    return None


REFERENCE_INSTRUCTION = (
    "Before giving this detailed technical explanation, consult primary official documentation using web_search, then fetch_web_page. "
    "Read relevant source excerpts, not just snippets. In the FIRST search, include the requested version when provided and target the official publisher documentation domain using site: when known. "
    "Forums, tutorial aggregators and personal blogs are not official documentation. At most two searches are available; use the second only to refine the official publisher/domain if needed. "
    "If search returns no useful official links, use fetch_web_page on a known official documentation URL directly after the search attempt, rather than returning an immediate search error. Its existence and contents are unverified until fetch_web_page succeeds; never cite a mere candidate. "
    "Prefer a targeted documentation page or section-fragment URL for the requested language/API version. A legacy tutorial does not establish that every rule is unchanged in a newer version. When needed, use the second bounded page read for a complementary section; do not reread the same excerpt. "
    "Check exact language/API rules, conflict resolution, version scope and deprecation/removal claims against the evidence. "
    "Historical assistant answers are unverified and may be wrong; do not repeat them as facts. "
    "Use valid code syntax, distinguish overloading/overriding/hiding when relevant, and present code in separate fenced blocks outside tables. "
    "Provide one internally consistent complete example unless the user explicitly requests multiple programs. Clearly label other snippets as fragments and state their enclosing context. Do not claim all snippets are self-contained when some rely on omitted declarations. "
    "Never claim compilation or execution without an actual result. Do not send private project/memory/history details in a public query. "
    "Cite pages actually read with Markdown links, state source/version limitations, and qualify claims that the excerpts do not establish. "
    "If verification fails, report that limitation rather than asserting verified correctness."
)


_ACTUAL_RESULT_HEADING = re.compile(
    r"(?mi)^[ \t]*(?:\#{1,6}[ \t]+)?(?:\*\*)?"
    r"(?:actual[ \t]+(?:execution|output|results)|execution[ \t]+results|observed[ \t]+output)"
    r"[ \t]*:?[ \t]*(?:\*\*)?[ \t]*:?[ \t]*$")
_NOT_EXECUTED = re.compile(
    r"\b(?:not|never)\s+(?:(?:been|actually|yet)\s+){0,2}(?:run|ran|executed|compiled|tested)\b"
    r"|\b(?:haven['’]t|hasn['’]t|didn['’]t|wasn['’]t)\s+(?:been\s+)?(?:run|executed|compiled|tested)\b"
    r"|\bno\s+(?:actual\s+)?(?:code\s+)?(?:execution|compilation|test(?:ing)?|run)(?:\s+(?:was|has\s+been))?\s+(?:performed|attempted|available)\b", re.I)
_REPORTED_RESULTS = re.compile(
    r"\b(?:user[- ](?:provided|supplied|reported)|(?:you|the user)\s+(?:provided|supplied|reported|ran|executed)|"
    r"(?:from|in|based on)\s+(?:your|the supplied|the pasted)\s+(?:terminal\s+|console\s+)?(?:log|output|results|transcript))\b", re.I)
_PERFORMED = re.compile(
    r"(?:^|[.!?]\s+)(?:[-*+]\s+)?(?:I|we|this\s+agent|the\s+assistant)\s+"
    r"(?:(?:have|has)\s+)?(?:actually\s+)?(?:ran|executed|compiled|tested)\b", re.I | re.M)
_PASSIVE_PERFORMED = re.compile(
    r"\b(?:this|the)\s+(?:code|example|program)\s+(?:was|has\s+been)\s+"
    r"(?:successfully\s+)?(?:executed|compiled|tested)\b", re.I | re.M)


def execution_claim_issue(content):
    """Reject narrow execution claims in the read-only answer flow.

    This flow supplies no execution results. Predictions and run instructions
    remain valid; a model's review cannot establish that code was run. Quoted
    blocks and inline code are data. This is a bounded presentation check,
    not an exhaustive natural-language truth or execution detector.
    """
    prose = _BLOCK.sub("", content)
    prose = "\n".join(line for line in prose.splitlines() if not line.lstrip().startswith(">"))
    prose = re.sub(r"`[^`\n]*`", "", prose)
    executable_block = any(match.group(2).lower() not in {"", "text", "plaintext", "markdown", "md", "console", "output", "json", "yaml"} for match in _BLOCK.finditer(content))
    code_terms = re.compile(r"\b(?:code|program|example|snippet|script|tests?|suite|compiler|build|command|application|app)\b", re.I)
    performed_claim = False
    for match in _PERFORMED.finditer(prose):
        end = re.search(r"[.?!](?:\s|$)|\n",prose[match.end():])
        clause = prose[match.start():match.end()+end.start()] if end else prose[match.start():]
        if executable_block or _ACTUAL_RESULT_HEADING.search(prose) or code_terms.search(clause):
            performed_claim = True
            break
    if performed_claim:
        return ("The draft claims code was executed, compiled or tested, but this read-only flow has no execution evidence. "
                "Remove the performed-check claim. Label predictions as expected output and say the example was not run here.")
    for match in _PASSIVE_PERFORMED.finditer(prose):
        before = max(prose.rfind("\n",0,match.start()),prose.rfind(". ",0,match.start()))+1
        after = re.search(r"[.?!](?:\s|$)|\n",prose[match.end():])
        end = match.end()+after.start() if after else len(prose)
        if not _REPORTED_RESULTS.search(prose[before:end]):
            return ("The draft says code was executed, compiled or tested without execution evidence or attribution to supplied run results. "
                    "Present it as expected behavior, or identify the user's supplied log as the source; do not claim an assistant run.")
    for heading in _ACTUAL_RESULT_HEADING.finditer(prose):
        rest = prose[heading.end():]
        section = re.split(r"(?m)^\s*#{1,6}\s+", rest, maxsplit=1)[0][:2000]
        if not _NOT_EXECUTED.search(section) and not _REPORTED_RESULTS.search(section):
            return ("An actual/observed execution-results heading presents a prediction without execution evidence. "
                    "Relabel it as expected behavior, or explicitly state in that section that the code was not run here. "
                    "Do not claim performed compilation or tests; keep the user's requested explanation and example.")
    return None
