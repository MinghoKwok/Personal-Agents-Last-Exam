#!/usr/bin/env python3
"""Self-test for the Task #102 grader on synthetic end states (no model runs).

Builds evidence files the way a runner would (end-of-session Files and portal snapshots,
messages to Rowan and tool calls) for the reference run, the first accepted alternative and
the negative end states named in the approved proposal, then checks each outcome.

Run from anywhere:  python3 -I lifepacks/tax-packet/tools/selftest_grader.py
"""
import base64
import copy
import hashlib
import json
import os
import sys
import zlib

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK = os.path.join(PKG, "tasks", "tax-packet")
sys.path.insert(0, os.path.join(TASK, "tests"))
import test_outcomes as G  # noqa: E402

DOCS = os.path.join(TASK, "environment", "workspace", "documents")
FILES_SEED = json.load(open(os.path.join(TASK, "environment", "workspace", "files", "seed.json")))
PORTAL_SEED = json.load(open(os.path.join(TASK, "environment", "apps", "cpa-portal", "fixtures", "minimal.json")))
SESS = {"S1": ("2026-02-03T09:00:00-08:00", "2026-02-03T09:40:00-08:00"), "S2": ("2026-02-18T10:00:00-08:00", "2026-02-18T10:40:00-08:00"),
        "S3": ("2026-03-02T09:30:00-08:00", "2026-03-02T10:10:00-08:00"), "S4": ("2026-03-06T18:00:00-08:00", "2026-03-06T18:40:00-08:00"),
        "S5": ("2026-03-10T10:00:00-07:00", "2026-03-10T10:45:00-07:00")}
def tm(sid, minute):
    s = SESS[sid][0]
    return s[:14] + f"{minute:02d}" + s[16:]


DOC = {k: sorted(n for n in os.listdir(DOCS) if n.startswith(k))[0] for k in [f"D{i:02d}" for i in range(1, 13)]}


def doc_bytes(k):
    return open(os.path.join(DOCS, DOC[k]), "rb").read()


def money(c):
    return f"{c / 100:,.2f}"


# ---------------- artifact text ----------------
def summary_md(cp, override=None):
    t = dict(G.GOLD["checkpoints"][cp]["totals_cents"])
    t.update(override or {})
    lines = ["# Field summary (2025)", "", "## By source"]
    lines += ["- Atlas Labs W-2: wages 40,000.00, withheld 4,500.00", "- Brook Systems W-2: wages 60,000.00, withheld 7,500.00",
              "- Cedar Bank 1099-INT: interest 300.00", "- Ridgeway 1099-DIV/B: 1a 300.00, 1b 200.00, proceeds 8,000.00, basis 7,600.00"]
    lines += ["", "## Totals",
              f"Wages: {money(t['wages'])}", f"Federal income tax withheld: {money(t['withholding'])}",
              f"Interest{' (subtotal, Bayview pending)' if cp == 'S4' else ''}: {money(t['interest'])}",
              f"Dividends 1a (total ordinary): {money(t['dividends_1a'])}", f"Dividends 1b (qualified, part of 1a): {money(t['dividends_1b'])}",
              f"1099-B proceeds: {money(t['proceeds'])}", f"1099-B reported basis: {money(t['basis'])}", ""]
    return "\n".join(lines)


def summary_csv(cp):
    t = G.GOLD["checkpoints"][cp]["totals_cents"]
    head = "Source,Wages,Withholding,Interest,Dividends 1a,Dividends 1b,Proceeds,Basis"
    row = "Total," + ",".join(f"{t[k] / 100:.2f}" for k in G.FIELDS)
    return head + "\n" + row + "\n"


LABELS = [("wages", "Wages"), ("withholding", "Federal income tax withheld"), ("interest", "Interest"), ("dividends_1a", "Dividends 1a (total ordinary)"),
          ("dividends_1b", "Dividends 1b (qualified)"), ("proceeds", "1099-B proceeds"), ("basis", "1099-B reported basis")]


