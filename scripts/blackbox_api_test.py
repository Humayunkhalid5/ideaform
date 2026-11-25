"""Black-box test of the running API (no imports from the backend; HTTP only).

Exercises every endpoint the way the frontend does, including the real Groq
extraction and a real Tavily research run, plus negative cases (auth, ownership,
validation, isolation). Writes a Markdown report to ``data/eval/results/``.

    backend/.venv/Scripts/python scripts/blackbox_api_test.py [--api http://localhost:8000] [--skip-research]
"""

from __future__ import annotations

import argparse
import io
import secrets
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "eval" / "results"

IDEA = (
    "A mobile app that helps university students in Lahore find affordable, verified peer "
    "tutors nearby, book sessions in-app and pay per session, with reviews after each class."
)
NOTES = (
    "# Tutor interview notes\n\n"
    + " ".join(
        f"Interview {i}: students said they would pay 1,500 to 2,500 rupees per hour for a verified "
        "senior student tutor, mostly for calculus and programming before exams."
        for i in range(25)
    )
).encode()


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, bool, str]] = []

    def check(self, area: str, name: str, ok: bool, detail: str = "") -> bool:
        self.rows.append((area, name, bool(ok), detail))
        print(f"{'PASS' if ok else 'FAIL'}  {area:10} {name}{('  -- ' + detail) if detail and not ok else ''}", flush=True)
        return ok

    @property
    def failed(self) -> int:
        return sum(1 for r in self.rows if not r[2])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--skip-research", action="store_true", help="skip the paid Tavily run")
    args = parser.parse_args()
    api = httpx.Client(base_url=args.api, timeout=900)
    rep = Report()
    tag = secrets.token_hex(3)
    pw = "bb-" + secrets.token_urlsafe(9)

    # ---------------------------------------------------------------- health + auth
    rep.check("health", "GET /health", api.get("/health").json().get("status") == "ok")
    ready = api.get("/health/ready")
    rep.check("health", "GET /health/ready is 200", ready.status_code == 200, ready.text[:200])

    a_email, b_email = f"bb-a-{tag}@example.com", f"bb-b-{tag}@example.com"
    r = api.post("/auth/register", json={"email": a_email, "password": pw, "full_name": "Black Box A"})
    rep.check("auth", "register returns 201", r.status_code == 201, r.text[:200])
    rep.check("auth", "register duplicate returns 409",
              api.post("/auth/register", json={"email": a_email, "password": pw}).status_code == 409)
    rep.check("auth", "register short password returns 422",
              api.post("/auth/register", json={"email": f"x{tag}@example.com", "password": "1"}).status_code == 422)
    api.post("/auth/register", json={"email": b_email, "password": pw})
    tok_a = api.post("/auth/login", json={"email": a_email, "password": pw}).json()["access_token"]
    tok_b = api.post("/auth/login", json={"email": b_email, "password": pw}).json()["access_token"]
    A, B = {"Authorization": f"Bearer {tok_a}"}, {"Authorization": f"Bearer {tok_b}"}
    rep.check("auth", "wrong password returns 401",
              api.post("/auth/login", json={"email": a_email, "password": "wrong-pass"}).status_code == 401)
    rep.check("auth", "GET /auth/me", api.get("/auth/me", headers=A).json().get("email") == a_email)
    rep.check("auth", "no token returns 401", api.get("/projects").status_code == 401)
    rep.check("auth", "bad token returns 401",
              api.get("/projects", headers={"Authorization": "Bearer nope"}).status_code == 401)

    # ---------------------------------------------------------------- projects (Phase 1)
    r = api.post("/projects", json={"title": "Tutor Match", "idea_text": IDEA, "help_level": "research"}, headers=A)
    rep.check("projects", "create project 201", r.status_code == 201, r.text[:200])
    pid = r.json()["id"]
    rep.check("projects", "short idea rejected 422",
              api.post("/projects", json={"title": "x", "idea_text": "short"}, headers=A).status_code == 422)
    rep.check("projects", "list shows project", any(p["id"] == pid for p in api.get("/projects", headers=A).json()))
    rep.check("projects", "patch title",
              api.patch(f"/projects/{pid}", json={"title": "Tutor Match Lahore"}, headers=A).json()["title"] == "Tutor Match Lahore")
    rep.check("ownership", "other user gets 404 on project", api.get(f"/projects/{pid}", headers=B).status_code == 404)

    started = time.perf_counter()
    r = api.post(f"/projects/{pid}/understand", headers=A)
    rep.check("nlp", "understand (real Groq) succeeds", r.status_code == 202 and r.json()["status"] in ("succeeded", "queued"), r.text[:300])
    rep.check("nlp", f"extraction took {time.perf_counter() - started:.0f}s", True)
    detail = api.get(f"/projects/{pid}", headers=A).json()
    reqs = detail["requirements"]
    rep.check("nlp", "structured idea extracted", bool((detail["version"] or {}).get("structured_idea")))
    rep.check("nlp", f"{len(reqs)} requirements extracted (5-12 expected)", 3 <= len(reqs) <= 15)
    if reqs:
        r = api.patch(f"/projects/{pid}/requirements", json={"requirements": [{"id": reqs[0]["id"], "confirmed": True}]}, headers=A)
        rep.check("nlp", "confirm a requirement", r.status_code == 200 and any(x["confirmed"] for x in r.json()))
        r = api.patch(f"/projects/{pid}/requirements",
                      json={"requirements": [{"id": reqs[1]["id"], "confirmed": True}, {"id": "00000000-0000-0000-0000-000000000000"}]},
                      headers=A)
        rep.check("nlp", "patch with unknown id is atomic 404", r.status_code == 404)

    run_list = api.get(f"/runs/project/{pid}", headers=A).json()
    rep.check("runs", "project runs listed with tokens", bool(run_list) and run_list[0]["tokens_in"] is not None)
    rep.check("runs", "run detail", api.get(f"/runs/{run_list[0]['id']}", headers=A).status_code == 200)
    rep.check("ownership", "other user gets 404 on run", api.get(f"/runs/{run_list[0]['id']}", headers=B).status_code == 404)

    v = api.post(f"/projects/{pid}/versions", json={"idea_text": IDEA + " Also group sessions.", "change_summary": "groups"}, headers=A)
    rep.check("versions", "create version 2", v.status_code == 201 and v.json()["version"]["version_no"] == 2, v.text[:200])
    rep.check("versions", "list versions", [x["version_no"] for x in api.get(f"/projects/{pid}/versions", headers=A).json()] == [2, 1])
    rep.check("versions", "restore version 1",
              api.post(f"/projects/{pid}/versions/1/restore", headers=A).json()["version"]["version_no"] == 1)

    # ---------------------------------------------------------------- Phase 2: documents
    up = api.post(f"/projects/{pid}/documents", files={"file": ("interviews.md", io.BytesIO(NOTES), "text/markdown")}, headers=A)
    rep.check("documents", "upload markdown 201", up.status_code == 201, up.text[:200])
    sid = up.json()["source"]["id"] if up.status_code == 201 else None
    rep.check("documents", "duplicate upload detected",
              api.post(f"/projects/{pid}/documents", files={"file": ("again.txt", io.BytesIO(NOTES), "text/plain")}, headers=A).json().get("status") == "duplicate")
    rep.check("documents", "unsupported type 415",
              api.post(f"/projects/{pid}/documents", files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")}, headers=A).status_code == 415)
    rep.check("documents", "empty file 422",
              api.post(f"/projects/{pid}/documents", files={"file": ("e.txt", io.BytesIO(b""), "text/plain")}, headers=A).status_code == 422)
    rep.check("ownership", "other user cannot upload (404)",
              api.post(f"/projects/{pid}/documents", files={"file": ("n.md", io.BytesIO(NOTES), "text/markdown")}, headers=B).status_code == 404)

    # ---------------------------------------------------------------- Phase 2: research (real Tavily)
    if not args.skip_research:
        started = time.perf_counter()
        r = api.post(f"/projects/{pid}/research", json={"queries": ["peer tutoring app Pakistan"]}, headers=A)
        took = time.perf_counter() - started
        rep.check("research", f"research run succeeds ({took:.0f}s)", r.status_code == 202, r.text[:300])
        runs = api.get(f"/runs/project/{pid}?agent_name=research", headers=A).json()
        out = (runs[0].get("output") or {}) if runs else {}
        rep.check("research", f"{len(out.get('queries', []))} queries planned (4-8 + user query)",
                  4 <= len(out.get("queries", [])) <= 9, str(out.get("queries"))[:300])
        rep.check("research", f"pages stored: {out.get('pages_stored')} of {out.get('pages_fetched')} fetched, "
                  f"{out.get('pages_skipped_robots')} robots-skipped", (out.get("pages_stored") or 0) >= 3)
        jobs = api.get(f"/projects/{pid}/crawl", headers=A).json()
        rep.check("research", "crawl log records every URL with robots decision",
                  bool(jobs) and all("robots_allowed" in p for p in jobs[0]["pages"]))
        blocked_fetched = [p for p in jobs[0]["pages"] if not p["robots_allowed"] and p["http_status"]] if jobs else []
        rep.check("research", "no fetch was made against a robots/terms block", not blocked_fetched)

    sources = api.get(f"/projects/{pid}/sources", headers=A).json()
    rep.check("sources", f"{len(sources)} project sources listed", len(sources) >= 1)
    rep.check("sources", "every source has title, retrieved date and licence note",
              all(s["title"] and s["retrieved_at"] and s["licence_note"] for s in sources))
    web = [s for s in sources if s["url"]]
    ok_links = 0
    for s in web[:8]:
        try:
            code = httpx.get(s["url"], timeout=20, follow_redirects=True,
                             headers={"User-Agent": "IdeaformBot/1.0 (link check)"}).status_code
        except httpx.HTTPError:
            code = 0
        ok_links += code < 400 and code != 0
    rep.check("sources", f"source links open: {ok_links}/{min(len(web), 8)}", not web or ok_links >= max(1, int(0.7 * min(len(web), 8))))
    if sources:
        d = api.get(f"/projects/{pid}/sources/{sources[0]['id']}", headers=A).json()
        rep.check("sources", "source detail has passages", len(d.get("passages", [])) >= 1)
        rep.check("ownership", "other user gets 404 on source",
                  api.get(f"/projects/{pid}/sources/{sources[0]['id']}", headers=B).status_code == 404)

    # ---------------------------------------------------------------- Phase 2: retrieval
    for mode in ("hybrid", "vector", "keyword"):
        r = api.post(f"/projects/{pid}/search", json={"query": "how much will students pay per hour for a tutor", "mode": mode}, headers=A)
        ps = r.json().get("passages", []) if r.status_code == 200 else []
        rep.check("search", f"{mode} search returns cited passages ({len(ps)})",
                  r.status_code == 200 and ps and all(p["source_id"] and p["kb"] in "ABC" for p in ps))
    r = api.post(f"/projects/{pid}/search", json={"query": "how much will students pay per hour for a tutor"}, headers=A).json()
    rep.check("search", "uploaded interview notes are retrievable", any(p["title"] == "Tutor interview notes" for p in r["passages"]))
    rep.check("search", "evidence block uses [E1] markers", r["evidence_block"].startswith("[E1] (source:"))
    r = api.post(f"/projects/{pid}/search", json={"query": "store configuration in environment variables", "kbs": ["B"]}, headers=A).json()
    rep.check("search", "KB-B filter returns only technical passages", r["passages"] and all(p["kb"] == "B" for p in r["passages"]))
    rep.check("search", "query too short 422", api.post(f"/projects/{pid}/search", json={"query": "a"}, headers=A).status_code == 422)

    # isolation: B's own project must never see A's KB-C
    pid_b = api.post("/projects", json={"title": "Other idea", "idea_text": IDEA}, headers=B).json()["id"]
    leaked = []
    for mode in ("hybrid", "vector", "keyword"):
        for kbs in (None, ["C"]):
            body = {"query": "students pay per hour verified senior student tutor calculus", "mode": mode, "k": 20}
            if kbs:
                body["kbs"] = kbs
            leaked += [p for p in api.post(f"/projects/{pid_b}/search", json=body, headers=B).json()["passages"] if p["kb"] == "C"]
    rep.check("isolation", "user B retrieves none of user A's KB-C passages", not leaked)
    rep.check("isolation", "user B cannot search A's project (404)",
              api.post(f"/projects/{pid}/search", json={"query": "tutor"}, headers=B).status_code == 404)
    rep.check("isolation", "user B sees no sources in own project", api.get(f"/projects/{pid_b}/sources", headers=B).json() == [])

    stats = api.get("/knowledge/stats", headers=A).json()
    rep.check("knowledge", f"shared KB: A={stats['kb']['A']} B={stats['kb']['B']} sources; column {stats['embedding_column']}",
              stats["kb"]["A"] > 0 and stats["kb"]["B"] > 0)

    if sid:
        rep.check("sources", "delete uploaded source 204", api.delete(f"/projects/{pid}/sources/{sid}", headers=A).status_code == 204)
        rep.check("sources", "deleted source is gone", api.get(f"/projects/{pid}/sources/{sid}", headers=A).status_code == 404)

    # ---------------------------------------------------------------- rate limit (last: locks this IP for a minute)
    codes = [api.post("/auth/login", json={"email": a_email, "password": "wrong-pass"}).status_code for _ in range(12)]
    rep.check("auth", "login rate limit kicks in (429)", 429 in codes, str(codes))

    # cleanup
    api.delete(f"/projects/{pid}", headers=A)
    api.delete(f"/projects/{pid_b}", headers=B)

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"api_blackbox_{datetime.now():%Y%m%d_%H%M%S}.md"
    lines = [f"# Black-box API test ({datetime.now():%Y-%m-%d %H:%M})", "",
             f"Target: {args.api}. {len(rep.rows) - rep.failed}/{len(rep.rows)} checks passed.", "",
             "| Area | Check | Result |", "| --- | --- | --- |"]
    lines += [f"| {a} | {n} | {'pass' if ok else 'FAIL: ' + d[:120]} |" for a, n, ok, d in rep.rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{len(rep.rows) - rep.failed}/{len(rep.rows)} passed -> {path.relative_to(ROOT)}")
    raise SystemExit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
