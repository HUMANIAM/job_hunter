from infra import browser as browser_utils


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