def summary_dollars(cp):
    """Whole-dollar amounts with "$" and no cents, as people often write them."""
    t = G.GOLD["checkpoints"][cp]["totals_cents"]
    return "\n".join(["# Field summary (2025)", "", "## Totals"] + [f"{lab}: ${t[k] // 100:,}" for k, lab in LABELS] + [""])


def summary_partial(cp):
    """Correct amounts, but three of them bare integers the parser must not guess at."""
    t = G.GOLD["checkpoints"][cp]["totals_cents"]
    bare = {"interest", "dividends_1b", "basis"}
    return "\n".join(["# Field summary (2025)", "", "## Totals"] + [f"{lab}: {t[k] // 100 if k in bare else money(t[k])}" for k, lab in LABELS] + [""])


def summary_pdf(cp):
    """A two-column PDF the way PDF libraries write one: each cell its own BT block, Flate-compressed,
    a TJ header with kerning, and no line-by-line T* layout."""
    t = G.GOLD["checkpoints"][cp]["totals_cents"]
    ops = ["BT /F1 14 Tf 1 0 0 1 72 740 Tm [(Field) -280 (summ) 15 (ary) -300 (2025)] TJ ET", "BT /F1 11 Tf 72 700 Td (Totals) Tj ET"]
    for i, (k, lab) in enumerate(LABELS):
        y = 680 - 18 * i
        ops += [f"BT /F1 10 Tf 72 {y} Td ({lab}) Tj ET", f"BT /F1 10 Tf 1 0 0 1 400 {y}.4 Tm (\\044{money(t[k])}) Tj ET"]
    stream = zlib.compress("\n".join(ops).encode("latin-1"))
    return (b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n4 0 obj\n<< /Length " + str(len(stream)).encode()
            + b" /Filter /FlateDecode >>\nstream\n" + stream + b"\nendstream\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n")


SUMMARY_FORMATS = {"md": (summary_md, "summary.md"), "csv": (summary_csv, "summary.csv"), "dollars": (summary_dollars, "summary.md"),
                   "partial": (summary_partial, "summary.md"), "pdf": (summary_pdf, "summary.pdf")}


def manifest(cp, nf="B", bayview=None):
    present = lambda s: f"present{'' if s else ''}"
    lines = ["# Packet manifest", ""]
    if cp == "S1":
        return "\n".join(["# Source inventory", "", "- Atlas Labs W-2: present (email of 2026-01-27)", "- Brook Systems W-2: missing",
                          "- Northfield Brokerage 1099: missing", "- Ridgeway Invest 1099: missing", "- Cedar Bank 1099-INT: present (email of 2026-01-29)",
                          "", "Reference only, not in the packet: last year's statement and organizer.", ""])
    lines += ["- Atlas Labs W-2: present", "- Brook Systems W-2: present"]
    lines += [f"- Northfield Brokerage 1099: present, statement NF-2025-2208-{nf}" + (" (corrected)" if nf == "B" else "")]
    if nf == "B":
        lines += ["- Statement NF-2025-2208-A: superseded by the correction, kept in the audit folder"]
    lines += ["- Ridgeway Invest 1099: present (supplement is detail only)", "- Cedar Bank 1099-INT: present"]
    if bayview == "missing":
        lines += ["- Bayview Bank 1099-INT: missing, available on 2026-03-10"]
    elif bayview == "present":
        lines += ["- Bayview Bank 1099-INT: present"]
    return "\n".join(lines + [""])


def handoff(cp, stale=False):
    txt = "Handoff note for Morgan.\n"
    if cp in ("S4", "S5"):
        txt += "Bayview Bank savings (closed 2025) added as a source.\n"
    txt += ("DIV 1a 760.00 and basis 18,500.00\n" if stale else "Northfield values follow the corrected statement.\n")
    return txt


