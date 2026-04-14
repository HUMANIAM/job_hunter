# Job HTML Signal Cleaner User Message

Clean the following raw job HTML.

Keep only job-relevant text and drop page noise.

Return exactly one JSON object.
The object must contain a `lines` array.
Each line item must include `html_tag` and `text`.

Important:
- use the original HTML tag names from the source
- preserve source order
- copy text closely from the source
- keep only visible vacancy text that a human candidate can directly see on the page
- every `text` value must stay on a single line
- replace any internal line breaks, tabs, or repeated whitespace with single spaces
- the final rendered text will be one line per item as `html_tag: text`
- do not summarize
- do not interpret
- do not classify into profile fields
- do not invent or rename tags
- do not include explanations

Raw job HTML:
{{RAW_JOB_HTML}}
