"""Validate links between user stories and functional test specifications."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
USER_STORY_DIRECTORY = REPOSITORY_ROOT / "docs" / "user-stories"
TEST_CASE_DIRECTORY = (REPOSITORY_ROOT / "docs" / "test-cases").resolve()

EXCLUDED_TEST_CASE_FILES = {
    (TEST_CASE_DIRECTORY / "README.md").resolve(),
    (TEST_CASE_DIRECTORY / "functional-test-case-prompt.md").resolve(),
}

MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
RAW_TEST_CASE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:docs/test-cases/|\.\./test-cases/)[A-Za-z0-9_./-]+\.md)"
)


def clean_link_target(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    return unquote(target).strip()


def is_external_or_anchor(target: str) -> bool:
    if not target or target.startswith("#"):
        return True
    parsed = urlparse(target)
    return bool(parsed.scheme or parsed.netloc)


def looks_like_inline_path(value: str) -> bool:
    value = value.strip()
    return value.startswith(("docs/", "../", "./", "/")) and bool(
        Path(value.split("#", 1)[0]).suffix
    )


def explicit_local_targets(content: str) -> list[str]:
    targets = []

    for match in MARKDOWN_LINK_PATTERN.finditer(content):
        target = clean_link_target(match.group(1))
        if not is_external_or_anchor(target):
            targets.append(target)

    for match in INLINE_CODE_PATTERN.finditer(content):
        target = match.group(1).strip()
        if looks_like_inline_path(target):
            targets.append(target)

    targets.extend(match.group(1) for match in RAW_TEST_CASE_PATTERN.finditer(content))
    return list(dict.fromkeys(targets))


def resolve_local_target(story_file: Path, target: str) -> Path:
    path_text = target.split("#", 1)[0].split("?", 1)[0]
    if path_text.startswith("docs/"):
        return (REPOSITORY_ROOT / path_text).resolve()
    if path_text.startswith("/"):
        return (REPOSITORY_ROOT / path_text.lstrip("/")).resolve()
    return (story_file.parent / path_text).resolve()


def repository_relative(path: Path) -> str:
    try:
        return path.relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        return str(path)


def is_under_directory(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def validate_story(story_file: Path) -> tuple[bool, str]:
    try:
        content = story_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return False, f"could not read file: {exc}"

    targets = explicit_local_targets(content)
    resolved_targets = [
        (target, resolve_local_target(story_file, target)) for target in targets
    ]

    issues = []
    for target, resolved in resolved_targets:
        if not is_under_directory(resolved, REPOSITORY_ROOT):
            issues.append(f"local reference is outside repository: {target}")
        elif not resolved.exists():
            issues.append(f"referenced file does not exist: {target}")

    functional_candidates = [
        (target, resolved)
        for target, resolved in resolved_targets
        if resolved.suffix.lower() == ".md"
        and is_under_directory(resolved, TEST_CASE_DIRECTORY)
    ]

    valid_functional_references = []
    for target, resolved in functional_candidates:
        if resolved in EXCLUDED_TEST_CASE_FILES:
            issues.append(f"not a story test specification: {target}")
        elif resolved.exists():
            valid_functional_references.append(resolved)

    if not functional_candidates:
        issues.append("no explicit functional test reference")
    elif not valid_functional_references and not issues:
        issues.append("no valid functional test reference")

    if issues:
        return False, "; ".join(dict.fromkeys(issues))

    references = ", ".join(
        repository_relative(path) for path in dict.fromkeys(valid_functional_references)
    )
    return True, references


def main() -> int:
    story_files = sorted(
        path
        for path in USER_STORY_DIRECTORY.glob("*.md")
        if path.name != "README.md"
    )

    passed = 0
    failed = 0

    if not story_files:
        print("FAIL | No user story files found.")
        failed = 1

    for story_file in story_files:
        is_valid, detail = validate_story(story_file)
        if is_valid:
            passed += 1
            print(f"PASS | {story_file.name} -> {detail}")
        else:
            failed += 1
            print(f"FAIL | {story_file.name} -> {detail}")

    print("\nSummary")
    print("-------")
    print(f"User stories checked: {len(story_files)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Overall: {'PASS' if failed == 0 else 'FAIL'}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
