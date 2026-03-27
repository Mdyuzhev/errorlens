"""EVA v2.1 — static analyzer for test quality (Python port of eva-v2.js)."""

import io
import re
import zipfile
from dataclasses import asdict, dataclass, field

WEIGHTS = {
    "oracle": 0.30,
    "mutation": 0.25,
    "negative": 0.20,
    "edge": 0.15,
    "structure": 0.10,
}

GRADES = [
    {"min": 90, "grade": "S", "desc": "Отлично, эталонное качество"},
    {"min": 80, "grade": "A", "desc": "Очень хорошо"},
    {"min": 70, "grade": "B", "desc": "Хорошо, есть потенциал"},
    {"min": 60, "grade": "C", "desc": "Удовлетворительно"},
    {"min": 50, "grade": "D", "desc": "Слабо, требует доработки"},
    {"min": 0, "grade": "F", "desc": "Неудовлетворительно"},
]

# --- Matchers ---

PYTHON_STRONG = [
    r'assert.*==.*["\']',
    r"assert.*in \[",
    r"assert re\.match",
    r"assert len\(",
    r"assert.*>=\s*\d+",
    r"assert.*<=\s*\d+",
    r"assert isinstance\(",
]
PYTHON_MEDIUM = [
    r"assert.*is not None",
    r"assert.*is None",
    r"assert.*!=",
    r"assert.*in ",
]
PYTHON_WEAK = [
    r"assert True",
    r"assert response",
]

JAVA_STRONG = [
    r"matchesPattern\(",
    r"oneOf\(",
    r"greaterThanOrEqualTo\(",
    r"hasSize\(",
    r"containsString\(",
    r"equalTo\(",
    r"hasItem\(",
]
JAVA_MEDIUM = [
    r"notNullValue\(\)",
    r"isA\(",
    r"not\(",
]
JAVA_WEAK = [
    r"is\(",
    r"anything\(\)",
]

# --- Anti-patterns ---

PYTHON_ANTI = [
    (r"time\.sleep\(\d+\)", -10, "time.sleep with literal delay"),
    (r"except\s*:\s*pass", -15, "bare except: pass"),
    (r"def test_\w+\([^)]*\):\s*pass", -20, "empty test function"),
    (r"assert True$", -5, "assert True (meaningless)"),
    (r'password\s*=\s*["\'][^"\']+', -20, "hardcoded password"),
]
JAVA_ANTI = [
    (r"Thread\.sleep\(\d+\)", -10, "Thread.sleep with literal delay"),
    (r"catch\s*\([^)]+\)\s*\{\s*\}", -15, "empty catch block"),
    (r"@Test\s+public\s+void\s+\w+\s*\(\s*\)\s*\{\s*\}", -20, "empty test method"),
    (r"anything\(\)", -5, "anything() matcher (too weak)"),
]

BAD_NAMES = re.compile(r"^(test\d*|t\d+|test_\d+|foo|bar|temp)$")


@dataclass
class EvaFileStats:
    tests: int = 0
    strong: int = 0
    medium: int = 0
    weak: int = 0
    lines: int = 0
    lang: str = "python"


@dataclass
class EvaResult:
    version: str = "2.1"
    files: int = 0
    tests: int = 0
    strong: int = 0
    medium: int = 0
    weak: int = 0
    scores: dict = field(default_factory=dict)
    base_total: int = 0
    total_penalty: int = 0
    total: int = 0
    grade: str = "F"
    grade_desc: str = ""
    oracle_depth: int = 0
    negative_covered: int = 0
    negative_total: int = 6
    edge_covered: int = 0
    edge_total: int = 10
    anti_patterns: list = field(default_factory=list)
    copy_paste: dict = field(default_factory=dict)
    bad_naming: dict = field(default_factory=dict)
    compilation: dict = field(default_factory=dict)
    recommendations: list = field(default_factory=list)


