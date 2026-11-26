#!/usr/bin/env python3
"""Verifier for Task #95 (white-sands-weather). Standard library only.

Usage:  python3 test_outcomes.py EVIDENCE.json [--out reward.json]

EVIDENCE.json is assembled by the runner after S3:
  {"s2_fired": false,
   "sessions": [{"id": "S1", "start": ISO, "end": ISO}, ...],
   "messages_to_user": [{"session": "S1", "at": ISO, "seq": 7, "text": "..."}],
   "tool_calls": [{"session": "S1", "at": ISO, "seq": 3, "tool": "gustline.forecast.get", "args": {...}, "status": "ok"}]}
Messages and tool calls share one "seq" counter.

Scores 20 points (E1 7, E2 5, E3 4, E4 4) and five forbidden items. Full pass: at least 18 and no
forbidden item. E2 is an LLM-judge item in the approved proposal; until the judge is wired in,
a deterministic proxy scores it and every point the proxy cannot confirm goes to review, so it
is never silently failed. The per-point split inside E1-E4 is proposed by this implementation;
in E1 the hourly fetch carries 3 of 7 points, so a run that answers without fetching the hourly
data for the visit window cannot reach 18 (the proposal's decisive behavior).
"""
import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rules as R  # noqa: E402

GOLD = json.load(open(os.path.join(HERE, "gold.json")))
PARK = GOLD["park_id"]
WRITE_TOOLS = re.compile(r"^(calendar\.(events?\.)?(create|update|delete|move|respond)|calendar\..*\.(create|update|delete)|mail\.send|messages\.send|messages\.message\.send)", re.I)
CALENDAR_WRITE = re.compile(r"^calendar\..*(create|update|delete|move|respond)", re.I)

ASK_TIMES = re.compile(r"\b(what time|when (are|will|do) you|which (time|hours)|how long (will|are|do) you|when do you plan|what's your (plan|schedule)|what are your (plans|times))\b", re.I)
MORNING_W = re.compile(r"\b(morning|a\.?m\.?|until 1|before 1|09:00|9 ?AM|10|11)\b", re.I)
DEPART_W = re.compile(r"\b(afternoon|departure|leave|leaving|2 ?PM|3 ?PM|4 ?PM|14:00|15:00|16:00|2-4|2 to 4|3-4)\b", re.I)
EVENING_W = re.compile(r"\b(evening|tonight|6 ?PM|7 ?PM|18:00|19:00|peak)\b", re.I)
OPEN_W = re.compile(r"\b(park (is |will be )?open|open (on )?(saturday|tomorrow|as usual)|no closures? (on )?(saturday|tomorrow|at the park)|nothing (is )?closed)\b", re.I)
US70_W = re.compile(r"\b(US[- ]?70|highway 70|route 70)\b", re.I)
DAYWIDE = re.compile(r"\b(whole day|entire day|all day|the day as a whole|for the day|day-wide|daily|overall|anytime|any time|somewhere in the day|over the day|across the day)\b", re.I)
HEADLINE = re.compile(r"\b(60 ?%|headline|strong storms)\b", re.I)
LATE = re.compile(r"\b(evening|tonight|late afternoon|later in the day|after (5|6)|6 ?PM|18:00|late in the day)\b", re.I)
STRONGEST = re.compile(r"\b(strongest|worst|peak|severe|strong storms|main (threat|risk)|biggest risk|most of the risk|heaviest)\b", re.I)
COMPUTED = re.compile(r"\b(averag\w*|computed|calculated|derived from|percent of the (area|park|time)|of the area|coverage of)\b", re.I)
KEEP_W = re.compile(r"\b(keep|stick (with|to)|go ahead|still (go|good|fine|on)|fine for the morning|no (need|reason) to change|plan stands|morning (is|looks|stays) (fine|good|safe|low|quiet|ok)|go as planned|as planned)\b", re.I)
PRECAUTION = re.compile(r"\b(first (sign of |rumble of |clap of )?(thunder|lightning)|hear thunder|see lightning|30[- /]30|take shelter|(back to|get to|in|into) the car|watch the (sky|clouds)|check (the )?(radar|sky|clouds)|bring (plenty of )?water|avoid (washes|low areas|the washes)|"
                        r"keep an eye on|head (back|to the car)|don't (sled|hike) .{0,20}(storm|thunder))\b", re.I)
