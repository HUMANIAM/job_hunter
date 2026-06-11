Evaluate candidate eligibility for this vacancy.

Use only the normalized comparison input below.

Important:
- Return JSON only.
- Use only the provided normalized fields.
- Do not invent missing facts.
- Do not use domain or industry background as an eligibility blocker unless it is explicitly included below as a hard requirement.
- A field with no vacancy requirement is neutral and must not increase the score.
- Generic overlap such as bachelor level, seniority band, or English must not outweigh a clear mismatch in role identity and required technical experience.
- If the role direction and required technical experience clearly mismatch, return `not_eligible`.
- Use `uncertain` only when the evidence is incomplete, ambiguous, or partially aligned in the required areas.


## Role titles

| type | vacancy | candidate |
| ---|---|---|
| Primary | {{VACANCY_ROLE_PRIMARY}} | {{CANDIDATE_ROLE_PRIMARY}} |
| Alternatives | {{VACANCY_ROLE_ALTERNATIVES}} | {{CANDIDATE_ROLE_ALTERNATIVES}} |

## Education

| field | vacancy | candidate |
|---|---|---|
| minimum level | {{VACANCY_EDUCATION_MIN_LEVEL}} | {{CANDIDATE_EDUCATION_MIN_LEVEL}} |
| accepted / relevant fields | {{VACANCY_EDUCATION_FIELDS}} | {{CANDIDATE_EDUCATION_FIELDS}} |

## Languages

| field | vacancy | candidate |
|---|---|---|
| required | {{VACANCY_REQUIRED_LANGUAGES}} | {{CANDIDATE_LANGUAGES}} |
| preferred | {{VACANCY_PREFERRED_LANGUAGES}} | {{CANDIDATE_LANGUAGES}} |

## Experience

| field | vacancy | candidate |
|---|---|---|
| minimum years | {{VACANCY_MIN_YEARS}} | {{CANDIDATE_MIN_YEARS}} |
| seniority band | {{VACANCY_SENIORITY_BAND}} | {{CANDIDATE_SENIORITY_BAND}} |

## Technical core features

### Vacancy
{{VACANCY_TECHNICAL_CORE_FEATURES}}

### Candidate
{{CANDIDATE_TECHNICAL_CORE_FEATURES}}

## Technologies

### Vacancy
{{VACANCY_TECHNOLOGIES}}

### Candidate
{{CANDIDATE_TECHNOLOGIES}}
