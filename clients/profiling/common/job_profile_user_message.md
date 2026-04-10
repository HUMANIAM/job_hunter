# Job Profile User Message

Extract the requested job profile fields from the job posting text.

Job fields should describe the role the company is actually hiring for based on the source text.

For job profile extraction:
- use the explicit job title, summary, responsibilities, requirements, and repeated work themes
- favor direct hiring signals over company marketing, benefits, culture text, or application process details
- favor repeated technical and professional signals over one-off mentions
- use the full posting context to infer the best-fitting professional interpretation when strongly supported
- prefer concrete professional role signals over vague labels
- be conservative when multiple interpretations are plausible

## Field Guidance

### role_titles
- start from the explicit job posting title
- refine using the responsibilities, requirements, and recurring engineering themes in the posting
- primary should be the single best professional role the company is hiring for
- alternatives may include nearby roles that are also strongly supported by the posting
- do not let one isolated tool, project, or domain mention redefine the main role


### education

Extract the education requirements that are clearly supported by the source text.

- `min_level` is the minimum clearly stated education level, if any.
- `accepted_fields` are the clearly accepted study fields or education directions.
- `confidence` should reflect how strongly the source text supports the extracted education requirements.
- `evidence` should contain the direct snippets that support the extracted education requirements.
- Do not infer education requirements from weak or indirect context.
- Do not convert a preference into a requirement.
- Normalize values to lowercase.
- Keep `accepted_fields` distinct and deduplicated.
- Leave `min_level` unset, `accepted_fields` empty, `confidence` at `0.0`, and `evidence` empty when the vacancy does not clearly specify them.

Source text:
{{SOURCE_TEXT}}
