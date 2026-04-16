from __future__ import annotations

from contextlib import contextmanager

from infra import browser as browser_utils


class OpenAndPrepareFakeLocator:
    def __init__(self, calls: list[tuple[str, object]], selector: str) -> None:
        self.calls = calls
        self.selector = selector

    @property
    def first(self) -> "OpenAndPrepareFakeLocator":
        return self

    def wait_for(self, timeout: int) -> None:
        self.calls.append(("wait_for", (self.selector, timeout)))

    def count(self) -> int:
        self.calls.append(("count", self.selector))
        return 1

    def is_visible(self) -> bool:
        self.calls.append(("is_visible", self.selector))
        return True

    def click(self, timeout: int) -> None:
        self.calls.append(("click", (self.selector, timeout)))


class OpenAndPrepareFakePage:
    def __init__(self, calls: list[tuple[str, object]]) -> None:
        self.calls = calls

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.calls.append(("goto", (url, wait_until, timeout)))

    def wait_for_load_state(self, state: str) -> None:
        self.calls.append(("load_state", state))

    def wait_for_timeout(self, timeout: int) -> None:
        self.calls.append(("timeout", timeout))

    def locator(self, selector: str) -> OpenAndPrepareFakeLocator:
        self.calls.append(("locator", selector))
        return OpenAndPrepareFakeLocator(self.calls, selector)


