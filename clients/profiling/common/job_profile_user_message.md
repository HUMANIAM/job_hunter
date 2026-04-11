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

### Global extraction rule

- Extract only what the vacancy explicitly states or directly and clearly implies as a candidate-facing requirement or constraint.
- Do not invent, generalize, normalize beyond recognition, or convert company context into candidate requirements.
- Do not turn role context, customer context, product examples, project examples, or company environment into hard requirements unless the posting clearly presents them as such.
- If a field is not clearly supported, leave it unset or empty.
- Do not emit negative boolean values such as `false` unless the vacancy explicitly states the negative.
- Evidence must support the exact extracted value, not a nearby or broader idea.
- If a field is not clearly supported as a candidate-facing requirement or constraint, leave it unset or empty.


### role_titles
- start from the explicit job posting title
- keep `primary` anchored to the explicit posting title unless the posting clearly and repeatedly supports a more standard professional role title
- refine using the responsibilities, requirements, and recurring engineering themes in the posting
- primary should be the single best professional role the company is hiring for
- alternatives may include nearby roles that are also strongly supported by the posting
- do not let one isolated tool, project, or domain mention redefine the main role
- do not add formatting variants as alternatives


### education

Extract the education requirements that are clearly supported by the source text.

- `min_level` is the minimum clearly stated education level, if any.
- `accepted_fields` are the clearly accepted study fields or education directions.
- `confidence` should reflect how strongly the source text supports the extracted education requirements.
- `evidence` should contain the direct snippets that support the extracted education requirements.
- Do not infer education requirements from weak or indirect context.
- Do not convert a preference into a requirement.
- Do not keep catch-all phrases such as `similar` as accepted fields.
- Normalize values to lowercase.
- Keep `accepted_fields` distinct and deduplicated.
- Leave `min_level` unset, `accepted_fields` empty, `confidence` at `0.0`, and `evidence` empty when the vacancy does not clearly specify them.


### experience

Extract the experience requirements that are clearly supported by the source text.

- `min_years` is the minimum clearly stated years of relevant professional experience, if any.
- `seniority_band` is the clearest explicitly supported seniority level, if any, such as `junior`, `medior`, `senior`, `lead`, or `principal`.
- Do not infer `min_years` from seniority labels alone.
- Do not infer seniority from one isolated responsibility or tool mention.
- Do not promote internships, education, or general exposure into professional experience.
- Set `seniority_band` only when the posting explicitly states it or the years-of-experience requirement clearly supports it.
- Normalize values to lowercase where applicable.
- Leave fields unset when the vacancy does not clearly specify them.

### languages

Extract language requirements that are clearly supported by the source text.

- `required` contains languages the vacancy explicitly treats as required.
- `preferred` contains languages the vacancy explicitly treats as preferred or beneficial.
- Only place a language in `required` when the posting makes that requirement explicit.
- Do not infer language requirements from location alone.
- Do not convert a preference into a requirement.
- Normalize values to lowercase.
- Keep values distinct and deduplicated across both lists.

### technical_core_requirements

Extract the core technical requirements that are clearly supported by the source text.

- `required` contains technical skills, technologies, or engineering capabilities the vacancy explicitly treats as required.
- `preferred` contains technical skills, technologies, or engineering capabilities the vacancy explicitly treats as preferred, optional, or beneficial.
- Extract only the core technical signals relevant to the role.
- Only extract items that the posting presents as candidate-facing expectations, not just task context or project context.
- Do not let one isolated tool, framework, or project mention redefine the role.
- Do not convert general environment context into a hard requirement.
- Do not convert a preference into a requirement.
- Normalize values to lowercase.
- Keep values distinct and deduplicated across both lists.

### domain_or_industry_requirements

Extract domain or industry requirements only when the vacancy clearly presents them as candidate-facing requirements.

- `required` contains domains or industries the vacancy explicitly requires as candidate experience, background, or familiarity.
- Extract a domain only when the posting clearly asks for it in the candidate profile, for example through wording such as `experience in`, `background in`, `knowledge of`, or `familiarity with`.
- Do not extract customer industries, product examples, application areas, project examples, or market context as candidate requirements unless the posting clearly frames them that way.
- Do not extract broad business context such as `high-tech`, `medical`, `semiconductor`, or similar unless the posting clearly requires candidate background in that domain.
- Do not infer a domain requirement from responsibilities alone.
- Normalize values to lowercase.
- Keep values distinct and deduplicated.
- Leave `required` empty, `confidence` at `0.0`, and `evidence` empty when the vacancy does not clearly specify domain requirements.

### work_mode_constraints

Extract work mode and location constraints only when they are clearly supported as role-specific expectations.

- `onsite`, `hybrid`, and `remote` should reflect clearly stated working mode expectations for the role.
- Set a work-mode field to `true` only when that mode is explicitly stated or directly and clearly supported by the posting.
- Do not set a work-mode field to `false` unless the posting explicitly rules that mode out.
- If the posting gives partial information, set only the clearly supported field and leave the others unset.
- `location` contains clearly stated work locations relevant to the role.
- Extract a location only when the posting presents it as a role location, work base, or work area.
- Do not treat general company locations, office marketing text, or regional branding as role locations unless the posting clearly ties them to the role.
- Normalize location values to lowercase.
- Keep `location` distinct and deduplicated.
- Leave fields unset or empty when the vacancy does not clearly specify them.


### mobility_constraints

Extract mobility-related constraints only when the vacancy clearly states them as candidate-facing requirements.

- `travel_required` indicates whether the role explicitly requires travel.
- `driving_license_required` indicates whether the role explicitly requires a driving license.
- Set these fields only when the vacancy clearly states the requirement.
- Mentions of client sites, customer premises, international customers, multiple locations, or regional work context are not enough on their own to set `travel_required`.
- Do not infer travel requirements from customer-facing work, field work, or collaboration across sites unless the posting clearly states travel is required.
- Do not infer driving-license requirements from field work, site visits, or location context alone.
- Leave fields unset when the vacancy does not clearly specify them.

### legal_and_compliance_constraints

Extract legal or compliance-related constraints only when the vacancy clearly states them as candidate-facing requirements.

- `work_authorization_required` indicates whether the role explicitly requires legal authorization to work in a country or region.
- `export_control_required` indicates whether the role explicitly states export control, controlled-technology access, or similar access restrictions.
- `background_check_required` indicates whether the role explicitly states screening or background-check requirements.
- `security_clearance_required` indicates whether the role explicitly states a clearance requirement.
- Do not infer legal or compliance blockers from regulated-industry context alone.
- Do not convert export-control language into generic work-authorization requirements unless the posting explicitly states both.
- If the posting states only controlled-technology access restrictions, set only `export_control_required` and leave `work_authorization_required` unset.
- Treat these fields conservatively because false negatives are costly.
- Leave fields unset when the vacancy does not clearly specify them.


Source text:
{{SOURCE_TEXT}}
