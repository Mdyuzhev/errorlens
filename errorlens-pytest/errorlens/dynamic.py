"""Runtime dynamic label API — el.dynamic.*"""
from .context import get_current


class DynamicContext:
    """Позволяет устанавливать метаданные теста в runtime."""

    def title(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.title = value

    def description(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.description = value

    def feature(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.feature = value

    def story(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.story = value

    def epic(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.epic = value

    def suite(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.suite = value

    def severity(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.severity = value

    def tag(self, *tags: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.tags.extend(tags)

    def owner(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.owner = value

    def id(self, value: str) -> None:
        ctx = get_current()
        if ctx:
            ctx.test_id = value

    def link(self, url: str, name: str = "", link_type: str = "") -> None:
        ctx = get_current()
        if ctx:
            ctx.links.append({"url": url, "name": name or url, "type": link_type})

    def issue(self, url: str, name: str = "") -> None:
        self.link(url, name, "issue")

    def testcase(self, url: str, name: str = "") -> None:
        self.link(url, name, "testcase")

    def parameter(self, name: str, value) -> None:
        ctx = get_current()
        if ctx:
            ctx.parameters.append({"name": name, "value": str(value)})


# Singleton
dynamic = DynamicContext()
