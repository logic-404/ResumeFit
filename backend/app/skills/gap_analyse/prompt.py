from langchain_core.prompts import ChatPromptTemplate

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a career advisor performing a skills gap analysis.\n\n"
            "Definitions:\n"
            "- matched: skill explicitly demonstrated in the resume (cite which "
            "role or project in `evidence`).\n"
            "- missing: skill in required/preferred but absent from the resume.\n"
            "- transferable: a candidate skill that maps to a JD requirement "
            "even if not an exact match.\n\n"
            "The `overall_match_score` MUST be between 0.0 and 1.0. Use:\n"
            "  score = clamp((matched + 0.5*transferable) / "
            "max(1, required + 0.5*preferred), 0.0, 1.0)\n\n"
            "Be specific in evidence. Suggestions for missing skills must be "
            "actionable (e.g. specific course, project, certification).",
        ),
        (
            "human",
            "Resume context:\n{resume_text}\n\n"
            "Retrieved evidence (semantic match for each JD skill):\n{retrieval_block}\n\n"
            "Skill taxonomy notes:\n{taxonomy_block}\n\n"
            "Parsed JD:\n{parsed_jd}\n\n"
            "Produce the gap analysis.",
        ),
    ]
)
