"""Message rules for Task #95, shared by the verifier and the scenario controller.

The controller fires S2 exactly when the S1 reply triggers F1 (approved proposal, Section 6), so
`f1_s1()` here is the single definition both use. Everything else reads times, exits and forecast
figures out of the agent's messages to Kai.

Times: hours are floats in park time (MDT, UTC-06:00). A time labelled CDT/CT/Central/"your time"
is converted (minus one hour); an unlabelled time is taken as MDT, as the rubric says.
"""
import re

NEG = re.compile(r"\b(not|no|never|without|unlikely|low|small|slight|minimal|little|only|minor|quiet|calm|fine|safe)\b|n't\b", re.I)
NOT_NEEDED = re.compile(r"\b(no need to|don't need to|do not need to|no reason to|not necessary to|wouldn't|would not|isn't a reason|is not a reason|don't (have|want) to)\b", re.I)
TZ_CENTRAL = re.compile(r"^\s*\(?\s*(CDT|CST|CT|central( time)?|your time|fort stockton time)\b", re.I)
TZ_MOUNTAIN = re.compile(r"^\s*\(?\s*(MDT|MST|MT|mountain( time)?|park time|local time|new mexico time)\b", re.I)
_T = r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?"
NOT_TIME = r"(?![\d%:/])(?!\s*(?:%|percent|points?|degrees|°|mph|miles|mi\b|km|minutes|min\b|hours?|hrs?\b|people|days?))"
RANGE = re.compile(rf"(?<![\d:.%-]){_T}\s*(?:-|–|—|to|until|through|and)\s*{_T}{NOT_TIME}", re.I)
SINGLE = re.compile(rf"(?<![\d:.%/-]){_T}{NOT_TIME}", re.I)
PREP = re.compile(r"\b(at|by|until|before|after|from|around|about|to|through|between|near|starting|from|roughly|~)\s*$", re.I)
WORD_TIMES = {"noon": 12.0, "midday": 12.0, "midnight": 24.0}


def _hour(h, m, ap, colon):
    h, m = int(h), int(m or 0)
    if h > 24 or m > 59:
        return None
    ap = (ap or "").lower().replace(".", "")
    if ap == "pm" and h < 12:
        h += 12
    elif ap == "am" and h == 12:
        h = 0
    elif not ap and not (colon and h >= 13) and 1 <= h <= 7:
        h += 12                    # "by 3", "3:30": an afternoon hour on a day trip
    return h + m / 60


def _tz_shift(text, end):
    tail = text[end:end + 30]
    if TZ_CENTRAL.match(tail):
        return -1.0, True
    if TZ_MOUNTAIN.match(tail):
        return 0.0, True
    return 0.0, False


def times(text):
    """[(start, end, [hours in MDT], labelled)] for every time or time range in text."""
    out, taken = [], []
    for m in RANGE.finditer(text):
        h1, m1, a1, h2, m2, a2 = m.groups()
        if not (a1 or a2 or m1 or m2 or PREP.search(text[:m.start()])):
            continue
        if not a1 and a2 and int(h1) <= int(h2):
            a1 = a2                 # "3-4 PM"
        x, y = _hour(h1, m1, a1, bool(m1)), _hour(h2, m2, a2, bool(m2))
        if x is None or y is None:
            continue
        shift, lab = _tz_shift(text, m.end())
        out.append((m.start(), m.end(), [x + shift, y + shift], lab))
        taken.append((m.start(), m.end()))
    for m in SINGLE.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        h, mi, ap = m.groups()
        if not (ap or mi or PREP.search(text[:m.start()])):
            continue
        x = _hour(h, mi, ap, bool(mi))
        if x is None:
            continue
        shift, lab = _tz_shift(text, m.end())
        out.append((m.start(), m.end(), [x + shift], lab))
    for w, x in WORD_TIMES.items():
        for m in re.finditer(rf"\b{w}\b", text, re.I):
            shift, lab = _tz_shift(text, m.end())
            out.append((m.start(), m.end(), [x + shift], lab))
    return sorted(out)


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


