The current VacancyProfile only contains role_titles, so the impact analysis should describe the full expansion of the model, not just two field edits.
# Software Impact Analysis

## Summary
Expand `VacancyProfile` from a minimal role-title-only model to a full must-have vacancy profile model.

## Current Model
```python
class VacancyProfile(BaseModel):
    role_titles: RoleTitles
Proposed Model Change
class VacancyProfile(BaseModel):
    role_titles: RoleTitles
    education: EducationRequirements
    experience: ExperienceRequirements
    languages: ClassifiedTexts
    technical_core_requirements: ClassifiedTexts
    domain_or_industry_requirements: RequirementTexts
    work_mode_constraints: WorkModeConstraints
    mobility_constraints: MobilityConstraints
    legal_and_compliance_constraints: LegalComplianceConstraints
New Supporting Models
class ClassifiedTexts(BaseModel):
    required: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)

class EducationRequirements(BaseModel):
    min_level: str | None = None
    accepted_fields: list[str] = Field(default_factory=list)

class ExperienceRequirements(BaseModel):
    min_years: int | None = None
    seniority_band: str | None = None

class RequirementTexts(BaseModel):
    required: list[str] = Field(default_factory=list)

class WorkModeConstraints(BaseModel):
    onsite: bool | None = None
    hybrid: bool | None = None
    remote: bool | None = None
    location: list[str] = Field(default_factory=list)

class MobilityConstraints(BaseModel):
    travel_required: bool | None = None
    driving_license_required: bool | None = None

class LegalComplianceConstraints(BaseModel):
    work_authorization_required: bool | None = None
    export_control_required: bool | None = None
    background_check_required: bool | None = None
    security_clearance_required: bool | None = None
Main Semantic Change

The model changes from:

identifying the vacancy role only

to:

identifying the role
extracting the common must-have eligibility signals
separating hard blockers from softer preferences

Most importantly:

languages changes from a flat list to:
required
preferred
technical_core_requirements changes from a flat list to:
required
preferred
Software Impact
Schema layer
vacancy_profile_model.py must be extended with the new nested models and validators.
Prompt / extraction layer
the extractor must classify vacancy statements into the new fields instead of returning only role_titles
it must distinguish explicit must-have wording from preferred wording
Validation layer
validation rules must allow empty optional sections but reject malformed structures
normalization and deduplication logic must be reused for nested text lists
Eligibility layer
hard filtering must use:
role_titles
education
experience
languages.required
technical_core_requirements.required
explicit legal / work-mode / mobility blockers
Ranking layer
only preferred items should affect fit scoring
preferred items must not reject a vacancy
Backward compatibility
any code assuming VacancyProfile contains only role_titles will break and must be updated
any downstream code expecting flat languages or flat technical_core_requirements must be migrated
Risks
vague vacancy wording may cause wrong classification between required and preferred
over-extraction may turn soft signals into blockers
under-extraction may weaken eligibility precision
Recommendation

Apply this as one coordinated model change now. Do not add only languages and technical_core_requirements first, because downstream code will otherwise be written against an incomplete shape and require another migration immediately after.


===============
## Additional Impact: Common Extraction Rules Integration

This model change also requires the vacancy profiler to adopt the shared extraction rules as a first-class dependency.

### Why
The expanded must-have model introduces more blocker-like fields such as:
- education
- experience
- languages.required
- technical_core_requirements.required
- legal and work constraints

Without shared extraction rules, these fields may be extracted with inconsistent strictness, which increases the risk of false negatives in eligibility filtering.

### Required Change
The vacancy profiler must use the common extraction rules for all extracted fields, especially blocker-like fields.

This includes:
- every extracted field must be supported by direct evidence
- confidence must be grounded in evidence quality
- extraction must be conservative
- weak clues must not become hard constraints
- ambiguous text must not be promoted into `required`
- required/preferred classification must follow explicit wording in the vacancy text

### Software Impact
- **Prompt layer**
  - the vacancy profiler system/user prompts must include or reference the shared extraction rules
- **Shared extraction contract**
  - vacancy profiling should depend on the same common extraction guidance used by other profilers, instead of embedding local ad-hoc rules
- **Consistency**
  - all must-have fields must follow one shared evidence/confidence/safety policy
- **False-negative control**
  - the shared rules become part of the mitigation against over-blocking in eligibility

### Recommendation
Do not implement the expanded vacancy profile model without wiring in the shared extraction rules at the same time. The schema defines the output shape, but the shared rules control the quality and safety of the extracted blockers.