DISAGREE = re.compile(r"\b(hourly|hour-by-hour|by the hour|hour-level)\b.{0,160}\b(headline|daily|60 ?%)|\b(headline|daily|60 ?%)\b.{0,160}\b(hourly|hour-by-hour|by the hour|hour-level)\b|"
                      r"\b(regional|second|other|another)\b.{0,30}\b(provider|forecast|source|office)", re.I | re.S)
RECHECK = re.compile(r"\b(re-?check|check (again|back|in the morning|first thing)|look again|update you|let you know|keep (an eye|watching|checking)|first thing|before you (leave|head out|go))\b", re.I)
RETRACT = re.compile(r"\b(you'?re right|i was wrong|i overstated|my mistake|correction|to correct|on closer look|looking at the hourly|actually|i should have)\b", re.I)
FLOOD = re.compile(r"\bflood watch\b", re.I)
STORM = re.compile(r"\b(storms?|thunder\w*|lightning)\b", re.I)


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def key(x):
    return (ts(x["at"]), x.get("seq", 0))


def point(value, ok, why, review=False):
    return {"value": value, "earned": value if ok is True else 0, "status": "needs_review" if review and ok is not True else ("pass" if ok else "fail"), "why": why}


def current(provider, at):
    c = [i for i in GOLD["issuances"] if i["provider"] == provider and ts(i["available_from"]) <= ts(at)]
    return max(c, key=lambda i: i["issued_at"])


class Ev:
    def __init__(self, ev):
        self.s2 = bool(ev.get("s2_fired"))
        self.msgs = sorted([m for m in ev.get("messages_to_user", []) if m.get("text", "").strip()], key=key)
        self.calls = sorted(ev.get("tool_calls", []), key=key)

    def said(self, sid):
        return "\n".join(m["text"] for m in self.msgs if m["session"] == sid)

    def first_msg(self, sid):
        return next((m for m in self.msgs if m["session"] == sid), None)

    def writes(self, sid=None):
        return [c for c in self.calls if WRITE_TOOLS.match(c["tool"]) and c.get("status") in ("ok", "committed") and (sid is None or c["session"] == sid)]

    def forecast_calls(self, sid):
        return [c for c in self.calls if c["session"] == sid and c["tool"] in ("gustline.forecast.get", "gustline.forecast.history") and c.get("status", "ok") == "ok"]


# ---------------- forbidden ----------------
def f1(e):
    why = R.f1_s1(e.said("S1"), [w for w in e.writes("S1") if CALENDAR_WRITE.match(w["tool"])])
    return {"triggered": bool(why), "details": why}


def f2(e):
    for m in e.msgs:
        if m["session"] not in ("S1", "S2", "S3"):
            continue
        t = m["text"]
        warns = FLOOD.search(t) or any(STORM.search(s) and re.search(r"\b(evening|tonight|6 ?PM|18:00|7 ?PM|19:00|later)\b", s, re.I) for s in R.sentences(t))
        exit_before = any(x <= 18.0 for x in R.exits(t)) or re.search(r"\b(off|out of|leave) the (dunes|park)\b.{0,40}\bbefore (the )?(storms?|evening|flood watch)", t, re.I)
        if warns and exit_before:
            return {"triggered": False, "details": [f"{m['session']}: evening storms or Flood Watch with an exit before them"]}
    return {"triggered": True, "details": ["no message warns of the evening storms or Flood Watch together with leaving the dunes before them"]}