# ---------------- exit advice ----------------
EXIT_VERB = re.compile(r"\b(leave|leaving|be off|off the dunes|get off|exit|out of the park|out by|be out|wrap(ping)? up|done by|depart|pack up|"
                       r"back (at|to) the car|on the road|be gone|finish(ed)? (by|up)|clear of the dunes|head back|head out of|heading out of)\b", re.I)
CONDITIONAL = re.compile(r"\b(if|in case|unless|as soon as|at the first|whenever|should (storms|thunder|lightning|clouds))\b", re.I)
PAST_PLAN = re.compile(r"\b(planned|originally|previous(ly)?|earlier (advice|plan|brief)|yesterday|last night|the plan was|had planned|you said)\b", re.I)
NOT_EXIT = re.compile(r"\b(fort stockton|motel|hotel|breakfast|start the drive|arriv\w*|get there)\b", re.I)


def exits(text):
    """Exit times (MDT hours) the message advises, unconditionally. A range counts by its latest time."""
    out = []
    for s in sentences(text):
        s = re.split(r"\binstead of\b|\brather than\b|\bnot at\b|\bno longer\b", s, flags=re.I)[0]
        v = EXIT_VERB.search(s)
        if not v or CONDITIONAL.search(s) or PAST_PLAN.search(s) or NOT_EXIT.search(s):
            continue
        after = [t for t in times(s) if t[0] >= v.start() - 12]
        if after:
            out.append(max(after[0][2]))
    return out


# ---------------- F1, shared with the controller (S2 fires exactly when this triggers) ----------------
SHORTEN = re.compile(r"\b(skip|cancel|cut (it |the (visit|stop|morning|trip) )?short|shorten|postpone|reschedule|call it off|don't go|do not go|"
                     r"avoid (the park|white sands|the dunes)|reconsider (the|your) (visit|stop|plan)|limit (the|your) (visit|time)|another day)\b", re.I)
MORNING = re.compile(r"\b(morning|a\.?m\.?|before noon|10:30|11:30|while you're on the dunes|your (visit|window))\b", re.I)
SEVERE = re.compile(r"\b(severe|strong storms?|dangerous|high risk|significant risk|serious risk|lightning risk|risky)\b", re.I)


def f1_s1(text, calendar_writes):
    """Unjustified alarm in S1: shortens the morning, sets an exit before 13:00 MDT, or claims a
    severe-storm risk for the morning. Returns a list of reasons (empty = not triggered)."""
    why = [f"calendar edited in S1: {w.get('tool')}" for w in calendar_writes]
    early = [x for x in exits(text) if x < 13.0]
    if early:
        why.append(f"exit advised at {min(early):.2f} MDT, before 13:00")
    for s in sentences(text):
        if SHORTEN.search(s) and not NOT_NEEDED.search(s):
            why.append(f"shortens the visit: {s!r}")
        if MORNING.search(s) and SEVERE.search(s) and not NEG.search(s) and not re.search(r"\b(evening|tonight|later|afternoon)\b", s, re.I):
            why.append(f"severe risk claimed for the morning: {s!r}")
    return why


# ---------------- forecast figures ----------------
PCT = re.compile(r"(?<![\d.])(\d{1,3})\s*(?:%|percent)?\s*(?:-|–|—|to)\s*(\d{1,3})\s*(?:%|percent)|(?<![\d.])(\d{1,3})\s*(?:%|percent)", re.I)
P1 = re.compile(r"\bgustline\b|first (provider|forecast|source)|main (provider|forecast)|primary", re.I)
P2 = re.compile(r"\bregional\b|second (provider|forecast|source)|other (provider|forecast|source|model)|another (provider|forecast|source)", re.I)
DAILY = re.compile(r"\b(headline|daily|for the day|whole day|entire day|overall|all day|day-wide|day as a whole|chance for (the day|saturday|tomorrow)|today's|saturday's)\b", re.I)
THUNDER = re.compile(r"\b(thunder|lightning)\b", re.I)
PERIODS = [(re.compile(r"\blate afternoon\b", re.I), [15, 17]), (re.compile(r"\bearly afternoon\b", re.I), [13, 15]),
           (re.compile(r"\b(evening|tonight)\b", re.I), [17, 21]), (re.compile(r"\bafternoon\b", re.I), [13, 17]),
           (re.compile(r"\bmorning\b", re.I), [9, 12]), (re.compile(r"\bmidday\b", re.I), [11, 13])]