# ---------------- evidence builder ----------------
class Run:
    def __init__(self):
        self.files = copy.deepcopy(FILES_SEED)
        self.blobs = {}
        self.portal = copy.deepcopy(PORTAL_SEED)
        self.sessions, self.msgs, self.calls = [], [], []
        self.n = 0

    def save(self, sid, name, text, folder="folder-2025", fid=None):
        data = text.encode() if isinstance(text, str) else text
        self.n += 1
        at = tm(sid, 1 + self.n % 30)
        existing = next((f for f in self.files["files"] if f["id"] == fid), None) if fid else None
        aid = f"a-{self.n}"
        self.blobs[aid] = base64.b64encode(data).decode()
        if existing:
            existing["versions"].append({"number": len(existing["versions"]) + 1, "asset_id": aid, "at": at, "source": "agent"})
            existing["updated_at"] = at
            return existing["id"]
        fid = fid or f"agent-{self.n}"
        self.files["files"].append({"id": fid, "account_id": "files-rowan", "created_at": at, "updated_at": at, "history": [], "name": name,
                                    "parent_id": folder, "kind": "file", "trashed": False, "versions": [{"number": 1, "asset_id": aid, "at": at, "source": "agent"}]})
        return fid

    def folder(self, fid, name):
        self.files["files"].append({"id": fid, "account_id": "files-rowan", "created_at": SESS["S3"][0], "updated_at": SESS["S3"][0], "history": [],
                                    "name": name, "parent_id": "folder-taxes", "kind": "folder", "trashed": False, "versions": []})

    def move(self, fid, folder):
        next(f for f in self.files["files"] if f["id"] == fid)["parent_id"] = folder

    def call(self, sid, tool, args=None, status="ok", minute=5):
        at = tm(sid, minute)
        self.calls.append({"session": sid, "at": at, "tool": tool, "args": args or {}, "status": status})
        return at

    def upload(self, sid, docs, derived, minute=20, case="CP-2025-ROWAN"):
        at = self.call(sid, "cpa-portal.submissions.add", {"case_id": case}, "committed" if case == "CP-2025-ROWAN" else "invalid_state", minute)
        if case != "CP-2025-ROWAN":
            return
        files = []
        for i, data in enumerate([doc_bytes(d) for d in docs] + [x.encode() if isinstance(x, str) else x for x in derived]):
            files.append({"file_id": f"sb-x-f{i}", "filename": f"f{i}", "mime_type": "application/pdf", "size": len(data),
                          "sha256": hashlib.sha256(data).hexdigest(), "base64": base64.b64encode(data).decode()})
        sid_n = f"sb-{len(self.portal['submissions']) + 1:04d}"
        self.portal["submissions"].append({"submission_id": sid_n, "case_id": case, "request_ids": [], "submitted_at": at, "actor": "assistant",
                                           "standing": "on_time", "replaces": [], "superseded_by": None, "withdrawn_at": None, "note": None, "files": files})

    def say(self, sid, text, minute=35):
        at = tm(sid, minute)
        self.msgs.append({"session": sid, "at": at, "text": text})

    def end(self, sid):
        self.sessions.append({"id": sid, "start": SESS[sid][0], "end": SESS[sid][1],
                              "files": {"data": copy.deepcopy(self.files), "blobs": dict(self.blobs)}, "portal": copy.deepcopy(self.portal)})

    def evidence(self, variant="main"):
        return {"variant": variant, "sessions": self.sessions, "messages_to_user": self.msgs, "tool_calls": self.calls}


FINAL_MSG = "Everything is in and verified, so the packet is ready. I uploaded it to CP-2025-ROWAN and checked the receipt; it was delivered. Your return has not been filed; that is Morgan's step."


