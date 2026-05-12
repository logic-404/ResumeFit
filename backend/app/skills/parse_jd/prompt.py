from langchain_core.prompts import ChatPromptTemplate

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Extract structured data from a job description. Rules:\n"
            "- Only list skills/responsibilities explicitly mentioned. Do not infer.\n"
            "- Classify experience_level by years required and seniority language.\n"
            "- Separate required vs preferred skills based on the JD's own wording.\n"
            "- If a field is not present, omit it.",
        ),
        ("human", "Parse this job description:\n\n{jd_text}"),
    ]
)
