#!/usr/bin/env python3
"""Generate the proposal index from GitHub data without running PR code."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import html
from http.client import RemoteDisconnected
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

try:
    from .review_identity import can_self_review, is_automated_reviewer
except ImportError:
    from review_identity import can_self_review, is_automated_reviewer

INDEX_PATH = "proposals/proposal-list.md"
INDEX_BRANCH = "proposal-index"
# Per-PR results reused between runs. Stored next to the index on the bot-only branch.
CACHE_PATH = "proposals/proposal-cache.json"
# Open PRs are re-read at least this often even when GitHub reports no update.
OPEN_REFRESH_SECONDS = 6 * 3600
MAX_PROPOSAL_BYTES = 200_000
TITLE = re.compile(r"^\[(Environment|Task) Proposal\]\s*(?:\[([^\]]+)\])?\s*(.*)$", re.I)
PROPOSAL_PATH = re.compile(r"^proposals/(environment|task)/[A-Za-z0-9][A-Za-z0-9_.-]*\.md$")
URL = re.compile(r"(https?://\S+)")


class APIError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class RateLimited(APIError):
    """GitHub refused the request because the token's API quota is exhausted."""

    def __init__(self, status, message, reset=None):
        super().__init__(status, message)
        self.reset = reset


def rate_limit_notice(job, error):
    when = ""
    if error.reset:
        when = " The quota resets at " + datetime.fromtimestamp(error.reset, timezone.utc).strftime("%H:%M UTC") + "."
    print(f"::error title=GitHub API rate limit::{job} is incomplete.{when} "
          f"Pending commands remain in PR comments for scheduled recovery. {error}")


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid repository name")
        self.repository = repository
        self.token = token
        self._last_write = 0.0

    def request(self, path, method="GET", data=None):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Only GitHub API paths are supported")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        payload = None if data is None else json.dumps(data).encode()
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = Request("https://api.github.com" + path, data=payload, headers=headers, method=method)
        if method not in {"GET", "HEAD"}:
            # Serialize writes below GitHub's secondary content-creation limit,
            # especially when backfilling merge checks for many existing PRs.
            time.sleep(max(0.0, 1.1 - (time.monotonic() - self._last_write)))
            self._last_write = time.monotonic()
        for attempt in range(3):
            try:
                with urlopen(request, timeout=30) as response:
                    if response.status == 204:
                        return None
                    return json.load(response)
            except HTTPError as error:
                h = error.headers or {}
                retry_after, reset = h.get("retry-after"), h.get("x-ratelimit-reset")
                reset = int(reset) if reset and reset.isdigit() else None
                # Inspect only for classification; never log bodies or credentials.
                try:
                    message = json.loads(error.read(8192)).get("message", "").lower()
                except (ValueError, AttributeError):
                    message = ""
                limited = error.code in {403, 429} and (error.code == 429 or
                    h.get("x-ratelimit-remaining") == "0" or retry_after or "rate limit" in message)
                diagnostic = (f"GitHub API {error.code} for {method} {path}; "
                    f"remaining={h.get('x-ratelimit-remaining', 'unknown')}, "
                    f"reset={reset}, retry_after={retry_after}, request_id={h.get('x-github-request-id', 'unknown')}")
                if limited:
                    delay = int(retry_after) if retry_after and retry_after.isdigit() else (
                        max(1, reset - int(time.time()) + 1) if reset and h.get("x-ratelimit-remaining") == "0" else 60)
                    if attempt < 2 and delay <= 60:
                        print(f"::warning::{diagnostic}; retrying in {delay}s", file=sys.stderr)
                        time.sleep(delay)
                        continue
                    raise RateLimited(error.code, diagnostic, reset) from None
                if error.code in {500, 502, 503, 504} and method in {"GET", "HEAD"} and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(error.code, diagnostic) from None
            except (URLError, RemoteDisconnected, TimeoutError, ConnectionError) as error:
                # A POST may have committed before losing its response. Recover
                # from live state next run instead of blindly creating it twice.
                if method in {"GET", "HEAD"} and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(0, f"GitHub transport error for {method} {path}: {type(error).__name__}") from None

    def pages(self, path, **params):
        for page in range(1, 1001):
            batch = self.request(path + "?" + urlencode(dict(params, per_page=100, page=page)))
            if not isinstance(batch, list):
                raise RuntimeError("Unexpected paginated response")
            yield from batch
            if len(batch) < 100:
                return
        raise RuntimeError("Pagination limit reached; refusing to publish a partial index")

    def contents(self, path, ref):
        endpoint = f"/repos/{self.repository}/contents/{quote(path, safe='/')}?{urlencode({'ref': ref})}"
        try:
            result = self.request(endpoint)
        except APIError as error:
            if error.status == 404:
                return None
            raise
        if not isinstance(result, dict) or result.get("type") != "file":
            raise ValueError("Expected a regular file")
        return result