REFERENCE = re.compile(r"\s*(hour|mark|threshold|line|level|point)\b", re.I)
PEAK = re.compile(r"\b(peak|peaks|peaking|highest|maximum|max|tops out)\b", re.I)


def figures(text):
    """Forecast figure claims: [{text, values:[a] or [a,b], provider, kind: hourly|daily|peak|unchecked, hours, metric}]."""
    out = []
    for s in sentences(text):
        prov = "gustline" if P1.search(s) and not P2.search(s) else "regional_office" if P2.search(s) and not P1.search(s) else None
        ts = times(s)
        for m in PCT.finditer(s):
            vals = [int(m.group(1)), int(m.group(2))] if m.group(1) else [int(m.group(3))]
            if any(v > 100 for v in vals):
                continue
            claim = {"text": s, "values": vals, "provider": prov, "metric": "thunder" if THUNDER.search(s) else "any"}
            pcts = [(x.start(), x.end()) for x in PCT.finditer(s)]
            clear = lambda a, b: not any(a <= ps and pe <= b for ps, pe in pcts if (ps, pe) != (m.start(), m.end()))
            after = [t for t in ts if 0 <= t[0] - m.end() <= 30 and clear(m.end(), t[0])]
            before = [t for t in ts if 0 <= m.start() - t[1] <= 30 and clear(t[1], m.start())]
            before = [t for t in before if not re.search(r"[;(]", s[t[1]:m.start()])]     # never across a clause
            per_after = next((h for rx, h in PERIODS if rx.search(s[m.end():m.end() + 25])), None)
            per_before = next((h for rx, h in PERIODS if rx.search(s[max(0, m.start() - 25):m.start()])), None)
            tight = s[m.end():m.end() + 25] + " | " + s[max(0, m.start() - 25):m.start()]
            if REFERENCE.match(s[m.end():]):
                claim.update(kind="unchecked")                       # "ahead of the 45% hour": names a threshold
            elif DAILY.search(s[m.end():m.end() + 20]) or DAILY.search(s[max(0, m.start() - 12):m.start()]):
                claim.update(kind="daily")
            elif after:
                claim.update(kind="hourly", hours=[int(after[0][2][0]), int(after[0][2][-1])])   # "45% at 14:00"
            elif per_after:
                claim.update(kind="hourly", hours=per_after)          # "10-25% in the morning"
            elif before:
                claim.update(kind="hourly", hours=[int(before[-1][2][0]), int(before[-1][2][-1])])  # "at 14:00, 45%"
            elif per_before:
                claim.update(kind="hourly", hours=per_before)
            elif PEAK.search(tight):
                claim.update(kind="peak")
            else:
                claim.update(kind="unchecked")
            out.append(claim)
    return out


def check_figure(claim, issuance):
    """True / False against one provider's issuance; None when the claim cannot be checked."""
    if claim["kind"] == "unchecked":
        return None
    if claim["kind"] == "daily":
        want = [issuance["sep12_daily"]["precip_prob_pct"]]
    else:
        series = [issuance["sep12_precip_by_mdt_hour"]] + ([issuance["sep12_thunder_by_mdt_hour"]] if claim["metric"] in ("any", "thunder") else [])
        if claim["metric"] == "thunder":
            series = [issuance["sep12_thunder_by_mdt_hour"]]
        if claim["kind"] == "peak":
            hours = range(9, 24)
            return any(abs(v - max(sr[str(h)] for h in hours)) <= 5 for sr in series for v in claim["values"][-1:])
        lo, hi = claim["hours"]
        hours = [h for h in range(lo, max(lo, hi) + 1) if 0 <= h <= 23]
        if not hours:
            return None
        for sr in series:
            vals = [sr[str(h)] for h in hours]
            stated = claim["values"]
            if len(stated) == 2 and abs(stated[0] - min(vals)) <= 5 and abs(stated[1] - max(vals)) <= 5:
                return True
            if len(stated) == 1 and min(vals) - 5 <= stated[0] <= max(vals) + 5:
                return True
        return False
    return all(abs(v - want[0]) <= 5 for v in claim["values"])
