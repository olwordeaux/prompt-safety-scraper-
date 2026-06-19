#!/usr/bin/env python3
"""
scrape_prompt_repos.py

Clones a set of GitHub repositories known to contain system prompts and AI‑tool
instructions, then scans all Markdown (and plain text) files for keywords
related to safe code generation (sandboxing, banned functions, safetensors, etc.)
and stores the results in a SQLite database.

Usage:
    python scrape_prompt_repos.py
"""

import re
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
REPOS = [
    "https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools.git",
    "https://github.com/LouisShark/chatgpt_system_prompt.git",
    "https://github.com/mustvlad/ChatGPT-System-Prompts.git",
    "https://github.com/linexjlin/GPTs.git",
    "https://github.com/Fonduelabs/ai-system-prompts.git",
    "https://github.com/greshake/llm-security.git",
    "https://github.com/dair-ai/Prompt-Engineering-Guide.git",
]

REPOS_DIR = Path("./repos")
REPOS_DIR.mkdir(exist_ok=True)

DB_PATH = Path("./prompt_snippets.db")

KEYWORDS = [
    r"sandbox",
    r"restricted environment",
    r"forbidden",
    r"code generation",
    r"eval\(\)",
    r"exec\(\)",
    r"open\(\)",
    r"safetensors",
    r"torch\.save",
    r"torch\.load",
    r"import os",
    r"import subprocess",
    r"__subclasses__",
    r"__globals__",
    r"getattr\(",
    r"setattr\(",
    r"whitelist",
    r"blacklist",
    r"never use",
    r"do not use",
    r"must not",
    r"prohibited",
]
KEYWORD_PATTERN = re.compile("|".join(KEYWORDS), re.IGNORECASE)

TARGET_EXTENSIONS = {".md", ".txt", ".markdown"}


# ------------------------------------------------------------
# Helper: clone a repository if not already present
# ------------------------------------------------------------
def clone_repo(url: str, target_dir: Path) -> bool:
    repo_name = url.split("/")[-1].replace(".git", "")
    local_path = target_dir / repo_name
    if local_path.exists():
        print(f"[✓] Already exists: {local_path}")
        return True
    print(f"[↓] Cloning {url} into {local_path}...")
    try:
        # The REPOS list is hardcoded and trusted, so we suppress S603/S607
        subprocess.run(  # noqa: S603
            ["git", "clone", "--depth", "1", url, str(local_path)],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        )
        print("    Clone successful.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[✗] Clone failed: {e.stderr.strip()}")
        if local_path.exists():
            shutil.rmtree(local_path, ignore_errors=True)
        return False


# ------------------------------------------------------------
# Database setup
# ------------------------------------------------------------
def init_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS snippets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            line_number INTEGER,
            line_content TEXT,
            context TEXT,
            scrape_date TEXT
        )
        """
    )
    conn.commit()
    return conn


# ------------------------------------------------------------
# Scanning and extraction
# ------------------------------------------------------------
def extract_context(lines, idx, window=2):
    start = max(0, idx - window)
    end = min(len(lines), idx + window + 1)
    context_lines = []
    for i in range(start, end):
        prefix = ">>" if i == idx else "  "
        context_lines.append(f"{prefix} L{i + 1}: {lines[i].rstrip()}")
    return "\n".join(context_lines)


def scan_repo(repo_path: Path, conn: sqlite3.Connection):
    repo_name = repo_path.name
    cur = conn.cursor()
    total_matches = 0

    for file_path in repo_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in TARGET_EXTENSIONS:
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    if KEYWORD_PATTERN.search(line):
                        context = extract_context(lines, i, window=2)
                        cur.execute(
                            "INSERT INTO snippets (repo_name, file_path, "
                            "line_number, line_content, context, scrape_date) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                repo_name,
                                str(file_path.relative_to(repo_path.parent)),
                                i + 1,
                                line.strip(),
                                context,
                                datetime.now().isoformat(),
                            ),
                        )
                        total_matches += 1
                if total_matches % 50 == 0:
                    conn.commit()
            except Exception as e:
                print(f"  [!] Error reading {file_path}: {e}")

    conn.commit()
    print(f"  → {repo_name}: {total_matches} matches found.")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    conn = init_db(DB_PATH)

    cloned_count = 0
    for url in REPOS:
        success = clone_repo(url, REPOS_DIR)
        if success:
            cloned_count += 1

    if cloned_count == 0:
        print("No repositories cloned. Exiting.")
        conn.close()
        return

    print(f"\nScanning {cloned_count} repositories for keywords...")
    for repo_path in sorted(REPOS_DIR.iterdir()):
        if repo_path.is_dir():
            scan_repo(repo_path, conn)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM snippets")
    total = cur.fetchone()[0]
    print(f"\n✓ Done. Total snippets stored: {total}")
    print(f"  Database: {DB_PATH.resolve()}")
    conn.close()


if __name__ == "__main__":
    main()