def decode_file(result, limit=None):
    if result.get("encoding") != "base64":
        raise ValueError("Unsupported file encoding")
    if limit is not None and result.get("size", 0) > limit:
        raise ValueError("Proposal exceeds the text size limit")
    raw = base64.b64decode(result["content"])
    if limit is not None and len(raw) > limit:
        raise ValueError("Proposal exceeds the text size limit")
    return raw.decode("utf-8")


def clean(value):
    value = value.strip().strip("`").strip()
    if "[Fill in:" in value or value.casefold() in {"none", "n/a", "tbd"}:
        return ""
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("**", "")
    return " ".join(value.split())


def field(text, name):
    # The value is the rest of the label's own line; an empty value must not capture the next line.
    pattern = r"^[ \t]*(?:[-*][ \t]+)?\*\*" + re.escape(name) + r"(?:\s*\([^)]*\))?:\*\*[ \t]*(.*)$"
    match = re.search(pattern, text, re.M | re.I)
    return clean(match[1]) if match else ""


def answer(text, heading):
    pattern = r"^##\s+\d+\.\s+" + re.escape(heading) + r"\s*\n(.*?)(?=^##\s|\Z)"
    section = re.search(pattern, text, re.M | re.S | re.I)
    if not section:
        return ""
    bullet = re.search(
        r"^\s*[-*]\s+\*\*Personalization insight(?:\s*\([^)]*\))?:\*\*\s*(.*?)(?=^\s*[-*]\s+\*\*|\n\n|\Z)",
        section[1],
        re.M | re.S | re.I,
    )
    if bullet:
        return clean(bullet[1])
    response = re.search(r"\*\*(?:✍️\s*)?Your answer \(required\):\*\*\s*(.*)", section[1], re.S)
    return clean(response[1].split("\n\n", 1)[0]) if response else ""


def domains_from_readme(text):
    if "## 🏗️ Environment domains" not in text:
        raise ValueError("Could not read canonical domains")
    section = text.split("## 🏗️ Environment domains", 1)[1].split("</table>", 1)[0]
    domains = [html.unescape(x) for x in re.findall(r"<strong>(.*?)</strong>", section)]
    if not domains or len(domains) != len(set(domains)):
        raise ValueError("Could not read canonical domains")
    return set(domains)


def labels(pr):
    return {item["name"].casefold() for item in pr.get("labels", [])}


def track(pr):
    named = TITLE.match(pr.get("title", ""))
    tagged = labels(pr) & {"track:environment", "track:task"}
    if len(tagged) == 1:
        return next(iter(tagged)).split(":")[1]
    if named:
        return named[1].lower()
    checked = re.findall(r"^\s*- \[[xX]\]\s*(Environment|Task) Track\s*$", pr.get("body") or "", re.M)
    return checked[0].lower() if len(checked) == 1 else None


def review_state(reviews, pr):
    latest = {}
    commented = False
    for review in sorted(reviews, key=lambda x: (x.get("submitted_at") or "", x.get("id", 0))):
        if is_automated_reviewer(review.get("user")):
            continue
        state = review.get("state", "").upper()
        user = (review.get("user") or {}).get("login")
        if not user or user == (pr.get("user") or {}).get("login"):
            continue
        if state in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            latest[user] = state
        elif state == "COMMENTED":
            commented = True
    changes = sum(state == "CHANGES_REQUESTED" for state in latest.values())
    approvals = sum(state == "APPROVED" for state in latest.values())
    if changes:
        return f"Changes requested ({changes})", True
    if approvals:
        return f"Approved ({approvals})", False
    if any(not is_automated_reviewer(u) for u in pr.get("requested_reviewers", [])) or pr.get("requested_teams"):
        return "Review requested", False
    return ("Commented" if commented else "Awaiting review"), False


