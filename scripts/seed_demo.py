"""Seed a demo account with the 10 Phase 0 sample ideas as projects.

Creates (or reuses) ``demo@example.com`` and adds one project per idea in
``data/test_ideas/sample_ideas.md`` that the account does not have yet. With
``--understand`` it also runs classification + requirement extraction for each
(needs ``GROQ_API_KEY``). The password is printed once; change it after login.

Run with the backend virtualenv, from the repo root:

    backend/.venv/Scripts/python scripts/seed_demo.py [--understand]
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SAMPLES = ROOT / "data" / "test_ideas" / "sample_ideas.md"
DEMO_EMAIL = "demo@example.com"

sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")


def sample_ideas() -> list[tuple[str, str, str]]:
    ideas = []
    for line in SAMPLES.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            number, category, idea, _ = match.groups()
            ideas.append((number, category, idea))
    return ideas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--understand", action="store_true", help="run extraction (uses Groq)")
    args = parser.parse_args()

    from sqlalchemy import select

    from app.config import get_settings
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models.project import Project, ProjectVersion
    from app.models.user import User
    from app.services.nlp.pipeline import run_understanding

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            password = secrets.token_urlsafe(9)
            user = User(
                email=DEMO_EMAIL,
                password_hash=hash_password(password),
                full_name="Demo user",
                daily_token_limit=get_settings().daily_token_limit_per_user,
            )
            db.add(user)
            db.commit()
            print(f"created {DEMO_EMAIL} with password: {password}")
        else:
            print(f"reusing {DEMO_EMAIL}")

        existing = set(db.scalars(select(Project.title).where(Project.user_id == user.id)))
        for number, category, idea in sample_ideas():
            title = f"Sample {number}: {idea[:60].rstrip(' ,.')}"
            if title in existing:
                continue
            project = Project(
                user_id=user.id,
                title=title,
                # the vague idea has no category yet; extraction decides
                category="software" if category == "vague" else category,
                help_level="everything",
            )
            db.add(project)
            db.flush()
            version = ProjectVersion(project_id=project.id, version_no=1, idea_text=idea)
            db.add(version)
            db.flush()
            project.current_version_id = version.id
            db.commit()
            print(f"added  {title}")

            if args.understand:
                try:
                    print("       ", run_understanding(db, project.id))
                except Exception as exc:  # noqa: BLE001 - keep seeding the rest
                    print(f"        extraction failed: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