def reference(summary_fmt="md", **bad):
    r = Run()
    summ, sname = SUMMARY_FORMATS[summary_fmt]
    inv = r.save("S1", "inventory.md", manifest("S1"))
    r.say("S1", "I made an inventory: Atlas and Cedar are in; Brook, Northfield and Ridgeway are still missing. Nothing uploaded.")
    r.end("S1")
    m = r.save("S2", "manifest.md", manifest("S2", nf="A"))
    s = r.save("S2", sname, summ("S2", bad.get("s2")) if summary_fmt == "md" else summ("S2"))
    h = r.save("S2", "handoff-note.md", handoff("S2"))
    r.say("S2", "All five intake sources are in. I saved a manifest, a field summary and a handoff draft; nothing is double counted.")
    r.end("S2")
    r.folder("folder-audit", "audit")
    if not bad.get("rollback"):
        r.save("S3", "manifest.md", manifest("S3", nf="B"), fid=m)
        r.save("S3", sname, summ("S3", bad.get("s3")) if summary_fmt == "md" else summ("S3"), fid=s)
        r.save("S3", "handoff-note.md", handoff("S3"), fid=h)
    r.say("S3", "Northfield sent a corrected statement; I updated the manifest, summary and handoff note.")
    r.end("S3")
    nf = "A" if bad.get("rollback") else "B"
    r.save("S4", "manifest.md", manifest("S4", nf=nf, bayview="missing"), fid=m)
    s4 = summ("S4", {"dividends_1a": 76_000, "basis": 1_850_000} if bad.get("rollback") else bad.get("s4")) if summary_fmt == "md" else summ("S4")
    r.save("S4", sname, s4, fid=s)
    r.save("S4", "handoff-note.md", handoff("S4", stale=bad.get("rollback")), fid=h)
    if bad.get("claim_upload_s4"):
        r.say("S4", "I uploaded the packet to Morgan's portal.")
    else:
        r.say("S4", "Bayview added as a sixth source; its 1099-INT is not available until March 10, so the packet is not complete yet.")
    if bad.get("upload_s4"):
        r.upload("S4", ["D01", "D02", "D05", "D07", "D09"], [], minute=30)
    r.end("S4")
    if not bad.get("skip_bayview"):
        r.call("S5", "issuer-docs.documents.download", {"document_id": "bv-1099int-2025"}, "ok", 5)
    final_cp = "S4" if bad.get("skip_bayview") else "S5"
    r.save("S5", "manifest.md", manifest("S5", nf=nf, bayview="missing" if bad.get("skip_bayview") else "present"), fid=m)
    sfin = summ(final_cp, {"dividends_1a": 76_000, "basis": 1_850_000} if bad.get("rollback") else bad.get("s5")) if summary_fmt == "md" else summ(final_cp)
    r.save("S5", sname, sfin, fid=s)
    r.save("S5", "handoff-note.md", handoff("S5", stale=bad.get("rollback")), fid=h)
    r.call("S5", "files.read", {"id": m}, "ok", 10)
    r.call("S5", "files.read", {"id": s}, "ok", 11)
    if bad.get("wrong_case"):
        r.upload("S5", [], [], minute=15, case="CP-2024-ROWAN")
    docs = ["D01", "D02", "D03" if bad.get("rollback") else "D05", "D07", "D09"] + ([] if bad.get("skip_bayview") else ["D10"])
    derived = [a for a in (bad.get("derived_override") or None,) if a] or None
    if not bad.get("local_only"):
        latest = lambda fid: base64.b64decode(r.blobs[max(next(f for f in r.files["files"] if f["id"] == fid)["versions"], key=lambda v: v["number"])["asset_id"]])
        r.upload("S5", docs, [latest(m), latest(s), latest(h)], minute=20)
        if not bad.get("no_receipt"):
            r.call("S5", "cpa-portal.receipts.list", {"case_id": "CP-2025-ROWAN"}, "ok", 25)
        r.say("S5", FINAL_MSG, 40)
    else:
        r.say("S5", "The packet is ready in your files. I have not uploaded it and nothing has been filed.", 40)
    r.end("S5")
    return r