def progress(pr, changes_requested):
    if pr.get("merged_at"):
        return "Accepted"
    if pr.get("state") == "closed":
        return "Closed"
    if pr.get("draft"):
        return "Draft"
    if changes_requested:
        return "Changes requested"
    for label, state in [("validation", "Validation"), ("in-progress", "Implementation"), ("plan-approved", "Plan approved")]:
        if label in labels(pr):
            return state
    return "Design review"


def proposal_text(api, pr, kind):
    files = list(api.pages(f"/repos/{api.repository}/pulls/{pr['number']}/files"))
    if len(files) >= 3000:
        # GitHub lists at most 3000 files. Flag this row rather than abort the whole index.
        return "", "", "PR changes too many files to identify the proposal file"
    paths = [x["filename"] for x in files if x.get("status") != "removed" and PROPOSAL_PATH.fullmatch(x["filename"])]
    paths = [path for path in paths if path.split("/")[1] == kind]
    if len(paths) != 1:
        return "", "", "Add exactly one proposal file for this track"
    path = paths[0]
    # The base repository's pull ref also works for public fork PRs. Never check out the head.
    ref = (pr.get("head") or {}).get("sha") or f"refs/pull/{pr['number']}/head"
    try:
        result = api.contents(path, ref)
        if result is None and pr.get("merged_at") and pr.get("merge_commit_sha"):
            result = api.contents(path, pr["merge_commit_sha"])
    except ValueError:
        # A symlink, submodule or directory at the proposal path. API errors still abort the run.
        return "", path, "Proposal path must be a regular Markdown file"
    if result is None:
        return "", path, "Proposal file is unavailable"
    try:
        return decode_file(result, MAX_PROPOSAL_BYTES), path, ""
    except (ValueError, UnicodeError):
        return "", path, "Proposal must be a UTF-8 text file of at most 200 KB"


REVIEW_QUERY = """query ProposalReviews($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on PullRequest {
      id number
      reviews(first: 100) {
        nodes { databaseId state submittedAt updatedAt author { login __typename } }
        pageInfo { hasNextPage }
      }
    }
  }
}"""


def open_review_snapshots(api, pulls):
    """Read reviews in batches without executing a fork's review-event workflow.

    Read even when updated_at is unchanged: edits/dismissals must invalidate the
    displayed review state independently of the proposal metadata cache.
    """
    selected = [p for p in pulls if p.get("state") == "open" and p.get("node_id")]
    snapshots = {}
    for offset in range(0, len(selected), 50):
        batch = selected[offset:offset + 50]
        for attempt in range(3):
            try:
                # This fixed GraphQL document is read-only despite HTTP POST.
                result = api.request("/graphql", "POST", {
                    "query": REVIEW_QUERY, "variables": {"ids": [p["node_id"] for p in batch]}})
                break
            except APIError as error:
                if error.status not in {0, 500, 502, 503, 504} or attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        nodes = (result.get("data") or {}).get("nodes")
        if result.get("errors") or not isinstance(nodes, list) or len(nodes) != len(batch):
            raise ValueError("Incomplete GitHub review snapshot; refusing to publish stale review state")
        for pr, node in zip(batch, nodes):
            if (not node or node.get("id") != pr["node_id"] or node.get("number") != pr["number"]
                    or not isinstance(node.get("reviews"), dict)):
                raise ValueError("GitHub review snapshot did not match the requested PR")
            connection = node["reviews"]
            if connection["pageInfo"]["hasNextPage"]:
                # Never silently truncate heavily reviewed proposals.
                reviews = list(api.pages(f"/repos/{api.repository}/pulls/{pr['number']}/reviews"))
            else:
                reviews = [{"id": r.get("databaseId") or 0, "state": r["state"],
                    "submitted_at": r.get("submittedAt"), "updated_at": r.get("updatedAt"),
                    "user": {"login": (r.get("author") or {}).get("login"),
                             "type": (r.get("author") or {}).get("__typename", "")}}
                    for r in connection["nodes"]]
            snapshots[pr["number"]] = reviews
    return snapshots


def cache_key(pr, reviews=None):
    # Metadata and review activity have independent cache identities. The head
    # SHA pins proposal contents; a fresh review snapshot detects dismissals.
    head, updated = (pr.get("head") or {}).get("sha"), pr.get("updated_at")
    if not head or not updated:
        return None
    key = [updated, head]
    if reviews is not None:
        rows = sorted((r.get("id") or 0, r.get("state") or "", r.get("submitted_at") or "", r.get("updated_at") or "",
                       (r.get("user") or {}).get("login") or "") for r in reviews)
        key.append(hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest())
    return key


