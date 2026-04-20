from __future__ import annotations

from clients.candidate_profiling.candidate_profile_schema import CandidateProfileRead
from clients.candidate_profiling.candidate_profiling_model import CandidateProfileRecord

# def _to_domain_profile(
#     payload: CandidateProfileUserSchema,
# ) -> CandidateProfileModel:
#     return CandidateProfileModel(
#         role_titles=RoleTitlesModel(
#             primary=payload.role_titles.primary,
#             alternatives=payload.role_titles.alternatives,
#             **_support_kwargs(),
#         ),
#         education=EducationModel(
#             min_level=payload.education.min_level,
#             accepted_fields=payload.education.accepted_fields,
#             **_support_kwargs(),
#         ),
#         experience=ExperienceModel(
#             min_years=payload.experience.min_years,
#             seniority_band=payload.experience.seniority_band,
#             **_support_kwargs(),
#         ),
#         technical_experience=TechnicalExperienceModel(
#             technical_core_features=[
#                 _to_strength_feature_model(feature)
#                 for feature in payload.technical_experience.technical_core_features
#             ],
#             technologies=[
#                 _to_strength_feature_model(feature)
#                 for feature in payload.technical_experience.technologies
#             ],
#         ),
#         languages=[
#             _to_strength_feature_model(feature)
#             for feature in payload.languages
#         ],
#         domain_background=[
#             _to_strength_feature_model(feature)
#             for feature in payload.domain_background
#         ],
#     )

def _to_read_schema(record: CandidateProfileRecord) -> CandidateProfileRead:
    return CandidateProfileRead.model_validate(
        {
            "role_titles": record.role_titles_json,
            "education": record.education_json,
            "experience": record.experience_json,
            "technical_experience": record.technical_experience_json,
            "languages": record.languages_json,
            "domain_background": record.domain_background_json,
        }
    )
