#!/usr/bin/env python3
"""ErrorLens Code Audit Tool"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    category: str          # e.g. "F01"
    severity: str          # high / medium / low
    file: str
    line: int
    message: str
    context: str = ""
    suggestion: str = ""
    category_name: str = ""


# ---------------------------------------------------------------------------
# Checker base
# ---------------------------------------------------------------------------

SKIP_DIRS = {"node_modules", "dist", ".git", "__pycache__", ".vite", "venv", ".pytest_cache"}


class Checker:
    code: str = ""
    name: str = ""
    severity: str = "low"
    extensions: tuple[str, ...] = ()

    def applies_to(self, filepath: str) -> bool:
        return filepath.endswith(self.extensions)

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        return []

    def _make_context(self, lines: list[str], lineno: int, radius: int = 1) -> str:
        start = max(0, lineno - radius)
        end = min(len(lines), lineno + radius + 1)
        return "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))


# ---------------------------------------------------------------------------
# Frontend checkers
# ---------------------------------------------------------------------------

class EmojiChecker(Checker):
    code = "F01"
    name = "EmojiChecker"
    severity = "high"
    extensions = (".vue", ".js")

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            for ch in line:
                cp = ord(ch)
                if (0x1F000 <= cp <= 0x1FFFF) or (0x2600 <= cp <= 0x27BF):
                    findings.append(Finding(
                        category=self.code, severity=self.severity,
                        file=filepath, line=i + 1,
                        message=f"Emoji Unicode character U+{cp:04X} found",
                        context=self._make_context(lines, i),
                        suggestion="Use emoji component or named icon instead of raw Unicode",
                        category_name=self.name,
                    ))
                    break  # one finding per line
        return findings


class HardcodedColorsChecker(Checker):
    code = "F02"
    name = "HardcodedColorsChecker"
    severity = "high"
    extensions = (".vue",)
    HEX_RE = re.compile(r"(?<!['\"\-])#([0-9a-fA-F]{3,8})\b")

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        in_style = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("<style"):
                in_style = True
                continue
            if stripped.startswith("</style"):
                in_style = False
                continue
            if not in_style:
                continue
            if "var(--" in line:
                continue
            if self.HEX_RE.search(line):
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message="Hardcoded hex color in <style> block",
                    context=self._make_context(lines, i),
                    suggestion="Use CSS variable (var(--color-*)) or theme token",
                    category_name=self.name,
                ))
        return findings


class DirectApiInComponentChecker(Checker):
    code = "F03"
    name = "DirectApiInComponentChecker"
    severity = "high"
    extensions = (".vue",)
    API_RE = re.compile(r"import\s*\{[^}]*Api[^}]*\}\s*from\s*['\"]@/services/api['\"]")

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            if self.API_RE.search(line):
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message="Direct API import in .vue component",
                    context=self._make_context(lines, i),
                    suggestion="Use a composable or store to call API instead of importing directly",
                    category_name=self.name,
                ))
        return findings


class LocalProjectFetchChecker(Checker):
    code = "F04"
    name = "LocalProjectFetchChecker"
    severity = "high"
    extensions = (".vue",)
    FETCH_RE = re.compile(r"projectsApi\.list\(\)")

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        # Only check files under views/
        norm = filepath.replace("\\", "/")
        if "/views/" not in norm:
            return findings
        for i, line in enumerate(lines):
            if self.FETCH_RE.search(line):
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message="Local projectsApi.list() call in views/",
                    context=self._make_context(lines, i),
                    suggestion="Use project store or composable for project fetching",
                    category_name=self.name,
                ))
        return findings


class LargeVueFileChecker(Checker):
    code = "F05"
    name = "LargeVueFileChecker"
    severity = "medium"
    extensions = (".vue",)

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        if len(lines) > 500:
            return [Finding(
                category=self.code, severity=self.severity,
                file=filepath, line=len(lines),
                message=f"Large Vue file: {len(lines)} lines (>500)",
                suggestion="Split into smaller components",
                category_name=self.name,
            )]
        return []


class InlineStyleChecker(Checker):
    code = "F06"
    name = "InlineStyleChecker"
    severity = "medium"
    extensions = (".vue",)
    STYLE_RE = re.compile(r'style=["\'].*?(#[0-9a-fA-F]{3,8}|rgb\()', re.IGNORECASE)

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            if self.STYLE_RE.search(line):
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message="Inline style with hardcoded color",
                    context=self._make_context(lines, i),
                    suggestion="Move color to CSS class with theme variable",
                    category_name=self.name,
                ))
        return findings


class LegacyStoreChecker(Checker):
    code = "F07"
    name = "LegacyStoreChecker"
    severity = "medium"
    extensions = (".vue", ".js", ".ts")
    LEGACY_RE = re.compile(r"(useTasksStore|useTestCasesStore|useTestPlansStore)")

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        norm = filepath.replace("\\", "/")
        if "/qa/" not in norm and "/issues/" not in norm:
            return []
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            m = self.LEGACY_RE.search(line)
            if m:
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message=f"Legacy store usage: {m.group(1)}",
                    context=self._make_context(lines, i),
                    suggestion="Migrate to new domain-specific store",
                    category_name=self.name,
                ))
        return findings


class ConsoleLogChecker(Checker):
    code = "F08"
    name = "ConsoleLogChecker"
    severity = "low"
    extensions = (".vue", ".js", ".ts")
    CONSOLE_RE = re.compile(r"console\.(log|debug|warn)\s*\(")

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            if self.CONSOLE_RE.search(line):
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message="console.log/debug/warn statement",
                    context=self._make_context(lines, i),
                    suggestion="Remove or replace with proper logger",
                    category_name=self.name,
                ))
        return findings


# ---------------------------------------------------------------------------
# Backend checkers
# ---------------------------------------------------------------------------

class BareExceptChecker(Checker):
    code = "B01"
    name = "BareExceptChecker"
    severity = "high"
    extensions = (".py",)
    BARE_RE = re.compile(r"^\s*except\s*:\s*$")

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            if self.BARE_RE.match(line):
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message="Bare except clause",
                    context=self._make_context(lines, i),
                    suggestion="Catch specific exception type (e.g. except ValueError:)",
                    category_name=self.name,
                ))
        return findings


class HttpExceptionInServiceChecker(Checker):
    code = "B02"
    name = "HttpExceptionInServiceChecker"
    severity = "high"
    extensions = (".py",)
    HTTP_RE = re.compile(r"HTTPException")

    def applies_to(self, filepath: str) -> bool:
        norm = filepath.replace("\\", "/")
        return filepath.endswith(".py") and "/services/" in norm

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            if self.HTTP_RE.search(line):
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message="HTTPException used in service layer",
                    context=self._make_context(lines, i),
                    suggestion="Raise domain exception; let router handle HTTP mapping",
                    category_name=self.name,
                ))
        return findings


class DirectSqlInServiceChecker(Checker):
    code = "B03"
    name = "DirectSqlInServiceChecker"
    severity = "high"
    extensions = (".py",)
    SQL_RE = re.compile(r"await\s+db\.execute\s*\(\s*select\s*\(")

    def applies_to(self, filepath: str) -> bool:
        norm = filepath.replace("\\", "/")
        return filepath.endswith(".py") and "/services/" in norm

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            if self.SQL_RE.search(line):
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message="Direct SQL query in service layer",
                    context=self._make_context(lines, i),
                    suggestion="Move query to repository layer",
                    category_name=self.name,
                ))
        return findings


class MissingTypeHintsChecker(Checker):
    code = "B04"
    name = "MissingTypeHintsChecker"
    severity = "low"
    extensions = (".py",)
    DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+\w+\s*\(")

    def applies_to(self, filepath: str) -> bool:
        norm = filepath.replace("\\", "/")
        return filepath.endswith(".py") and ("/services/" in norm or "/repositories/" in norm)

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            if self.DEF_RE.search(line) and "->" not in line:
                # Check next lines too (multi-line def)
                block = line
                for j in range(i + 1, min(i + 5, len(lines))):
                    block += lines[j]
                    if ")" in lines[j]:
                        break
                if "->" not in block:
                    findings.append(Finding(
                        category=self.code, severity=self.severity,
                        file=filepath, line=i + 1,
                        message="Function missing return type hint",
                        context=self._make_context(lines, i),
                        suggestion="Add -> ReturnType annotation",
                        category_name=self.name,
                    ))
        return findings


class LargePythonFileChecker(Checker):
    code = "B05"
    name = "LargePythonFileChecker"
    severity = "medium"
    extensions = (".py",)

    def applies_to(self, filepath: str) -> bool:
        norm = filepath.replace("\\", "/")
        return filepath.endswith(".py") and "/backend/" in norm

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        if len(lines) > 500:
            return [Finding(
                category=self.code, severity=self.severity,
                file=filepath, line=len(lines),
                message=f"Large Python file: {len(lines)} lines (>500)",
                suggestion="Split into smaller modules",
                category_name=self.name,
            )]
        return []


# ---------------------------------------------------------------------------
# General checkers
# ---------------------------------------------------------------------------

class MissingClaudeMdChecker(Checker):
    code = "G01"
    name = "MissingClaudeMdChecker"
    severity = "medium"

    def scan_directories(self, root: str) -> list[Finding]:
        findings: list[Finding] = []
        check_roots = [
            os.path.join(root, "backend", "app"),
            os.path.join(root, "dashboard-vue", "src"),
        ]
        for base in check_roots:
            if not os.path.isdir(base):
                continue
            for entry in sorted(os.listdir(base)):
                dirpath = os.path.join(base, entry)
                if os.path.isdir(dirpath) and entry not in SKIP_DIRS:
                    claude_md = os.path.join(dirpath, "CLAUDE.md")
                    if not os.path.isfile(claude_md):
                        rel = os.path.relpath(dirpath, root)
                        findings.append(Finding(
                            category=self.code, severity=self.severity,
                            file=rel, line=0,
                            message=f"Directory missing CLAUDE.md: {rel}",
                            suggestion="Add CLAUDE.md with module purpose and conventions",
                            category_name=self.name,
                        ))
        return findings


class TodoFixmeChecker(Checker):
    code = "G02"
    name = "TodoFixmeChecker"
    severity = "low"
    extensions = (".py", ".js", ".ts", ".vue")
    TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)

    def check_file(self, filepath: str, lines: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(lines):
            m = self.TODO_RE.search(line)
            if m:
                findings.append(Finding(
                    category=self.code, severity=self.severity,
                    file=filepath, line=i + 1,
                    message=f"{m.group(1).upper()} comment found",
                    context=self._make_context(lines, i),
                    suggestion="Resolve or create a tracked issue",
                    category_name=self.name,
                ))
        return findings


# ---------------------------------------------------------------------------
# AuditRunner
# ---------------------------------------------------------------------------

ALL_CHECKERS: list[Checker] = [
    EmojiChecker(),
    HardcodedColorsChecker(),
    DirectApiInComponentChecker(),
    LocalProjectFetchChecker(),
    LargeVueFileChecker(),
    InlineStyleChecker(),
    LegacyStoreChecker(),
    ConsoleLogChecker(),
    BareExceptChecker(),
    HttpExceptionInServiceChecker(),
    DirectSqlInServiceChecker(),
    MissingTypeHintsChecker(),
    LargePythonFileChecker(),
    MissingClaudeMdChecker(),
    TodoFixmeChecker(),
]


class AuditRunner:
    def __init__(self, root: str, category: Optional[str] = None, severity: Optional[str] = None):
        self.root = os.path.abspath(root)
        self.category = category
        self.severity = severity

    def run(self) -> list[Finding]:
        findings: list[Finding] = []

        # G01 — directory-level check
        for checker in ALL_CHECKERS:
            if isinstance(checker, MissingClaudeMdChecker):
                if self.category and not self.category.upper().startswith("G"):
                    continue
                findings.extend(checker.scan_directories(self.root))

        # File-level checks
        file_checkers = [c for c in ALL_CHECKERS if not isinstance(c, MissingClaudeMdChecker)]

        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                filepath = os.path.join(dirpath, fname)
                rel = os.path.relpath(filepath, self.root)
                for checker in file_checkers:
                    if self.category and not checker.code.upper().startswith(self.category.upper()):
                        continue
                    if not checker.applies_to(filepath):
                        continue
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.read().splitlines()
                    except (OSError, PermissionError):
                        continue
                    findings.extend(checker.check_file(rel, lines))

        # Filter by severity
        if self.severity:
            sev = self.severity.lower()
            findings = [f for f in findings if f.severity == sev]

        # Sort: high → medium → low, then file, then line
        order = {"high": 0, "medium": 1, "low": 2}
        findings.sort(key=lambda f: (order.get(f.severity, 9), f.file, f.line))
        return findings


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def write_md_report(findings: list[Finding], output_path: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    high = sum(1 for f in findings if f.severity == "high")
    med = sum(1 for f in findings if f.severity == "medium")
    low = sum(1 for f in findings if f.severity == "low")

    lines: list[str] = []
    lines.append("# ErrorLens Audit Report")
    lines.append(f"\nGenerated: {now}\n")
    lines.append("## Summary\n")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| HIGH     | {high}  |")
    lines.append(f"| MEDIUM   | {med}  |")
    lines.append(f"| LOW      | {low}  |")
    lines.append(f"| **Total**| **{len(findings)}** |")
    lines.append("")

    # Group by category
    cats: dict[str, list[Finding]] = {}
    for f in findings:
        key = f"{f.category} {f.category_name}"
        cats.setdefault(key, []).append(f)

    # Findings by severity
    for sev_label in ("HIGH", "MEDIUM", "LOW"):
        sev_findings = [f for f in findings if f.severity == sev_label.lower()]
        if not sev_findings:
            continue
        lines.append(f"## {sev_label} Severity\n")
        for f in sev_findings:
            lines.append(f"- **[{f.category}]** `{f.file}:{f.line}` — {f.message}")
            if f.suggestion:
                lines.append(f"  - Suggestion: {f.suggestion}")
        lines.append("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def write_json_report(findings: list[Finding], output_path: str) -> None:
    data = {
        "generated": datetime.now().isoformat(),
        "total": len(findings),
        "by_severity": {
            "high": sum(1 for f in findings if f.severity == "high"),
            "medium": sum(1 for f in findings if f.severity == "medium"),
            "low": sum(1 for f in findings if f.severity == "low"),
        },
        "findings": [asdict(f) for f in findings],
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Baseline diff
# ---------------------------------------------------------------------------

def load_baseline(path: str) -> set[str]:
    """Load baseline JSON and return set of finding keys for diff."""
    if not os.path.isfile(path):
        return set()
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    keys = set()
    for f in data.get("findings", []):
        key = f"{f['category']}|{f['file']}|{f['line']}|{f['message']}"
        keys.add(key)
    return keys


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="ErrorLens Code Audit Tool")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--category", default=None, help="Filter by category prefix (F, B, G)")
    parser.add_argument("--severity", default=None, help="Filter by severity (high, medium, low)")
    parser.add_argument("--output", default=None, help="Output directory for reports")
    parser.add_argument("--diff", default=None, help="Path to baseline JSON for diff")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    output_dir = args.output or os.path.join(root, ".claude")

    runner = AuditRunner(root, category=args.category, severity=args.severity)
    findings = runner.run()

    # Diff against baseline
    if args.diff:
        baseline = load_baseline(args.diff)
        new_findings = []
        for f in findings:
            key = f"{f.category}|{f.file}|{f.line}|{f.message}"
            if key not in baseline:
                new_findings.append(f)
        print(f"Baseline: {len(baseline)} findings, Current: {len(findings)}, New: {len(new_findings)}")
        findings = new_findings

    md_path = os.path.join(output_dir, "audit-report.md")
    json_path = os.path.join(output_dir, "audit-report.json")

    write_md_report(findings, md_path)
    write_json_report(findings, json_path)

    high = sum(1 for f in findings if f.severity == "high")
    med = sum(1 for f in findings if f.severity == "medium")
    low = sum(1 for f in findings if f.severity == "low")

    print(f"Audit complete: {len(findings)} findings (HIGH={high}, MEDIUM={med}, LOW={low})")
    print(f"  MD report:   {md_path}")
    print(f"  JSON report: {json_path}")

    if high > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
