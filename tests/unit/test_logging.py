from infra import logging as infra_logging


def test_log_prefixes_message_with_timestamp(monkeypatch, capsys) -> None:
    monkeypatch.setattr(infra_logging.time, "strftime", lambda _fmt: "12:34:56")

    infra_logging.log("hello")

    assert capsys.readouterr().out == "[12:34:56] hello\n"
