# LLM User Message Template

Extract the ambiguous ranking-relevant fields from the following job detail.

## Instructions

- Use the system rules.
- Return JSON only.
- Match the schema exactly.
- Be conservative.
- Do not copy long requirement sentences into skill arrays.
- Normalize concrete technical terms into compact items.
- Use `null` or empty arrays when unsupported.
- Include short evidence snippets.

## Output Schema

```json
{{llm_output_schema_json}}
```

## Deterministic Fields Already Extracted

These fields were extracted by deterministic code and are supplied only for context. Do not try to re-infer them unless they directly support ambiguous extraction.

```json
{{deterministic_fields_json}}
```

## Job Detail Text

```text
{{description_text}}
```
