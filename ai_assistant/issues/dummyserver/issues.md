# DummyHttpServer close() hang without start()

## Repro script

File: `ai_assistant/issues/dummyserver/shutdown.py`

```python
server = DummyHttpServer()
server.close()
```

The script also prints before and after `close()` so it is obvious where it stops.

## Command used

```bash
timeout 3s .venv/bin/python ai_assistant/issues/dummyserver/shutdown.py
```

## Observed result

It hangs in `close()` when `start()` was never called.

Observed output before the timeout:

```text
creating server
calling close() without start()
```

The process did not print `close() returned` and exited only because `timeout`
killed it after 3 seconds with exit code `124`.