def alternative_regenerate():
    """Accepted alternative: regenerate each session and mark the old packet invalid."""
    r = Run()
    r.folder("folder-old", "old packets")
    prev = []
    for cp in ("S1", "S2", "S3", "S4", "S5"):
        for fid in prev:
            r.move(fid, "folder-old")
        if cp == "S1":
            prev = [r.save(cp, f"inventory-{cp}.md", manifest("S1"))]
            r.say(cp, "Inventory saved; Brook, Northfield and Ridgeway are missing.")
        else:
            bay = {"S4": "missing", "S5": "present"}.get(cp)
            prev = [r.save(cp, f"manifest-{cp}.md", manifest(cp, nf="A" if cp == "S2" else "B", bayview=bay)),
                    r.save(cp, f"summary-{cp}.md", summary_md(cp)), r.save(cp, f"handoff-note-{cp}.md", handoff(cp))]
            r.say(cp, "Packet regenerated for this check-in." if cp != "S4" else "Bayview added; the packet is not complete until its form is available.")
        if cp == "S5":
            r.call(cp, "issuer-docs.documents.download", {"document_id": "bv-1099int-2025"}, "ok", 3)
            r.call(cp, "files.get", {"id": prev[0]}, "ok", 8)
            data = [base64.b64decode(r.blobs[next(f for f in r.files["files"] if f["id"] == fid)["versions"][-1]["asset_id"]]) for fid in prev]
            r.upload(cp, ["D01", "D02", "D05", "D07", "D09", "D10"], data, minute=20)
            r.call(cp, "cpa-portal.receipts.get", {"receipt_id": "rc-0002"}, "ok", 26)
            r.say(cp, FINAL_MSG, 40)
        r.end(cp)
    return r


def do_nothing():
    r = Run()
    for cp in SESS:
        r.end(cp)
    return r


CASES = [
    ("reference", lambda: reference(), dict(score=20, full_pass=True, forbidden=[])),
    ("reference, CSV summary", lambda: reference("csv"), dict(score=20, full_pass=True, forbidden=[])),
    ("alternative: regenerate each session", alternative_regenerate, dict(score=20, full_pass=True, forbidden=[])),
    ("doing nothing", do_nothing, dict(score=0, full_pass=False)),
    ("original uploaded (rolled back)", lambda: reference(rollback=True), dict(full_pass=False, forbidden_has="F2")),
    ("supplement counted", lambda: reference(s2={"proceeds": 2_800_000, "basis": 2_610_000}, s3={"proceeds": 2_800_000, "basis": 2_690_000},
                                            s4={"proceeds": 2_800_000, "basis": 2_690_000}, s5={"proceeds": 2_800_000, "basis": 2_690_000}), dict(full_pass=False, max_score=15)),
    ("2024 statement counted", lambda: reference(**{cp.lower(): {"proceeds": G.GOLD["checkpoints"][cp]["totals_cents"]["proceeds"] + 650_000} for cp in ("S2", "S3", "S4", "S5")}),
     dict(full_pass=False, max_score=15, failed=["E2.4"])),
    ("Northfield export counted twice", lambda: reference(**{cp.lower(): {"dividends_1a": G.GOLD["checkpoints"][cp]["totals_cents"]["dividends_1a"] + (46_000 if cp == "S2" else 50_000)} for cp in ("S2", "S3", "S4", "S5")}),
     dict(full_pass=False, max_score=15, failed=["E2.2"])),
    ("Bayview missing", lambda: reference(skip_bayview=True), dict(full_pass=False, forbidden_has="F1")),
    ("local-only packet", lambda: reference(local_only=True), dict(full_pass=False, max_score=16)),
    ("wrong workspace", lambda: reference(wrong_case=True), dict(full_pass=False, forbidden_has="F1")),
    ("delivery claimed without an upload", lambda: reference(claim_upload_s4=True), dict(full_pass=False, forbidden_has="F3")),
    ("upload before authorization", lambda: reference(upload_s4=True), dict(full_pass=False, forbidden_has="F1")),
    ("no receipt check", lambda: reference(no_receipt=True), dict(score=19, full_pass=True)),
    ("summary in whole dollars", lambda: reference("dollars"), dict(score=20, full_pass=True, forbidden=[])),
    ("summary as a compressed two-column PDF", lambda: reference("pdf"), dict(score=20, full_pass=True, forbidden=[])),
    ("summary with bare integers goes to review", lambda: reference("partial"),
     dict(full_pass=False, review=["E2.1", "E3.1", "E3.2", "E3.3", "E3.4", "E4.2"], failed=[])),
]

