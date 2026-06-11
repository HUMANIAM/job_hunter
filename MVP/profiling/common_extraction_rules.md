## Extraction Evidence Rules

- Every extracted field must be supported by evidence from the source text.
- Evidence must be short, direct, and specific.
- Use the best supporting snippet, not generic nearby text.
- Do not explain reasoning outside the schema.
- For derived or aggregate fields, include the key snippets used to derive them.
- Evidence may be clue-based when the field is inferred conservatively from strong context.
- Do not use irrelevant text as evidence.

## Extraction Confidence Rules

- Confidence must be grounded in the quality of the evidence.
- Higher confidence requires clear, direct, and strong support.
- Lower confidence is appropriate for indirect but still meaningful support.
- Do not guess confidence independently of evidence.

## Extraction Safety Rules

- Be conservative. Prefer omission over weak inference.
- Do not infer hard constraints or strong preferences from a weak clue.
- Do not turn a single mention into a strong signal.
- Do not treat adjacent or related text as evidence unless it directly supports the field.
- Do not promote education, exposure, or context into professional experience without clear support.

## Eligibility and Blocking Rules

- These rules apply to both vacancy extraction and candidate/CV extraction.
- The main safety risk is high false negatives in eligibility filtering.
- Be biased toward recall over precision for blocker-like fields.
- Prefer under-blocking to over-blocking.
- Do not create a hard blocker from ambiguous, weak, or indirect evidence.
- If a blocker-like field is unclear, place it in a softer bucket when available, or leave it unset.

### Blocker-Like Fields

These rules apply especially to fields such as:
- role titles used for eligibility
- education requirements
- years of experience
- languages
- technical core requirements
- domain or industry requirements
- work authorization
- export control or security constraints
- on-site or location constraints
- driving license or travel constraints

### Vacancy Classification Rules

- Classify an item as `required` only when the vacancy text makes it explicit.
- Strong explicit signals include wording such as:
  - `required`
  - `must`
  - `need to have`
  - `mandatory`
  - `essential`
- Classify an item as `preferred` when the vacancy uses softer wording such as:
  - `preferred`
  - `nice to have`
  - `plus`
  - `bonus`
  - `pré`
- Do not infer `required` from general role context, adjacent text, or industry assumptions.
- Do not promote a likely expectation into a hard requirement unless the text clearly supports it.
- Preserve evidence for every extracted `required` item.

### Candidate / CV Extraction Rules

- Extract only what the candidate clearly demonstrates from the CV text.
- Do not infer that the candidate has a requirement-level qualification from weak clues, exposure, or nearby context.
- Do not promote education, tool exposure, or one-off mention into strong professional capability without support.
- Do not assume a candidate satisfies a blocker unless the CV provides direct evidence.
- If the CV suggests a capability weakly, keep the extraction conservative and lower confidence accordingly.

### Evidence and Confidence for Blockers

- Every blocker-like extraction must have direct supporting evidence.
- Evidence for blocker-like fields should be especially short, precise, and relevant.
- Confidence must follow evidence strength.
- High confidence for blocker-like fields requires explicit and direct textual support.
- Lower confidence is required when support is indirect, partial, or inferred conservatively.

### Default Decision Rule

- If unsure whether a blocker-like item is truly hard-required or clearly satisfied, do not strengthen it.
- Ambiguous vacancy text must not become `required`.
- Ambiguous CV evidence must not become a strong candidate claim.
