#!/usr/bin/env python3
"""Check a Task Track proposal against the task proposal template.

Usage:
    python3 check_task_proposal.py proposals/task/<slug>.md [--template PATH] [--strict]

The script is advisory. It lists gaps (something the template asks for that is
not there yet) and notes (worth a second look), then prints a suggested PR
title. Neither blocks submission: a proposal can be opened with gaps, and
reviewers will ask about them. The exit status is 0 unless --strict is given,
in which case it is 1 when there is at least one gap.

It checks what can be checked mechanically: structure, leftover placeholders,
domain names, the length of the personalization insight, rubric points and the
pass mark, coverage of rubric items by the reference solution, and timestamps.
It cannot judge whether the task is personal, whether the hint leaks the
solution or whether the story is coherent. Those need a reader.

Only the Python standard library is used.
"""

import argparse
import html
import re
import sys
from pathlib import Path

TEMPLATE_RELATIVE = Path("proposals/templates/task-proposal.md")
INSIGHT_LIMIT = 240
PLACEHOLDER = re.compile(r"\[Fill in(?!: …\])")
HEADING = re.compile(r"^(#{2,3})\s+(.*?)\s*$")
BULLET_FIELD = re.compile(r"^\s*[-*]\s+\*\*([^*]+?)(?:\s*\((required|optional)\))?:\*\*[ \t]*(.*)$")
BLOCK_FIELD = re.compile(r"^\*\*(?:✍️\s*)?([^*]+?)\s*\((required|optional)\):\*\*[ \t]*(.*)$")
RUBRIC_ITEM = re.compile(r"^\s*[-*]\s+\*\*([FE]\d+)\b([^*]*)\*\*(.*)$")
RUBRIC_ID = re.compile(r"(?<![A-Za-z0-9])([FE]\d+)(?![A-Za-z0-9])")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?")
OFFSET = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})")
ACTION_WORDS = (
    "order", "cancel", "send", "switch", "book", "buy", "pay", "reply", "choose",
    "wait", "decline", "accept", "refund", "reschedule", "delete", "forward",
)


class Report:
    def __init__(self):
        self.gaps = []
        self.notes = []

    def gap(self, message, line=None):
        self.gaps.append((line, message))

    def note(self, message, line=None):
        self.notes.append((line, message))

    def lines(self):
        out = []
        for level, items in (("GAP ", self.gaps), ("NOTE", self.notes)):
            for line, message in items:
                where = f"line {line}: " if line else ""
                out.append(f"{level}  {where}{message}")
        return out


def find_template(proposal, explicit):
    if explicit:
        return Path(explicit)
    for base in [proposal.resolve().parent, *proposal.resolve().parents, Path.cwd()]:
        candidate = base / TEMPLATE_RELATIVE
        if candidate.is_file():
            return candidate
    return None


def structure(text):
    """Return the headings, field labels and table row labels of a document."""
    headings, fields, rows = [], [], []
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            headings.append(heading[2])
            continue
        if RUBRIC_ITEM.match(line):
            continue
        field = BULLET_FIELD.match(line) or BLOCK_FIELD.match(line)
        if field:
            fields.append((field[1].strip(), field[2] or ""))
            continue
        if line.startswith("|"):
            first = line.strip().strip("|").split("|")[0].strip()
            if first and re.match(r"^[A-Za-z][A-Za-z ,/&-]*$", first):
                rows.append(first)
    return headings, fields, rows


def bullet_value(text, label):
    """Value of a '- **Label (required):** value' field, including indented continuation lines."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        field = BULLET_FIELD.match(line)
        if not (field and field[1].strip().casefold() == label.casefold()):
            continue
        indent = len(line) - len(line.lstrip())
        body = [field[3]]
        for following in lines[index + 1:]:
            if not following.strip() or len(following) - len(following.lstrip()) <= indent:
                break
            body.append(following.strip())
        return "\n".join(body).strip(), index + 1
    return None, None


def block_value(text, label):
    """Text of a '**✍️ Label (required):**' block, up to the next block or heading."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        field = BLOCK_FIELD.match(line)
        if not (field and field[1].strip().casefold() == label.casefold()):
            continue
        body = [field[3]]
        for following in lines[index + 1:]:
            if BLOCK_FIELD.match(following) or re.match(r"^#{1,3}\s", following):
                break
            body.append(following)
        return "\n".join(body).strip(), index + 1
    return None, None


