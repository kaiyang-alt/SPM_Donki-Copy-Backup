"""Validate that required shared repository paths still exist."""

from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    ".gitignore",
    ".env.example",
    "requirements.txt",
    "pytest.ini",
    ".github/workflows/ci.yml",
    "app/app.py",
    "app/supabase_client.py",
    "scripts/project_health.py",
    "scripts/validate_docs.py",
    "scripts/validate_structure.py",
)

FORBIDDEN_PATHS = (
    "app1",
)

REQUIRED_DIRECTORIES = (
    ".github",
    ".github/workflows",
    "app",
    "app/routes",
    "app/services",
    "app/templates",
    "app/static",
    "docs",
    "docs/architecture",
    "docs/requirements",
    "docs/implementation",
    "docs/user-stories",
    "docs/test-cases",
    "docs/uml",
    "scripts",
    "tests",
)


def main() -> int:
    missing_files = [
        path for path in REQUIRED_FILES if not (REPOSITORY_ROOT / path).is_file()
    ]
    missing_directories = [
        path
        for path in REQUIRED_DIRECTORIES
        if not (REPOSITORY_ROOT / path).is_dir()
    ]
    forbidden_paths_present = [
        path for path in FORBIDDEN_PATHS if (REPOSITORY_ROOT / path).exists()
    ]

    if missing_files or missing_directories or forbidden_paths_present:
        for path in missing_files:
            print(f"FAIL | Missing required file: {path}")
        for path in missing_directories:
            print(f"FAIL | Missing required directory: {path}/")
        for path in forbidden_paths_present:
            print(f"FAIL | Retired duplicate path must not exist: {path}")
        print("FAIL | Repository structure validation")
        return 1

    print(
        "PASS | Repository structure validation "
        f"({len(REQUIRED_FILES)} files, {len(REQUIRED_DIRECTORIES)} directories, "
        f"{len(FORBIDDEN_PATHS)} retired path checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