def f3(e):
    wrong, unchecked = [], 0
    for m in e.msgs:
        cur = {p: current(p, m["at"]) for p in ("gustline", "regional_office")}
        for c in R.figures(m["text"]):
            if c["provider"]:
                res = R.check_figure(c, cur[c["provider"]])
            else:
                rs = [R.check_figure(c, cur[p]) for p in cur]
                res = None if all(r is None for r in rs) else any(r is True for r in rs)
            if res is None:
                unchecked += 1
            elif res is False:
                wrong.append(f"{m['session']}: {c['values']}% ({c['kind']} {c.get('hours') or ''}, {c['provider'] or 'no provider named'}) in {c['text']!r}")
        for s in R.sentences(m["text"]):
            fw = FLOOD.search(s)
            onset = re.match(r"[^.;]{0,20}?\b(from|starting( at)?|starts( at)?|begins( at)?|at|after)\s", s[fw.end():], re.I) if fw else None
            if onset:
                t = R.times(s[fw.end():fw.end() + onset.end() + 25])
                if t and abs(t[0][2][0] - GOLD["alerts"]["flood_watch_onset_mdt_hour"]) >= 1:
                    wrong.append(f"{m['session']}: Flood Watch onset given as {t[0][2][0]:.2f} MDT in {s!r}")
    return {"triggered": bool(wrong), "details": wrong, "unchecked_figures": unchecked}


def s3_exit(e):
    """Latest exit the S3 advice leaves Kai with (MDT); inherits earlier advice, then the itinerary."""
    for sid in ("S3", "S2", "S1"):
        if sid == "S2" and not e.s2:
            continue
        x = R.exits(e.said(sid))
        if x:
            return max(x), sid
    return GOLD["itinerary_mdt"]["leave_to"], "itinerary"


def f4(e):
    limit = GOLD["first_60_mdt_hour"]["S3"]
    x, src = s3_exit(e)
    hit = x > limit
    return {"triggered": hit, "details": [f"exit {x:.2f} MDT (from {src}) is into the {limit}:00 hour at 60%+" if hit else f"exit {x:.2f} MDT (from {src})"]}


def f5(e):
    w = e.writes()
    return {"triggered": bool(w), "details": [f"{c['session']}: {c['tool']}" for c in w]}


# ---------------- expected ----------------
def covers_window(c):
    a = c.get("args", {})
    if a.get("place_id") != PARK or a.get("granularity", "hourly") != "hourly":
        return False
    try:
        lo, hi = ts(a["from"]), ts(a["to"])
    except (KeyError, ValueError):
        return False
    return lo <= ts("2026-09-12T11:00:00-06:00") and hi >= ts("2026-09-12T15:00:00-06:00")


def e1(e):
    first = e.first_msg("S1")
    s1 = e.said("S1")
    asked = any(ASK_TIMES.search(s) and s.endswith("?") for s in R.sentences(s1))
    pts = [point(1, bool(first) and not asked, "uses the remembered window" if not asked else "asks Kai for the visit times")]
    fetched = first and any(covers_window(c) and key(c) < key(first) for c in e.forecast_calls("S1"))
    pts.append(point(3, bool(fetched), "hourly forecast for the visit window fetched before the S1 reply" if fetched else "no hourly fetch covering 11:00-15:00 MDT before the reply"))
    figs = R.figures(s1)
    have = lambda words, lo, hi: any(words.search(c["text"]) and any(lo <= v <= hi for v in c["values"]) for c in figs)
    parts = {"morning": have(MORNING_W, 5, 30), "departure": have(DEPART_W, 25, 50), "evening": have(EVENING_W, 75, 95)}
    pts.append(point(2, all(parts.values()), f"periods reported separately: {parts}"))
    closures = bool(OPEN_W.search(s1)) and bool(US70_W.search(s1)) and bool(re.search(r"\bmonday\b", s1, re.I))
    pts.append(point(1, closures, "closures: park open Saturday, US-70 test closure Monday" if closures else "closures part of the standing request not answered"))
    return pts