def section(text, heading):
    """Text under the heading titled `heading` (section number optional), up to the next heading of the same or higher level."""
    wanted = re.sub(r"^\d+\.\s*", "", heading).casefold()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if not (match and re.sub(r"^\d+\.\s*", "", match[2]).casefold() == wanted):
            continue
        level = len(match[1])
        body = []
        for following in lines[index + 1:]:
            nxt = re.match(r"^(#{1,3})\s", following)
            if nxt and len(nxt[1]) <= level:
                break
            body.append(following)
        return "\n".join(body)
    return None


def empty(value):
    return value is None or not value.strip() or bool(PLACEHOLDER.search(value))


def check_structure(text, template, report):
    t_headings, t_fields, t_rows = structure(template)
    headings, fields, rows = structure(text)
    have_headings = {h.casefold() for h in headings}
    have_fields = {name.casefold() for name, _ in fields}
    have_rows = {r.casefold() for r in rows}
    if any("rubric" in h.casefold() for h in t_headings) and not any("rubric" in h.casefold() for h in headings):
        report.note("this file seems to follow an older version of the template; the parts it does not have yet are listed as gaps")
    for heading in t_headings:
        body = section(template, heading) or ""
        instructional = not (PLACEHOLDER.search(body) or "(required)" in body)
        if heading.casefold() not in have_headings and not instructional:
            report.gap(f"missing heading from the template: \"{heading}\"")
    for name, _ in dict.fromkeys(t_fields):
        if name.casefold() not in have_fields:
            report.gap(f"missing field from the template: \"{name}\"")
    for row in t_rows:
        if row.casefold() not in have_rows:
            report.gap(f"missing table row from the template: \"{row}\"")


def check_required_fields(text, template, report):
    seen = set()
    for line in template.splitlines():
        bullet = BULLET_FIELD.match(line)
        block = None if bullet else BLOCK_FIELD.match(line)
        match = bullet or block
        if not match or RUBRIC_ITEM.match(line) or match[2] != "required":
            continue
        label = match[1].strip()
        if label.casefold() in seen or label.casefold() == "your answer":
            continue
        seen.add(label.casefold())
        value, number = (bullet_value if bullet else block_value)(text, label)
        if number and empty(value):
            report.gap(f"required field \"{label}\" is empty", number)


def check_placeholders(text, template, report):
    template_lines = set(template.splitlines()) if template else set()
    open_items = []
    for number, line in enumerate(text.splitlines(), 1):
        if PLACEHOLDER.search(line):
            report.gap("placeholder left in the file: replace `[Fill in: …]` with an answer", number)
        elif re.search(r"\bTBD\b", line) and line not in template_lines and "use `TBD`" not in line:
            open_items.append(str(number))
    if open_items:
        report.note(f"{len(open_items)} line(s) contain TBD (lines {', '.join(open_items)}); make sure each says how it will be resolved")


