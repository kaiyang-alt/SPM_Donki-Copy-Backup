"""Run the shared, non-destructive ConnectSphere project health checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_LOCATIONS = (
    Path("supabase/migrations"),
    Path("database/migrations"),
    Path("migrations"),
)


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPOSITORY_ROOT, text=True, check=False)


def capture_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def check_app_import() -> bool:
    if str(REPOSITORY_ROOT) not in sys.path:
        sys.path.insert(0, str(REPOSITORY_ROOT))

    try:
        from app.app import app
    except Exception as exc:
        print(f"FAIL | Production Flask app import: {exc}")
        return False

    if app is None:
        print("FAIL | Production Flask app import: app is not available")
        return False

    print("PASS | Production Flask app import")
    return True


def git_information() -> None:
    branch_result = capture_command(["git", "branch", "--show-current"])
    if branch_result.returncode == 0:
        branch = branch_result.stdout.strip() or "detached HEAD"
        print(f"INFO | Git branch: {branch}")
    else:
        print("INFO | Git branch: unavailable")

    status_result = capture_command(["git", "status", "--porcelain"])
    if status_result.returncode == 0:
        state = "clean" if not status_result.stdout.strip() else "dirty"
        print(f"INFO | Working tree: {state}")
    else:
        print("INFO | Working tree: unavailable")


def migration_information() -> None:
    versioned_locations = []
    unversioned_locations = []

    for relative_path in MIGRATION_LOCATIONS:
        directory = REPOSITORY_ROOT / relative_path
        if not directory.is_dir():
            continue

        tracked_result = capture_command(
            ["git", "ls-files", "--", relative_path.as_posix()]
        )
        if tracked_result.returncode == 0 and tracked_result.stdout.strip():
            versioned_locations.append(relative_path.as_posix())
        else:
            unversioned_locations.append(relative_path.as_posix())

    if versioned_locations:
        print(
            "INFO | Versioned database migrations: "
            + ", ".join(versioned_locations)
        )
    elif unversioned_locations:
        print(
            "INFO | Database migration directories exist but contain no versioned "
            "files: "
            + ", ".join(unversioned_locations)
        )
    else:
        print("INFO | Versioned database migrations: not found (informational only)")


def main() -> int:
    print("ConnectSphere Project Health")
    print("============================")
    print(f"INFO | Python: {sys.executable}")
    git_information()
    migration_information()

    app_import_passed = check_app_import()

    print("INFO | Running: python -m pytest", flush=True)
    pytest_result = run_command([sys.executable, "-m", "pytest"])
    pytest_passed = pytest_result.returncode == 0
    print(f"{'PASS' if pytest_passed else 'FAIL'} | Full regression suite")

    print("INFO | Running: python scripts/validate_docs.py", flush=True)
    docs_result = run_command([sys.executable, "scripts/validate_docs.py"])
    docs_passed = docs_result.returncode == 0
    print(f"{'PASS' if docs_passed else 'FAIL'} | Documentation validation")

    print("INFO | Running: python scripts/validate_structure.py", flush=True)
    structure_result = run_command(
        [sys.executable, "scripts/validate_structure.py"]
    )
    structure_passed = structure_result.returncode == 0
    print(
        f"{'PASS' if structure_passed else 'FAIL'} | Repository structure validation"
    )

    print("INFO | Running: git diff --check HEAD", flush=True)
    diff_result = run_command(["git", "diff", "--check", "HEAD"])
    diff_passed = diff_result.returncode == 0
    print(f"{'PASS' if diff_passed else 'FAIL'} | git diff --check HEAD")

    required_checks = {
        "Production Flask app import": app_import_passed,
        "Full regression suite": pytest_passed,
        "Documentation validation": docs_passed,
        "Repository structure validation": structure_passed,
        "git diff --check HEAD": diff_passed,
    }

    print("\nSummary")
    print("-------")
    for name, passed in required_checks.items():
        print(f"{'PASS' if passed else 'FAIL'} | {name}")

    all_required_checks_passed = all(required_checks.values())
    print(
        f"{'PASS' if all_required_checks_passed else 'FAIL'} | Overall project health"
    )
    return 0 if all_required_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
