"""Extract code from LLM responses."""
import re


def get_language_for_framework(framework: str) -> str:
    return {"pytest": "python", "restassured": "java", "postman": "json",
            "cypress": "javascript", "k6": "javascript"}.get(framework, "python")


class CodeExtractor:
    def __init__(self, language: str = "python"):
        self.language = language

    def extract(self, text: str) -> str:
        if not text:
            return ""
        code = self._extract_from_markdown(text)
        if code:
            return self._clean_code(code)
        code = self._extract_by_pattern(text)
        return self._clean_code(code or text)

    def _extract_from_markdown(self, text: str) -> str | None:
        for pattern in [rf"```{self.language}\s*(.*?)```", r"```\w*\s*(.*?)```"]:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                return max(matches, key=len)
        return None

    def _extract_by_pattern(self, text: str) -> str | None:
        if self.language == "python":
            match = re.search(r"((?:import|from|def|class)\s+.*)", text, re.DOTALL)
            return match.group(1) if match else None
        return None

    def _clean_code(self, code: str) -> str:
        lines = [l for l in code.split("\n")
                 if not l.strip().startswith(("Here", "This", "The ", "Note:", "```"))]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)
