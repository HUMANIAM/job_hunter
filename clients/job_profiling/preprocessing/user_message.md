# Job HTML Signal Cleaner User Message

Clean the following raw job HTML.

Keep only job-relevant text and drop page noise.

Return exactly one JSON object.
The object must contain a `lines` array.
Each line item must include `source_kind`, `html_tag`, and `text`.

Important:
- `source_kind` must be one of `visible_html`, `json_ld`, or `meta`
- use the original HTML tag names from the source
- preserve source order
- copy text closely from the source
- keep vacancy-relevant JSON-LD and meta facts only as targeted fact lines, not full blobs
- do not summarize
- do not interpret
- do not classify into profile fields
- do not invent or rename tags
- do not include explanations

Raw job HTML:
{{RAW_JOB_HTML}}