def check_domains(text, template, report):
    table = template.split("<table>", 1)[1].split("</table>", 1)[0] if "<table>" in template else ""
    domains = {html.unescape(d) for d in re.findall(r"<strong>(.*?)</strong>", table)}
    if not domains:
        report.note("could not read the domain names from the template; domains were not checked")
        return None, []
    primary, number = bullet_value(text, "Primary domain")
    secondary_raw, sec_number = bullet_value(text, "Secondary domains")
    if primary and not empty(primary) and primary not in domains:
        report.gap(f"primary domain \"{primary}\" is not one of the template's domain names", number)
    secondary = []
    if secondary_raw and not empty(secondary_raw) and secondary_raw.casefold() != "none":
        # Domain names themselves contain "&", so split on the longest names first.
        rest = secondary_raw
        for name in sorted(domains, key=len, reverse=True):
            if name in rest:
                secondary.append(name)
                rest = rest.replace(name, "")
        if re.sub(r"[\s,+;/]|and", "", rest):
            report.gap(f"secondary domains contain a name that is not in the template: \"{secondary_raw}\"", sec_number)
        secondary.sort(key=secondary_raw.index)
    return primary, secondary


def check_insight(text, report):
    insight, number = bullet_value(text, "Personalization insight")
    if insight and not empty(insight) and len(insight) > INSIGHT_LIMIT:
        report.gap(f"personalization insight is {len(insight)} characters; the limit is {INSIGHT_LIMIT}", number)


def rubric_items(block, prefix):
    items = []
    for line in block.splitlines():
        match = RUBRIC_ITEM.match(line)
        if match and match[1].startswith(prefix):
            points = re.search(r"\((\d+)\s*points?\)", match[2])
            items.append({"id": match[1], "points": int(points[1]) if points else None, "text": line})
    return items


def check_rubric(text, report):
    forbidden_block, f_line = block_value(text, "Forbidden")
    expected_block, e_line = block_value(text, "Expected")
    if forbidden_block is None or expected_block is None:
        return set()
    forbidden = rubric_items(forbidden_block, "F")
    expected = rubric_items(expected_block, "E")
    if not forbidden:
        report.gap("no forbidden items found; list them as \"- **F1 — name.** …\"", f_line)
    if not expected:
        report.gap("no expected items found; list them as \"- **E1 (N points) — name.** …\"", e_line)
    ids = [item["id"] for item in forbidden + expected]
    for duplicate in sorted({i for i in ids if ids.count(i) > 1}):
        report.gap(f"rubric item {duplicate} is defined more than once")
    for item in forbidden + expected:
        if "*Evidence:*" not in item["text"]:
            report.gap(f"{item['id']} has no \"*Evidence:*\" (the record and date from which the agent can learn it)")
        if "*Checked from:*" not in item["text"]:
            report.gap(f"{item['id']} has no \"*Checked from:*\" (the data the grader reads)")
    for item in expected:
        if item["points"] is None:
            report.gap(f"{item['id']} has no points; write them as \"{item['id']} (N points)\"")
    total = sum(item["points"] or 0 for item in expected)
    stated = re.match(r"\s*`?(\d+)`?\s*points?", expected_block)
    if expected and not stated:
        report.note("the total is not stated after \"Expected (required):\"; write it as \"N points.\"", e_line)
    elif expected and int(stated[1]) != total:
        report.gap(f"expected items add up to {total} points, but the stated total is {stated[1]}", e_line)

    full_pass, p_line = block_value(text, "Full pass")
    if full_pass is not None and not empty(full_pass):
        mark = re.search(r"at least\s+(\d+)\s+(?:of|out of|/)\s+(\d+)", full_pass)
        if not mark:
            report.note("could not read the pass mark; state it as \"at least N of M\"", p_line)
        elif expected:
            needed, out_of = int(mark[1]), int(mark[2])
            if out_of != total:
                report.gap(f"the pass mark is out of {out_of}, but the expected items add up to {total}", p_line)
            gap = out_of - needed
            largest = max(expected, key=lambda item: item["points"] or 0)
            if needed > out_of:
                report.gap("the pass mark is higher than the total", p_line)
            elif (largest["points"] or 0) <= gap:
                report.gap(
                    f"an agent can miss any single expected item and still pass: the largest item ({largest['id']}, "
                    f"{largest['points']} points) is not larger than the {gap}-point gap between the total and the pass mark",
                    p_line,
                )
        if "forbidden" not in full_pass.casefold():
            report.note("the full-pass rule does not mention forbidden items", p_line)
    return set(ids)


