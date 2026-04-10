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

Source text:
{{SOURCE_TEXT}}