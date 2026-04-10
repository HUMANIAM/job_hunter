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