class EvaService:
    """Static test-quality analyzer."""

    @staticmethod
    def _count_matchers(content: str, patterns: list[str]) -> int:
        total = 0
        for pat in patterns:
            total += len(re.findall(pat, content, re.MULTILINE))
        return total

    @staticmethod
    def _analyse_file(filename: str, content: str) -> EvaFileStats:
        lang = "java" if filename.endswith(".java") else "python"
        lines = content.splitlines()
        stats = EvaFileStats(lines=len(lines), lang=lang)

        if lang == "python":
            stats.tests = len(re.findall(r"def test_\w+", content))
            stats.strong = EvaService._count_matchers(content, PYTHON_STRONG)
            stats.medium = EvaService._count_matchers(content, PYTHON_MEDIUM)
            stats.weak = EvaService._count_matchers(content, PYTHON_WEAK)
        else:
            stats.tests = len(re.findall(r"@Test", content))
            stats.strong = EvaService._count_matchers(content, JAVA_STRONG)
            stats.medium = EvaService._count_matchers(content, JAVA_MEDIUM)
            stats.weak = EvaService._count_matchers(content, JAVA_WEAK)

        return stats

    @staticmethod
    def _detect_anti_patterns(
        filename: str, content: str, lang: str,
    ) -> list[dict]:
        patterns = PYTHON_ANTI if lang == "python" else JAVA_ANTI
        found: list[dict] = []
        for pat, penalty, desc in patterns:
            matches = re.findall(pat, content, re.MULTILINE)
            if matches:
                found.append({
                    "file": filename,
                    "pattern": desc,
                    "count": len(matches),
                    "penalty": penalty * len(matches),
                })
        return found

    @staticmethod
    def _detect_copy_paste(content: str) -> dict:
        nums = [int(m) for m in re.findall(r"test_\w+?(\d+)", content)]
        if len(nums) < 3:
            return {}
        nums.sort()
        seq_len = 1
        max_seq = 1
        for i in range(1, len(nums)):
            if nums[i] == nums[i - 1] + 1:
                seq_len += 1
                max_seq = max(max_seq, seq_len)
            else:
                seq_len = 1
        if max_seq >= 3:
            penalty = min(25, 15 + (max_seq - 3) * 5)
            return {
                "consecutive_tests": max_seq,
                "penalty": penalty,
                "hint": "Sequential numbered tests suggest copy-paste",
            }
        return {}

    @staticmethod
    def _detect_bad_naming(content: str, lang: str) -> dict:
        if lang == "python":
            names = re.findall(r"def (test_?\w*)\(", content)
        else:
            names = re.findall(r"void\s+(\w+)\s*\(", content)
        bad = [n for n in names if BAD_NAMES.match(n)]
        if bad:
            return {
                "names": bad,
                "count": len(bad),
                "penalty": len(bad) * 5,
            }
        return {}

    @staticmethod
    def _calc_grade(score: int) -> tuple[str, str]:
        for g in GRADES:
            if score >= g["min"]:
                return g["grade"], g["desc"]
        return "F", "Неудовлетворительно"

    @staticmethod
    def _build_recommendations(result: EvaResult) -> list[str]:
        recs: list[str] = []
        if result.scores.get("oracle", 0) < 60:
            recs.append("Усильте assert-ы: используйте точные сравнения вместо assert True")
        if result.scores.get("mutation", 0) < 50:
            recs.append("Добавьте больше strong-матчеров (assertEqual, exact match)")
        if result.negative_covered < 3:
            recs.append("Покройте негативные сценарии (невалидный ввод, граничные ошибки)")
        if result.edge_covered < 5:
            recs.append("Добавьте edge-case тесты (пустые значения, null, overflow)")
        if result.anti_patterns:
            recs.append("Устраните анти-паттерны: sleep, пустые тесты, захардкоженные пароли")
        if result.copy_paste:
            recs.append("Рефакторинг копипаста: параметризуйте тесты")
        return recs

    @staticmethod
    def analyse_zip(zip_bytes: bytes) -> EvaResult:
        """Analyse a ZIP archive of test files and return EVA score."""
        result = EvaResult()
        all_stats: list[EvaFileStats] = []
        all_anti: list[dict] = []
        all_content = ""
        primary_lang = "python"

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                if not (name.endswith(".py") or name.endswith(".java")):
                    continue
                try:
                    raw = zf.read(name)
                    content = raw.decode("utf-8", errors="replace")
                except (KeyError, UnicodeDecodeError):
                    continue

                stats = EvaService._analyse_file(name, content)
                if stats.tests == 0:
                    continue

                all_stats.append(stats)
                all_content += "\n" + content

                lang = stats.lang
                anti = EvaService._detect_anti_patterns(name, content, lang)
                all_anti.extend(anti)

        if not all_stats:
            result.compilation = {"ok": False, "error": "No test files found"}
            return result

        # Determine primary language
        java_count = sum(1 for s in all_stats if s.lang == "java")
        if java_count > len(all_stats) / 2:
            primary_lang = "java"

        # Aggregate stats
        result.files = len(all_stats)
        result.tests = sum(s.tests for s in all_stats)
        result.strong = sum(s.strong for s in all_stats)
        result.medium = sum(s.medium for s in all_stats)
        result.weak = sum(s.weak for s in all_stats)
        result.anti_patterns = all_anti
        result.compilation = {"ok": True}

        # Copy-paste & bad naming
        result.copy_paste = EvaService._detect_copy_paste(all_content)
        result.bad_naming = EvaService._detect_bad_naming(all_content, primary_lang)

        # Negative / edge heuristics
        neg_patterns = [
            r"invalid", r"error", r"fail", r"reject", r"denied", r"unauthorized",
        ]
        edge_patterns = [
            r"empty", r"null", r"none", r"zero", r"boundary", r"overflow",
            r"negative", r"max", r"min", r"special.?char",
        ]
        lower_content = all_content.lower()
        result.negative_covered = sum(
            1 for p in neg_patterns if re.search(p, lower_content)
        )
        result.edge_covered = sum(
            1 for p in edge_patterns if re.search(p, lower_content)
        )

        # --- Score calculation ---
        total_matchers = result.strong + result.medium + result.weak
        weighted = result.strong * 3 + result.medium * 2 + result.weak * 1
        total_lines = sum(s.lines for s in all_stats)
        density = total_matchers / max(result.tests, 1)
        density_bonus = min(20, density * 5)

        oracle = min(100, (weighted / max(total_matchers, 1)) * 33.3 + density_bonus)
        mutation = min(100, (result.strong * 4 + result.medium * 2)) * (
            1 + result.tests / 50
        )
        mutation = min(100, mutation)
        negative = (result.negative_covered / result.negative_total) * 100
        edge = (result.edge_covered / result.edge_total) * 100
        structure = 50
        if result.files > 1:
            structure += 20
        if result.tests > 5:
            structure += 15
        if density >= 2:
            structure += 15

        result.scores = {
            "oracle": round(oracle, 1),
            "mutation": round(mutation, 1),
            "negative": round(negative, 1),
            "edge": round(edge, 1),
            "structure": round(structure, 1),
        }
        result.oracle_depth = min(3, result.strong // max(result.tests, 1))

        base_total = sum(
            result.scores[k] * WEIGHTS[k] for k in WEIGHTS
        )
        result.base_total = round(base_total)

        # Penalties
        penalty = sum(a["penalty"] for a in all_anti)
        if result.copy_paste:
            penalty += result.copy_paste.get("penalty", 0)
        if result.bad_naming:
            penalty += result.bad_naming.get("penalty", 0)
        result.total_penalty = abs(penalty)

        comp_mult = 1.0 if result.compilation.get("ok") else 0.0
        result.total = round(max(0, base_total - result.total_penalty) * comp_mult)

        grade, desc = EvaService._calc_grade(result.total)
        result.grade = grade
        result.grade_desc = desc

        result.recommendations = EvaService._build_recommendations(result)
        return result