def collect(api, domain_names, branch, cache=None, now=None):
    """Build index records. When a cache dict is given, reuse unchanged PRs and update it in place."""
    records = []
    now = time.time() if now is None else now
    rules = json.loads(Path(__file__).resolve().parents[1].joinpath(".github/review-policy.json").read_text())
    pulls = [p for p in api.pages(f"/repos/{api.repository}/pulls", state="all", base=branch,
                                sort="created", direction="desc") if track(p)]
    review_snapshots = open_review_snapshots(api, pulls)
    for summary in pulls:
        kind = track(summary)
        if kind is None:
            continue
        # The list response already contains these PR fields. Avoid one extra
        # API request per proposal on every index refresh.
        pr = summary
        reviews = review_snapshots.get(pr["number"])
        key = cache_key(pr, reviews)
        entry = (cache or {}).get(str(pr["number"]))
        if (key and isinstance(entry, dict) and entry.get("key") == key and isinstance(entry.get("record"), dict)
                and (pr.get("state") == "closed" or now - entry.get("fetched", 0) < OPEN_REFRESH_SECONDS)):
            records.append(entry["record"])
            continue
        text, path, issue = proposal_text(api, pr, kind)
        named = TITLE.match(pr.get("title", ""))
        title_domains = [x.strip() for x in (named[2] or "").split("+")] if named else []
        primary = field(text, "Primary domain")
        secondary = field(text, "Secondary domains")
        if not text and title_domains and title_domains[0] in domain_names:
            primary = title_domains[0]
        if primary not in domain_names:
            primary = "Needs a valid primary domain"
        heading = "What you plan to build" if kind == "environment" else "What makes this distinct and personal"
        synopsis = answer(text, heading) or field(pr.get("body") or "", "Summary")
        if kind == "environment":
            connections = [field(text, "Internal personal apps"), field(text, "Other apps and websites")]
            synopsis = "; ".join(x for x in [synopsis, *connections] if x)
        title = (field(text, "Reference app or website / URL") if kind == "environment" else field(text, "Short task title"))
        title = title or (named[3] if named else pr.get("title", ""))
        if reviews is None:
            reviews = list(api.pages(f"/repos/{api.repository}/pulls/{pr['number']}/reviews"))
        review, changes = review_state(reviews, pr)
        if review == "Awaiting review" and can_self_review(pr["user"]["login"], pr["user"].get("id"), rules):
            review = "Owner review; no external reviewer required"
        lifecycle = {}
        if labels(pr) & {"plan-approved", "plan-needs-review", "in-progress", "validation", "ready-to-merge", "v1-overdue"}:
            try:
                from .proposal_lifecycle import load_state
            except ImportError:
                from proposal_lifecycle import load_state
            lifecycle, _ = load_state(list(api.pages(f"/repos/{api.repository}/issues/{pr['number']}/comments")), pr["number"])
        records.append({
            "number": pr["number"], "track": kind, "title": title, "path": path,
            "primary": primary, "secondary": secondary, "synopsis": synopsis or "Summary pending",
            "issue": issue, "status": progress(pr, changes), "review": review,
            "created_at": pr["created_at"], "merged_at": pr.get("merged_at"),
            "author": (pr.get("user") or {}).get("login") or "ghost",
            "lifecycle": lifecycle,
            "reviewers": [u["login"] for u in pr.get("requested_reviewers", [])],
        })
        if cache is not None and key:
            cache[str(pr["number"])] = {"key": key, "fetched": now, "record": records[-1]}
    return sorted(records, key=lambda x: (x["created_at"], x["number"]), reverse=True)


def escape_cell(value, limit=240):
    value = " ".join(str(value).split())
    if len(value) > limit:
        cut = value[:limit - 1]
        if not value[limit - 1].isspace() and " " in cut:
            # End on a whole word so that no word or link is left half-printed.
            cut = cut.rsplit(" ", 1)[0]
        value = cut.rstrip(" ,;:([") + "…"
    value = html.escape(value, quote=False)
    parts = URL.split(value)
    for index, part in enumerate(parts):
        # Odd items are bare URLs: an escaped underscore would become part of the link target.
        for char in ("\\", "|", "[", "]", "*", "`", "!") + (() if index % 2 else ("_",)):
            part = part.replace(char, "\\" + char)
        parts[index] = part
    return "".join(parts)


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if value else ""


