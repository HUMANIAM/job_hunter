Based on your current schemas, plus the missing role fields you want to add, the common must-have fields for both job and candidate should be: role_title, role_family, role_class, skills, domains, education, languages, location, workplace_type, seniority, years_experience. The current schemas already cover much of this shape for skills, languages, domains, seniority, years, location, workplace, and education, while role_family exists in the eligibility schema and role_class is the extra field to add now.


# Common fields
- *role title*: A CV or job can have multiple job titles. one is primary and others are alternatives.

For Job:
{
  "primary": "embedded software engineer",
  "alternatives": [
    "software engineer",
    "c++ software engineer"
  ]
}

For Candidate:
{
  "primary": "embedded software engineer",
  "alternatives": [
    "software engineer",
    "c++ software engineer",
    "software developer",
    "python engineer"
  ]
}


## Data Model:
from pydantic import BaseModel, Field, model_validator
from shared.normalizer import normalize_and_dedupe_texts, normalize_taxonomy_name


class RoleTitles(BaseModel):
    primary: str
    alternatives: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_titles(self) -> "RoleTitles":
        self.primary = normalize_taxonomy_name(self.primary)
        if not self.primary:
            raise ValueError("primary role title must not be empty")

        self.alternatives = [
            title
            for title in normalize_and_dedupe_texts(
                normalize_taxonomy_name(title) for title in self.alternatives
            )
            if title != self.primary
        ][:5]
        return self

# LLM instruction
