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

- `min_years` is the best conservative estimate of total relevant professional experience derived from the candidate’s listed professional work experience dates.
- Calculate `min_years` only from explicit professional role date ranges in the CV.
- Treat roles marked `current` or equivalent as ending on the extraction date.
- Do not double-count overlapping roles.
- Do not count internships, education, hobbies, courses, certifications, projects, or general exposure as professional experience.
- If the dates are incomplete or ambiguous, use the most conservative estimate clearly supported by the source text.

- `seniority_band` must be one of `junior`, `standard`, `senior`, `lead`, or `principal`.
- Derive `seniority_band` from the calculated `min_years` when the work history clearly supports it.
- Do not infer `seniority_band` from one isolated responsibility, tool, or title alone.

Use this mapping:
- `junior`: 1 <= years < 3
- `standard`: 3 <= years < 5
- `senior`: 5 <= years < 10
- `lead`: 10 <= years < 12
- `principal`: years >= 12

### Evidence rules for experience

- Evidence must come only from the listed professional experience entries used in the calculation.
- Evidence must be explicit date-bearing role snippets from the CV.
- Include all professional role entries used to derive `min_years`.
- Do not use summary text, skills sections, project sections, education, or technology lists as evidence for this field.
- Do not use partial evidence when the calculation depends on additional roles; include the full set of roles used.
- If explicit professional experience entries are not sufficient, leave the field unset.

- Normalize values to lowercase where applicable.
- Leave fields unset when the CV does not clearly support them.


### languages

Extract human languages the candidate clearly appears able to use.

- Return a list of language items with `name`, `strength`, `confidence`, and `evidence`.
- Extract only human languages such as `english`, `arabic`, `dutch`, or `german`.
- Never extract programming languages or technologies as human languages.

#### Extraction order

1. If the CV explicitly mentions a human language, extract it from that explicit evidence.
2. If the CV does not explicitly mention human languages, infer them only from strong real-world evidence.

#### Valid evidence for inferred human languages

- repeated professional work in multinational or clearly English-based environments
- work experience at companies or teams where professional English use is clearly implied
- birthplace, nationality, or home-country context when it strongly supports the native language
- long-term residence or work in a country can support the local language, but this is weaker than explicit mention or strong professional evidence

#### Invalid evidence

- programming-language lists
- technology stacks
- sections labeled `Languages:` that contain only technologies
- person name
- phone number
- email
- location alone, unless used only as a weak clue for the local language

#### Strength rules

- `core`: explicit strong evidence of fluent or professional use, or repeated direct support across the CV
- `strong`: strong inferred evidence from repeated professional context or strongly supported native-language context
- `secondary`: weaker but still meaningful evidence, such as living or working in a country where the language is commonly used
- `exposure`: weak but valid clue that does not support stronger certainty

#### Specific inference rules

- If a human language is explicitly mentioned, prefer that over inference.
- Do not infer additional languages unless the CV clearly supports them.
- Repeated work in multinational engineering environments can be strong evidence for `english`.
- Birthplace or clear country-of-origin context can be strong evidence for the native language of that country.
- Living or working in the Netherlands can support `dutch`, but usually only as `secondary` unless the CV gives stronger support.
- Do not use one weak clue to create a strong language claim.

#### Output rules

- If no valid human-language evidence exists, return an empty list.
- Normalize language names to lowercase.
- Keep values distinct and deduplicated.
- Evidence must use the strongest supporting clues available.


### technical_experience

Extract the candidate’s technical experience from the source text.

Shared rules for all subsections:

- Return structured feature items with `name`, `strength`, `confidence`, and `evidence`.
- Use `core` for defining strengths, `strong` for clearly supported strengths, `secondary` for meaningful but less central strengths, and `exposure` for weaker but real exposure.
- Extract only signals supported by the source text.
- Prefer extraction over summarization.
- Normalize values to lowercase.
- Keep values distinct and deduplicated.
- Each item must represent one concept only.
- Do not merge multiple concepts into one item.
- Do not invent broader labels when the source supports a more exact term.
- Keep concrete signals separate when they may matter independently later.

#### technical_core_features

Extract broad technical experience areas that describe the candidate’s professional profile.

- Use this field for high-level technical experience areas only.
- Good examples: `testing`, `ci/cd`, `software design and implementation`, `r&d software engineering`.
- Do not use this field for concrete programming languages, tools, frameworks, protocols, or libraries.
- Do not rewrite concrete signals into a broad category if they belong in a more specific field.

#### technologies

Extract concrete technologies clearly supported by the source text.

- This field includes programming languages, frameworks, libraries, tools, platforms, protocols, standards, databases, build systems, testing technologies, and infrastructure technologies.
- Examples: `c`, `c++`, `python`, `cmake`, `bazel`, `docker`, `git`, `pytest`, `googletest`, `robot framework`, `some/ip`, `ara com`, `rpc`, `tensorflow`, `pytorch`, `opencv`, `kaldi`, `mysql`, `sqlite`, `jenkins`.
- Keep exact supported terms where possible.
- Keep each item as one concept only.
- Do not merge multiple technologies into one item.
- Do not rewrite concrete technologies into broad labels.
- Do not populate this field with broad experience labels such as `testing`, `ci/cd`, or `software design and implementation`; those belong in `technical_core_features`.


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
