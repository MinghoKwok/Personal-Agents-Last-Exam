#!/usr/bin/env python3
"""Check a review file against the proposal it reviews.

Usage:
  check_feedback.py <author-feedback.md> <proposal.md>
  check_feedback.py --report <review-report.md | decisions-needed.md> <proposal.md>

Always checked:
  - cited line numbers ("第 N 行", "line N", ":N" in backticks, "L N") that are missing or blank
  - double-quoted English phrases that do not occur in the proposal
  - a quotation that is not on (or next to) any line cited in the same paragraph
Author feedback only (no --report):
  - a header item count that differs from the numbered items
  - leftover <...> template placeholders
  - wording that should not reach the author ("has been forwarded", strengths,
    "not a blocker", unverified "please check"), ignoring text inside double quotes
Double-quoted English phrases are treated as quotations from the proposal; write
platform terms in backticks instead. Quotes containing Chinese are skipped. In
--report mode expect a few leads that are not errors (the PR title, the reviewer's
own words); read each one rather than treating the count as a score. Exit code 1 when anything is reported.
"""
import re, sys

def norm(s):
    s = s.replace("’", "'").replace("“", '"').replace("”", '"').replace("…", "...")
    return re.sub(r"\s+", " ", s).lower()

CITE = re.compile(r"第 ?([\d、,，\-–— ]+) ?行|\b[Ll]ines? ([\d, \-–]+(?:and \d+)?)|`:(\d+)`|(?<![\w/.])L ?(\d+)\b|\.md:(\d+)")
QUOTE = re.compile(r"[\"“]([A-Za-z#(~][^\"”\n]{5,})[\"”]")

def cited(text):
    out = []
    for m in CITE.finditer(text):
        raw = next(g for g in m.groups() if g)
        for tok in re.findall(r"\d+(?:\s*[\-–—]\s*\d+)?", raw):
            ends = [int(x) for x in re.findall(r"\d+", tok)]
            out.extend(range(ends[0], ends[-1] + 1))
    return out

def main():
    args = [a for a in sys.argv[1:] if a != "--report"]
    report = "--report" in sys.argv[1:]
    if len(args) != 2:
        print(__doc__); return 2
    fb = open(args[0], encoding="utf-8").read()
    lines = open(args[1], encoding="utf-8").read().split("\n")
    nlines = [norm(l) for l in lines]
    whole = norm(" ".join(lines)); whole_nobt = whole.replace("`", "")
    problems = []

    for n in cited(fb):
        if n < 1 or n > len(lines) or not lines[n - 1].strip():
            problems.append(f"line {n} is cited but is missing or blank in the proposal")

    for para in re.split(r"\n(?=\s*(?:[-*]|\d+\.|\|)\s)|\n\s*\n", fb):
        nums = [n for n in cited(para) if 1 <= n <= len(lines)]
        for q in QUOTE.findall(para):
            if re.search(r"[\u4e00-\u9fff]", q):
                continue  # not a quotation from an English proposal
            parts = [norm(x).strip() for x in re.split(r"\.\.\.|…", q)]
            parts = [x for x in parts if len(x) > 4]
            if not parts:
                continue
            if any(x not in whole and x.replace("`", "") not in whole_nobt for x in parts):
                problems.append(f'quoted text not found in the proposal: "{q}"'); continue
            if nums:
                near = " ".join(nlines[k] for n in nums for k in range(max(0, n - 2), min(len(lines), n + 1)))
                if not any(x in near or x.replace("`", "") in near.replace("`", "") for x in parts):
                    problems.append(f'quotation is not on any line cited with it ({sorted(set(nums))}): "{q[:60]}"')

    if not report:
        head = re.search(r"共 (\d+) 条|\((\d+) items?\)|（(\d+) 条）", fb)
        count = len(re.findall(r"^\d+\. \*\*", fb, flags=re.M))
        if head:
            h = int(next(g for g in head.groups() if g))
            if h != count:
                problems.append(f"header says {h} items but {count} are numbered")
        if re.search(r"<[^<>\n`!]{1,60}>", re.sub(r"`[^`]*`", "", fb)):
            problems.append("a <...> template placeholder was left in")
        unquoted = QUOTE.sub("", fb)
        for pat, why in [(r"已转交|has been forwarded", "says something was forwarded: confirm that it was, and name who decides"),
                         (r"做得好的地方|What works|^#+ *Notes", "strengths / notes section"),
                         (r"不妨碍批准|not a blocker", "tells the author something is fine instead of something to do"),
                         (r"请核对|please check whether", "unverified claim: verify it yourself, then state it or drop it")]:
            for m in re.finditer(pat, unquoted, flags=re.M | re.I):
                problems.append(f"{why}: …{unquoted[max(0, m.start()-20):m.end()+20].strip()}…")

    problems = list(dict.fromkeys(problems))
    for p in problems:
        print("-", p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