def render(records, repository):
    root = f"https://github.com/{repository}"
    lines = ["# Proposal list", "", "<!-- Generated by scripts/sync_proposals.py. Do not edit rows manually. -->", "",
             "Automatically synchronized from proposal PRs, their proposal files, reviews and maintainer labels. All times are UTC. Closed and merged proposals remain listed.", "",
             f"[🏗️ Environment template]({root}/blob/main/proposals/templates/environment-proposal.md) · [🧪 Task template]({root}/blob/main/proposals/templates/task-proposal.md) · [📖 Submission guide]({root}/blob/main/CONTRIBUTING.md#start-with-a-proposal)", ""]
    pools = json.loads(Path(__file__).resolve().parents[1].joinpath(".github/review-policy.json").read_text())["reviewers"]
    active = [r for r in records if r["status"] not in {"Accepted", "Closed", "Draft"}]
    drafts = sum(r["status"] == "Draft" for r in records)
    awaiting = sum(r["review"] == "Awaiting review" for r in active)
    lines += ["## Reviewer distribution", "",
              f"**{len(active)} open non-draft proposals · {awaiting} awaiting initial review · {drafts} drafts.**", "",
              "| Track | Reviewer | Pending review requests |", "| :--- | :--- | ---: |"]
    for kind, users in pools.items():
        for user in users:
            count = sum(user in r["reviewers"] for r in active if r["track"] == kind)
            search = quote(f"is:pr is:open review-requested:{user}", safe="")
            lines.append(f"| {kind.title()} | [{user}]({root}/pulls?q={search}) | {count} |")
    lines += ["", "Counts show pending requests, not accepted contributions or lifetime review totals. Submitted reviews leave the pending queue; multiple reviewers on one PR count separately.", "",
              f"New proposals follow the [domain and author routing policy]({root}/blob/main/docs/review/reviewer-routing.md). Drafts wait for Ready for review, and existing manual assignments are preserved.", ""]
    for kind, icon, detail in [("environment", "🏗️", "Scope and app connections"), ("task", "🧪", "Personalization insight")]:
        rows = [x for x in records if x["track"] == kind]
        lines += [f"## {icon} {kind.title()} Track", "", f"**{len(rows)} proposals.**", "",
                  f"| Submitted (UTC) | PR / {'app or website' if kind == 'environment' else 'task title'} | Primary domain | {detail} | Progress | Review / reviewer | Environment v1 deadline (UTC) | Author | Merged (UTC) |",
                  "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
        for item in rows:
            number = int(item["number"])
            domain = escape_cell(item["primary"])
            if item["secondary"]:
                domain += "<br>Also: " + escape_cell(item["secondary"])
            description = escape_cell(item["synopsis"])
            if item["issue"]:
                description += "<br>Metadata: " + escape_cell(item["issue"])
            proposal = f"[#{number}]({root}/pull/{number}) · {escape_cell(item['title'], 120)}"
            if item["path"]:
                proposal += f"<br>[View changes]({root}/pull/{number}/files)"
            author = escape_cell(item["author"])
            state = item.get("lifecycle", {})
            reviewers = item.get("reviewers") or ([state["approval"]["by"]] if state.get("approval") else [])
            review = item["review"] + ("<br>" + ", ".join("@" + escape_cell(u) for u in reviewers) if reviewers else "")
            due = utc(state.get("environment_v1_due_at"))
            if due:
                try:
                    from .proposal_lifecycle import due_status
                except ImportError:
                    from proposal_lifecycle import due_status
                due += "<br>" + due_status(state, datetime.now(timezone.utc))
            cells = [utc(item["created_at"]), proposal, domain, description, item["status"], review, due,
                     f"[{author}](https://github.com/{quote(item['author'], safe='')})", utc(item["merged_at"])]
            lines.append("| " + " | ".join(cells) + " |")
        lines += ["", "No proposals submitted yet." if not rows else "", ""]
    lines += ["## How updates work", "",
              "- Submit Environment files to `proposals/environment/<slug>.md` and Task files to `proposals/task/<slug>.md` in your PR branch. Keep one proposal file per PR and preserve the template's field labels.",
              "- PR lifecycle and routing updates refresh the list. A trusted default-branch poll reads current reviews every 5 minutes, subject to GitHub scheduling delays; fork workflow approval is not needed for review synchronization. Domains and summaries come from the proposal file. Missing metadata is flagged for correction in the same PR.",
              "- Review results and maintainer stage labels are synchronized separately. Only a merged PR is Accepted. Closing without merging is Closed; plan approval keeps the PR open.",
              "- Environment v1 is due 14 calendar days after the first plan approval. Submission is subject to review; it is not acceptance. Only a maintainer can record a deadline extension with a reason.",
              "", f"[How to submit and track a proposal]({root}/blob/main/proposals/README.md)", ""]
    return "\n".join(lines)


def cache_fingerprint():
    # Any change to this script, the review policy or the domain list invalidates cached records.
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in (Path(__file__).resolve(), root / "scripts/review_identity.py", root / ".github/review-policy.json", root / "README.md"):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_cache(api, fingerprint):
    existing = api.contents(CACHE_PATH, INDEX_BRANCH)
    if not existing:
        return {}
    try:
        data = json.loads(decode_file(existing, 5_000_000))
    except (ValueError, UnicodeError):
        return {}
    if not isinstance(data, dict) or data.get("fingerprint") != fingerprint or not isinstance(data.get("records"), dict):
        return {}
    return data["records"]


def cache_content(cache, fingerprint):
    return json.dumps({"fingerprint": fingerprint, "records": cache}, sort_keys=True, separators=(",", ":")) + "\n"


def publish(api, branch, content, path=INDEX_PATH, message="Update proposal list"):
    if branch != INDEX_BRANCH:
        raise ValueError("Generated indexes may only be published to proposal-index, never main")
    for attempt in range(3):
        existing = api.contents(path, branch)
        if existing and decode_file(existing) == content:
            return False
        data = {"message": message, "content": base64.b64encode(content.encode()).decode(), "branch": branch}
        if existing:
            data["sha"] = existing["sha"]
        try:
            api.request(f"/repos/{api.repository}/contents/{path}", "PUT", data)
            return True
        except APIError as error:
            if error.status != 409 or attempt == 2:
                raise
    return False


def ensure_index_branch(api, default_branch):
    try:
        api.request(f"/repos/{api.repository}/git/ref/heads/{INDEX_BRANCH}")
    except APIError as error:
        if error.status != 404:
            raise
        base = api.request(f"/repos/{api.repository}/git/ref/heads/{quote(default_branch, safe='')}")
        try:
            api.request(f"/repos/{api.repository}/git/refs", "POST", {"ref": "refs/heads/" + INDEX_BRANCH, "sha": base["object"]["sha"]})
        except APIError as conflict:
            if conflict.status != 422:
                raise
            api.request(f"/repos/{api.repository}/git/ref/heads/{INDEX_BRANCH}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "MatrAIx-ai/Personal-Agents-Last-Exam"))
    parser.add_argument("--output", type=Path, default=Path(INDEX_PATH))
    parser.add_argument("--publish", action="store_true", help="Update only the generated index on the proposal-index branch")
    args = parser.parse_args()
    api = GitHub(args.repository, os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    branch = api.request(f"/repos/{api.repository}")["default_branch"]
    domains = domains_from_readme(Path(__file__).resolve().parents[1].joinpath("README.md").read_text())
    if args.publish:
        ensure_index_branch(api, branch)
        fingerprint = cache_fingerprint()
        cache = load_cache(api, fingerprint)
        reused = len(cache)
        records = collect(api, domains, branch, cache)
        content = render(records, args.repository)
        changed = publish(api, INDEX_BRANCH, content)
        publish(api, INDEX_BRANCH, cache_content(cache, fingerprint), CACHE_PATH, "Update proposal cache")
        print(f"Proposal index: {len(records)} records ({reused} cached before this run); {'updated' if changed else 'unchanged'}.")
    else:
        records = collect(api, domains, branch)
        content = render(records, args.repository)
        args.output.write_text(content)
        print(f"Preview written to {args.output}: {len(records)} proposals. GitHub was not modified.")


if __name__ == "__main__":
    try:
        main()
    except RateLimited as error:
        rate_limit_notice("Proposal sync", error)
        sys.exit(1)
    except (APIError, ValueError, RuntimeError) as error:
        print(f"Proposal sync failed: {error}", file=sys.stderr)
        sys.exit(1)
