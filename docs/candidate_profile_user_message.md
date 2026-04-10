# Candidate Profile User Message

Extract the requested candidate profile fields from the CV or resume text.

Candidate fields should describe what the person appears qualified to do professionally based on the source text.

For candidate profile extraction:
- use the CV headline, summary, work experience, projects, and repeated responsibilities
- favor recent and repeated professional evidence over old, minor, or one-off mentions
- use the full CV context to infer the best-fitting professional interpretation when strongly supported
- prefer concrete professional signals over vague labels
- do not use education, hobbies, courses, or isolated keyword mentions as strong evidence unless the field explicitly calls for them
- be conservative when multiple interpretations are plausible

## Field Guidance

### role_titles
- infer titles from explicit job titles, repeated responsibilities, strongest technical ownership, and recurring engineering themes
- primary should be the single best professional role suggested by the CV
- alternatives may include nearby roles that are also strongly supported by the CV
- do not rely on one isolated project or one isolated tool mention to define the main role

Source text:
{{SOURCE_TEXT}}