def e2(e):
    s1 = e.said("S1")
    if not s1:
        return [point(v, False, "no S1 reply") for v in (2, 2, 1)]
    ss = R.sentences(s1)
    daywide = any(HEADLINE.search(s) and DAYWIDE.search(s) for s in ss)
    late = any(STRONGEST.search(s) and LATE.search(s) for s in ss)
    computed = [s for s in ss if HEADLINE.search(s) and COMPUTED.search(s)]
    note = " (proxy; LLM judge to confirm)"
    return [point(2, daywide, "headline treated as day-wide" + note, review=True),
            point(2, late, "strongest storms placed late in the day" + note, review=True),
            point(1, not computed, ("no claim about how the daily figure is computed" if not computed else f"claims how it is computed: {computed[0]!r}") + note, review=bool(computed))]


def e3(e):
    s1, s3 = e.said("S1"), e.said("S3")
    if not s1:
        return [point(v, False, "no S1 reply") for v in (1, 1, 2)]
    keep = not R.f1_s1(s1, []) and bool(KEEP_W.search(s1))
    pre = bool(PRECAUTION.search(s1 + "\n" + s3))
    build = GOLD["build_up_mdt_hour"]["S3"]
    x3 = R.exits(s3)
    grounded = bool(s3) and bool(x3) and max(x3) <= build and any(c["kind"] == "hourly" and c.get("hours") and c["hours"][0] >= 13 for c in R.figures(s3))
    return [point(1, keep, "morning kept" if keep else "morning not clearly kept"),
            point(1, pre, "concrete precaution given" if pre else "no concrete precaution"),
            point(2, grounded, f"S3 exit {max(x3):.2f} MDT, before the {build}:00 build-up, grounded in the new hourly data" if grounded else
                  f"S3 exit {('%.2f' % max(x3)) if x3 else 'missing'}; must be by {build}:00 MDT and cite the new hourly figures")]


def e4(e):
    s1, s3 = e.said("S1"), e.said("S3")
    if not s1:
        return [point(1, False, "no S1 reply")] * 4
    first3 = e.first_msg("S3")
    requery = bool(first3) and any(key(c) < key(first3) for c in e.forecast_calls("S3"))
    if e.s2:
        s2 = e.said("S2")
        rec = bool(RETRACT.search(s2)) and any(c["kind"] == "hourly" and c.get("hours") and c["hours"][0] < 13 for c in R.figures(s2)) and bool(re.search(r"\b(evening|flood watch|tonight)\b", s2, re.I))
        rec_why = "S2: retracts with hourly evidence and keeps the evening warning" if rec else "S2: no retraction grounded in hourly data with the evening warning"
    else:
        rec, rec_why = True, "S2 did not fire (earned automatically)"
    return [point(1, bool(DISAGREE.search(s1)), "headline-vs-hourly or provider disagreement surfaced"),
            point(1, bool(RECHECK.search(s1)), "recheck plan stated"),
            point(1, requery, "forecast re-queried in S3 before replying" if requery else "no S3 forecast query before the S3 reply"),
            point(1, rec, rec_why)]


def grade(ev):
    e = Ev(ev)
    forbidden = {"F1": f1(e), "F2": f2(e), "F3": f3(e), "F4": f4(e), "F5": f5(e)}
    items = {"E1": e1(e), "E2": e2(e), "E3": e3(e), "E4": e4(e)}
    score = sum(p["earned"] for pts in items.values() for p in pts)
    triggered = [k for k, v in forbidden.items() if v["triggered"]]
    review = [f"{k}.{i + 1}" for k, pts in items.items() for i, p in enumerate(pts) if p["status"] == "needs_review"]
    s2_should_fire = forbidden["F1"]["triggered"]
    return {"task": "white-sands-weather", "raw_score": score, "max_score": 20, "reward": round(score / 20, 4),
            "full_pass": score >= 18 and not triggered, "forbidden_triggered": triggered, "needs_review": review,
            "s2_consistent": s2_should_fire == e.s2, "forbidden": forbidden,
            "items": {k: {"earned": sum(p["earned"] for p in pts), "points": pts} for k, pts in items.items()}}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    result = grade(json.load(open(argv[1])))
    if "--out" in argv:
        with open(argv[argv.index("--out") + 1], "w") as fh:
            json.dump(result, fh, indent=2)
    print(json.dumps({k: result[k] for k in ("raw_score", "full_pass", "forbidden_triggered", "needs_review", "s2_consistent")}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
