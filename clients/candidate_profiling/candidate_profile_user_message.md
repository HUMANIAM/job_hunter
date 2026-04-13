# Candidate Profile User Message

Extract the requested candidate profile fields from the candidate CV or resume text.

Candidate fields should describe what the candidate appears able to offer professionally based on the source text.

For candidate profile extraction:
- use the headline, summary, work experience, project history, education, skills, and repeated work themes
- favor repeated professional evidence over one-off mentions
- favor recent and substantial experience over old, minor, or isolated experience
- use the full CV context when it clearly supports a better professional interpretation than one literal line alone
- prefer concrete professional signals over vague labels
- be conservative when multiple interpretations are plausible

## Field Guidance

### Global extraction rule

- Extract only what the candidate CV explicitly states or directly and clearly supports as a candidate-side qualification, background, capability, or professional identity.
- Do not invent, generalize beyond the source text, or convert weak context into a strong claim.
- If a field is not clearly supported, leave it unset or empty.
- Evidence must support the exact extracted value, not a nearby or broader idea.
- Do not let a single weak clue outweigh repeated stronger evidence.

### Strength semantics

For list-based fields, return items with:
- `name`
- `strength`
- `confidence`
- `evidence`

Use only these strength values:
- `core`: central, repeated, and defining for the candidate profile
- `strong`: clearly supported and professionally meaningful, but not the main defining signal
- `secondary`: real and useful, but less central or less repeated
- `exposure`: present with weaker depth, duration, or repetition

### role_titles

- start from the explicit CV headline and explicit job titles
- keep `primary` anchored to the clearest current or dominant professional role unless the CV clearly and repeatedly supports a more standard professional role title
- refine using repeated responsibilities, strongest technical ownership, and recurring engineering themes across roles and projects
- primary should be the single best professional role the candidate appears qualified to perform
- alternatives may include nearby roles that are also strongly supported by the CV
- do not let one isolated tool, project, or domain mention redefine the main role
- do not add formatting variants as alternatives

### education

Extract the education background that is clearly supported by the source text.

- `min_level` is the highest clearly achieved education level, if any.
- `accepted_fields` are the clearly supported study fields, majors, or education directions.
- `confidence` should reflect how strongly the source text supports the extracted education background.
- `evidence` should contain the direct snippets that support the extracted education background.
- Do not infer education from weak or indirect context.
- Do not keep catch-all phrases such as `similar` as accepted fields.
- Normalize values to lowercase.
- Keep `accepted_fields` distinct and deduplicated.
- Leave `min_level` unset, `accepted_fields` empty, `confidence` at `0.0`, and `evidence` empty when the CV does not clearly specify them.

### experience

Extract the candidate experience that is clearly supported by the source text.

- `min_years` is the best conservative estimate of relevant professional experience clearly supported by the CV, if any.
- `seniority_band` is the clearest supported seniority level, if any, such as `junior`, `medior`, `senior`, `lead`, or `principal`.
- Do not infer `min_years` from seniority labels alone.
- Do not infer seniority from one isolated responsibility or tool mention.
- Do not promote internships, education, hobbies, or general exposure into professional experience.
- Set `seniority_band` only when the CV explicitly states it or the work history clearly supports it.
- Normalize values to lowercase where applicable.
- Leave fields unset when the CV does not clearly support them.

### languages

Extract human languages the candidate clearly appears able to use.

- Return a list of language items with `name`, `strength`, `confidence`, and `evidence`.
- Extract only human languages such as `english`, `german`, or `dutch`.
- Do not treat programming languages, technology lists, or sections labeled `Languages:` that enumerate technologies as human languages.
- Use `core` or `strong` only when the CV clearly supports real professional or fluent use of the human language.
- Use `secondary` or `exposure` for weaker but still meaningful human-language evidence.
- Do not infer languages from location alone.
- Do not convert a weak clue into a strong language claim.
- Normalize values to lowercase.
- Keep values distinct and deduplicated.

### technical_core_features

Extract the candidate’s core technical capabilities that are clearly supported by the source text.

- Return a list of technical feature items with `name`, `strength`, `confidence`, and `evidence`.
- Use `core` for defining technical strengths, `strong` for clearly supported strengths, `secondary` for meaningful but less central capabilities, and `exposure` for weaker but real exposure.
- Extract only core technical signals relevant to the candidate’s professional profile.
- Do not let one isolated tool, framework, or project mention redefine the candidate’s core profile.
- Do not convert minor exposure into a core strength.
- Normalize values to lowercase.
- Keep values distinct and deduplicated.

### domain_background

Extract the domains or industries the candidate clearly has background in.

- Return a list of domain items with `name`, `strength`, `confidence`, and `evidence`.
- Use `core` for domains that strongly define the candidate profile, `strong` for clearly established domains, `secondary` for meaningful but less central domains, and `exposure` for weaker but real domain exposure.
- Strong evidence includes explicit company context, project context, role context, or repeated work history tied to a domain.
- Do not extract vague business context or general technology labels as domain background.
- Do not infer a domain from one isolated example alone.
- Normalize values to lowercase.
- Keep values distinct and deduplicated.
- Return an empty list when the CV does not clearly support domain background.

Source text:
{{SOURCE_TEXT}}
