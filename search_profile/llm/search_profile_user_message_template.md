# Search Profile LLM User Message Template

Extract a candidate search profile from the following CV/resume text.

Return **JSON only**.

## Schema

```json
{{search_profile_schema_json}}
```

## Optional candidate context

Use this only when present. It is supportive context, not stronger than explicit CV evidence.

```json
{{candidate_context_json}}
```

## CV / Resume Text

```text
{{cv_text}}
```

## Reminder

- Follow the schema exactly.
- Be conservative.
- Do not rank jobs.
- Do not compare against any job.
- Extract candidate-side features only.
