# Codex Instructions

## Test Data Rules

- When reusable reference data exists under `tests/**/data/`, use that reference data in tests instead of copying the same literals inline.
- When a test needs the same arranged input or expected values more than once, extract or extend a shared helper under `tests/**/data/` rather than duplicating setup in the test body.