def check_hint(text, report):
    hint, number = block_value(text, "Hint")
    if hint is None or empty(hint):
        return
    hint_text = hint.split("\n\n", 1)[0]
    if re.search(r"[$€£¥]\s?\d|\b\d+(?:\.\d+)?\s?%|\b\d{1,2}:\d{2}\b", hint_text):
        report.note("the hint contains an amount, percentage or clock time; a hint points to records and should not state values", number)
    found = [w for w in ACTION_WORDS if re.search(rf"\b{w}\b", hint_text, re.I)]
    if found:
        report.note(f"the hint may prescribe an action ({', '.join(found)}); it should say where to look, not what to do", number)


def check_reference(text, rubric_ids, report):
    body = section(text, "Reference solution")
    reference, number = block_value(text, "Reference")
    if body is None or reference is None:
        return
    rows = [l for l in reference.splitlines() if l.startswith("|") and not re.match(r"^\|\s*:?-{3,}", l)]
    if len(rows) < 3 and not empty(reference):
        report.note("the reference has fewer than two steps; give one row per step of the timeline", number)
    used = set(RUBRIC_ID.findall(body))
    for missing in sorted(rubric_ids - used, key=lambda i: (i[0], int(i[1:]))):
        report.gap(f"no step of the reference solution cites {missing}; a full-score reference must satisfy every item")
    for unknown in sorted(used - rubric_ids, key=lambda i: (i[0], int(i[1:]))):
        report.gap(f"the reference solution cites {unknown}, which is not a rubric item")


def check_timestamps(text, report):
    story = section(text, "Story outline") or ""
    if story and not TIMESTAMP.search(story) and not PLACEHOLDER.search(story):
        report.note("the story outline has no timestamps; date each event so reviewers can see what the agent could know when")
    for number, line in enumerate(text.splitlines(), 1):
        for match in TIMESTAMP.finditer(line):
            if not OFFSET.match(line, match.end()):
                report.gap(f"timestamp {match[0]} has no UTC offset (for example -04:00)", number)


def pr_title(text, primary, secondary):
    title, _ = bullet_value(text, "Short task title")
    if empty(title) or empty(primary):
        return None
    return f"[Task Proposal] [{' + '.join([primary, *secondary])}] {title}"


def check(text, template):
    report = Report()
    primary, secondary = None, []
    if template is None:
        report.note("task proposal template not found; structure and domain names were not checked (pass --template)")
    else:
        check_structure(text, template, report)
        check_required_fields(text, template, report)
        primary, secondary = check_domains(text, template, report)
    check_placeholders(text, template or "", report)
    check_insight(text, report)
    rubric_ids = check_rubric(text, report)
    check_hint(text, report)
    check_reference(text, rubric_ids, report)
    check_timestamps(text, report)
    return report, pr_title(text, primary, secondary)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a Task Track proposal against the task proposal template.")
    parser.add_argument("proposal", help="path to proposals/task/<slug>.md")
    parser.add_argument("--template", help="path to the task proposal template (found automatically inside the repository)")
    parser.add_argument("--strict", action="store_true", help="exit with status 1 when there is at least one gap")
    args = parser.parse_args(argv)

    proposal = Path(args.proposal)
    if not proposal.is_file():
        print(f"File not found: {proposal}", file=sys.stderr)
        return 2
    template_path = find_template(proposal, args.template)
    template = template_path.read_text(encoding="utf-8") if template_path and template_path.is_file() else None
    report, title = check(proposal.read_text(encoding="utf-8"), template)

    print(proposal)
    for line in report.lines():
        print(line)
    if title:
        print(f"Suggested PR title: {title}")
    print(f"Result: {len(report.gaps)} gap(s), {len(report.notes)} note(s). These do not block submission.")
    return 1 if args.strict and report.gaps else 0


if __name__ == "__main__":
    sys.exit(main())
