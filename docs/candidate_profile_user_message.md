# Candidate Profile User Message

Extract the requested candidate profile fields from the candidate CV or resume text.

Candidate fields should describe what the candidate appears able to offer, support, or require based on the source text.

For candidate profile extraction:
- use the headline, summary, work experience, project history, education, skills, and repeated work themes
- favor repeated professional evidence over one-off mentions
- favor recent and substantial experience over old, minor, or isolated experience
- use the full CV context to infer the best-fitting professional interpretation when strongly supported
- prefer concrete professional signals over vague labels
- be conservative when multiple interpretations are plausible

## Field Guidance

### Global extraction rule

- Extract only what the candidate CV explicitly states or directly and clearly supports as a candidate-side qualification, background, capability, or constraint.
- Do not invent, generalize, normalize beyond recognition, or convert weak context into strong candidate claims.
- If a field is not clearly supported, leave it unset or empty.
- Do not emit negative boolean values such as `false` unless the source text clearly supports the negative.
- Evidence must support the exact extracted value, not a nearby or broader idea.

### role_titles

- start from the explicit CV headline and explicit job titles
- refine using repeated responsibilities, strongest technical ownership, and recurring engineering themes across roles and projects
- keep `primary` anchored to the clearest current or dominant professional role unless the CV clearly and repeatedly supports a more standard professional role title
- primary should be the single best professional role the candidate appears qualified to perform
- alternatives may include nearby roles that are also strongly supported by the CV
- do not let one isolated tool, project, or domain mention redefine the main role
- do not add formatting variants as alternatives

### education

Extract the education background that is clearly supported by the source text.

- `min_level` should be the clearest achieved education level supported by the CV
- `accepted_fields` should contain the study fields, majors, or education directions clearly supported by the CV
- `confidence` should reflect how strongly the source text supports the extracted education background
- `evidence` should contain the direct snippets that support the extracted education background
- do not infer education from weak or indirect context
- do not keep catch-all phrases such as `similar` as accepted fields
- normalize values to lowercase
- keep `accepted_fields` distinct and deduplicated
- leave fields unset or empty when the CV does not clearly specify them

### experience

Extract the candidate experience that is clearly supported by the source text.

- `min_years` should be the best conservative estimate of relevant professional experience directly supported by the CV
- `seniority_band` should be the clearest supported seniority level, if any, such as `junior`, `medior`, `senior`, `lead`, or `principal`
- do not infer `min_years` from seniority labels alone
- do not infer seniority from one isolated responsibility or tool mention
- do not promote internships, education, hobbies, or general exposure into professional experience
- set `seniority_band` only when the CV explicitly states it or the work history clearly supports it
- normalize values to lowercase where applicable
- leave fields unset when the CV does not clearly support them

### languages

Extract human languages the candidate clearly appears able to use.

- `required` should contain languages clearly supported as real candidate languages with strong evidence
- `preferred` should contain languages that are weaker but still meaningfully supported
- do not infer languages from location alone
- do not convert a weak clue into a strong language claim
- normalize values to lowercase
- keep values distinct and deduplicated across both lists

### technical_core_requirements

Extract the candidate’s core technical capabilities that are clearly supported by the source text.

- `required` should contain technical skills, technologies, or engineering capabilities strongly supported as real candidate strengths
- `preferred` should contain technical skills, technologies, or engineering capabilities that are supported but less central or less repeated
- extract only candidate-facing technical signals, not vague traits
- do not let one isolated tool, framework, or project mention redefine the candidate’s core profile
- do not convert minor exposure into a core strength
- normalize values to lowercase
- keep values distinct and deduplicated across both lists

### domain_or_industry_requirements

Extract the domains or industries the candidate clearly has background in.

- `required` should contain domains or industries clearly supported by real candidate experience, background, knowledge, familiarity, or prior work
- strong evidence includes explicit company context, project context, role context, or repeated work history tied to a domain
- do not extract vague business context or general technology labels as domain background
- do not infer a domain from one isolated example alone
- normalize values to lowercase
- keep values distinct and deduplicated
- leave `required` empty when the CV does not clearly support domain background

### work_mode_constraints

Extract work mode and location constraints only when they are clearly supported by the candidate source text.

- `onsite`, `hybrid`, and `remote` should reflect clearly stated or strongly supported candidate-side work mode constraints or preferences
- set a work-mode field to `true` only when that mode is explicitly stated or directly and clearly supported
- do not set a work-mode field to `false` unless the source text clearly supports the negative
- if the source gives partial information, set only the clearly supported field and leave the others unset
- `location` should contain clearly supported candidate locations relevant to work preference, current work base, or stable work region
- do not treat a single weak location mention as a firm work constraint
- normalize location values to lowercase
- keep `location` distinct and deduplicated
- leave fields unset or empty when the CV does not clearly support them

### mobility_constraints

Extract mobility-related constraints only when the source text clearly supports them.

- `travel_required` should indicate whether the candidate source text clearly supports willingness or requirement to travel
- `driving_license_required` should indicate whether the candidate source text clearly supports having or requiring a driving license as part of work mobility
- set these fields only when the source text clearly supports them
- do not infer travel or driving-license constraints from weak context alone
- leave fields unset when the CV does not clearly support them

### legal_and_compliance_constraints

Extract legal or compliance-related constraints only when the source text clearly supports them.

- `work_authorization_required` should indicate candidate-side work authorization or sponsorship constraints only when clearly supported by the source text
- `export_control_required` should indicate candidate-side export-control-related constraints only when clearly supported by the source text
- `background_check_required` should indicate candidate-side background-check constraints only when clearly supported by the source text
- `security_clearance_required` should indicate candidate-side security-clearance constraints only when clearly supported by the source text
- do not infer legal or compliance blockers from nationality, location, or regulated-industry context alone
- leave fields unset when the CV does not clearly support them

Source text:
{{SOURCE_TEXT}}