def test_create_browser_uses_sync_playwright_and_closes_browser(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    fake_browser = object()
    fake_playwright = object()

    class FakePlaywrightManager:
        def __enter__(self) -> object:
            calls.append(("sync_enter", None))
            return fake_playwright

        def __exit__(self, exc_type, exc, tb) -> None:
            calls.append(("sync_exit", exc_type))

    def fake_sync_playwright() -> FakePlaywrightManager:
        calls.append(("sync_playwright", None))
        return FakePlaywrightManager()

    def fake_launched_chromium(playwright, *, headless=True):
        @contextmanager
        def _manager():
            calls.append(("launch", (playwright, headless)))
            try:
                yield fake_browser
            finally:
                calls.append(("close", fake_browser))

        return _manager()

    monkeypatch.setattr(browser_utils, "sync_playwright", fake_sync_playwright)
    monkeypatch.setattr(browser_utils, "launched_chromium", fake_launched_chromium)

    with browser_utils.create_browser(headless=False) as browser:
        calls.append(("yielded", browser))

    assert calls == [
        ("sync_playwright", None),
        ("sync_enter", None),
        ("launch", (fake_playwright, False)),
        ("yielded", fake_browser),
        ("close", fake_browser),
        ("sync_exit", None),
    ]


def test_wait_for_page_ready_waits_for_dom_and_selector() -> None:
    calls: list[tuple[str, object]] = []

    class FakeLocator:
        @property
        def first(self) -> "FakeLocator":
            return self

        def wait_for(self, timeout: int) -> None:
            calls.append(("wait_for", timeout))

    class FakePage:
        def wait_for_load_state(self, state: str) -> None:
            calls.append(("load_state", state))

        def wait_for_timeout(self, timeout: int) -> None:
            calls.append(("timeout", timeout))

        def locator(self, selector: str) -> FakeLocator:
            calls.append(("locator", selector))
            return FakeLocator()

    browser_utils.wait_for_page_ready(
        FakePage(),
        "a.ready",
        timeout_ms=1234,
        settle_ms=567,
    )

    assert calls == [
        ("load_state", "domcontentloaded"),
        ("timeout", 567),
        ("locator", "a.ready"),
        ("wait_for", 1234),
    ]


def test_prepare_page_waits_for_each_selector_and_clicks_visible_ones() -> None:
    calls: list[tuple[str, object]] = []

    class FakeLocator:
        def __init__(self, selector: str) -> None:
            self.selector = selector

        @property
        def first(self) -> "FakeLocator":
            return self

        def wait_for(self, timeout: int) -> None:
            calls.append(("wait_for", (self.selector, timeout)))

        def count(self) -> int:
            calls.append(("count", self.selector))
            return 1 if self.selector == "input.cookie-close" else 0

        def is_visible(self) -> bool:
            calls.append(("is_visible", self.selector))
            return self.selector == "input.cookie-close"

        def click(self, timeout: int) -> None:
            calls.append(("click", (self.selector, timeout)))

    class FakePage:
        def wait_for_load_state(self, state: str) -> None:
            calls.append(("load_state", state))

        def wait_for_timeout(self, timeout: int) -> None:
            calls.append(("timeout", timeout))

        def locator(self, selector: str) -> FakeLocator:
            calls.append(("locator", selector))
            return FakeLocator(selector)

    clicked_selectors = browser_utils.prepare_page(
        FakePage(),
        wait_for=["a.ready", "div.results"],
        click_if_visible_selectors=["input.cookie-close", "button.missing"],
        wait_timeout_ms=1234,
        wait_settle_ms=567,
        click_timeout_ms=222,
        click_settle_ms=333,
    )

    assert clicked_selectors == ["input.cookie-close"]
    assert calls == [
        ("load_state", "domcontentloaded"),
        ("timeout", 567),
        ("locator", "a.ready"),
        ("wait_for", ("a.ready", 1234)),
        ("locator", "div.results"),
        ("wait_for", ("div.results", 1234)),
        ("locator", "input.cookie-close"),
        ("count", "input.cookie-close"),
        ("is_visible", "input.cookie-close"),
        ("click", ("input.cookie-close", 222)),
        ("timeout", 333),
        ("locator", "button.missing"),
        ("count", "button.missing"),
    ]


def test_open_and_prepare_page_opens_then_prepares_page() -> None:
    calls: list[tuple[str, object]] = []

    clicked_selectors = browser_utils.open_and_prepare_page(
        OpenAndPrepareFakePage(calls),
        "https://example.com/jobs",
        wait_for=["a.ready"],
        click_if_visible_selectors=["input.cookie-close"],
        open_wait_until="domcontentloaded",
        open_timeout_ms=123,
        wait_timeout_ms=456,
        wait_settle_ms=789,
        click_timeout_ms=111,
        click_settle_ms=222,
    )

    assert clicked_selectors == ["input.cookie-close"]
    assert calls == [
        ("goto", ("https://example.com/jobs", "domcontentloaded", 123)),
        ("load_state", "domcontentloaded"),
        ("timeout", 789),
        ("locator", "a.ready"),
        ("wait_for", ("a.ready", 456)),
        ("locator", "input.cookie-close"),
        ("count", "input.cookie-close"),
        ("is_visible", "input.cookie-close"),
        ("click", ("input.cookie-close", 111)),
        ("timeout", 222),
    ]


def test_click_if_visible_clicks_and_waits_when_element_is_visible() -> None:
    calls: list[tuple[str, object]] = []

    class FakeLocator:
        @property
        def first(self) -> "FakeLocator":
            return self

        def count(self) -> int:
            calls.append(("count", None))
            return 1

        def is_visible(self) -> bool:
            calls.append(("is_visible", None))
            return True

        def click(self, timeout: int) -> None:
            calls.append(("click", timeout))

    class FakePage:
        def locator(self, selector: str) -> FakeLocator:
            calls.append(("locator", selector))
            return FakeLocator()

        def wait_for_timeout(self, timeout: int) -> None:
            calls.append(("timeout", timeout))

    clicked = browser_utils.click_if_visible(
        FakePage(),
        "input.cookie-close",
        timeout_ms=222,
        settle_ms=333,
    )

    assert clicked is True
    assert calls == [
        ("locator", "input.cookie-close"),
        ("count", None),
        ("is_visible", None),
        ("click", 222),
        ("timeout", 333),
    ]
