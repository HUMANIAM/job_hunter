# Job HTML Signal Cleaner User Message

Clean the following raw job HTML.

Keep only job-relevant text and drop page noise.

Return plain text only in this format:

html_tag: copied text content

Important:
- use the original HTML tag names from the source
- preserve source order
- copy text closely from the source
- do not summarize
- do not interpret
- do not classify into profile fields
- do not invent or rename tags

Raw job HTML:
{{RAW_JOB_HTML}}