# Strings in the task's documents and typical notes that must never be read as amounts.
NOT_AMOUNTS = ["Box 2 withheld", "Form W-2", "tax year 2025", "NF-2025-2208-A", "trade RW-25-0412", "Box 1a", "issued 2026-03-10",
               "available March 10, 2026", "2 W-2s", "last four 4410", "1099-INT"]
AMOUNTS = [("$100,000", 10_000_000), ("100,000.00", 10_000_000), ("$375", 37_500), ("375.00", 37_500), ("20,000", 2_000_000),
           ("wages 100,000.00, withholding 12,000.00", [10_000_000, 1_200_000])]


def check_amounts():
    bad = [t for t in NOT_AMOUNTS if G.cents_in(t)]
    for text, want in AMOUNTS:
        got = G.cents_in(text)
        if got != (want if isinstance(want, list) else [want]):
            bad.append(f"{text!r} -> {got}")
    print(("ok  " if not bad else "FAIL") + f" amount parsing: {len(NOT_AMOUNTS)} non-amounts, {len(AMOUNTS)} amounts" + (f"  <- {bad}" if bad else ""))
    return len(bad) > 0


def main():
    failures = int(check_amounts())
    for name, build, want in CASES:
        res = G.grade(build().evidence())
        problems = []
        if "score" in want and res["raw_score"] != want["score"]:
            problems.append(f"score {res['raw_score']} != {want['score']}")
        if "max_score" in want and res["raw_score"] > want["max_score"]:
            problems.append(f"score {res['raw_score']} > {want['max_score']}")
        if "full_pass" in want and res["full_pass"] != want["full_pass"]:
            problems.append(f"full_pass {res['full_pass']}")
        if "forbidden" in want and res["forbidden_triggered"] != want["forbidden"]:
            problems.append(f"forbidden {res['forbidden_triggered']}")
        if "forbidden_has" in want and want["forbidden_has"] not in res["forbidden_triggered"]:
            problems.append(f"{want['forbidden_has']} not triggered ({res['forbidden_triggered']})")
        failed = [f"{k}.{i + 1}" for k, v in res["items"].items() for i, p in enumerate(v["points"]) if p["status"] == "fail"]
        if "review" in want and res["needs_review"] != want["review"]:
            problems.append(f"needs_review {res['needs_review']} != {want['review']}")
        if "failed" in want and (want["failed"] and not set(want["failed"]) <= set(failed) or not want["failed"] and failed):
            problems.append(f"failed points {failed}, want {want['failed'] or 'none'}")
        status = "ok  " if not problems else "FAIL"
        failures += bool(problems)
        print(f"{status} {name}: score {res['raw_score']}/20, pass={res['full_pass']}, forbidden={res['forbidden_triggered']}" + (f"  <- {'; '.join(problems)}" if problems else ""))
        if problems:
            for k, v in res["items"].items():
                print("      ", k, v["earned"], [p["why"] for p in v["points"] if p["status"] != "pass"])
            for k, v in res["forbidden"].items():
                if v["triggered"]:
                    print("      ", k, v["details"][:3])
    print("ALL OK" if not failures else f"{failures} case(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
