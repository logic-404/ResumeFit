from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

# Cover-letter craft knowledge, kept as an editable markdown skill alongside
# this prompt. Loaded once at import. Frontmatter stripped; braces doubled so
# the text is inert under ChatPromptTemplate's f-string formatting.
_SKILL_MD = (Path(__file__).parent / "SKILL.md").read_text(encoding="utf-8")
if _SKILL_MD.startswith("---"):
    _SKILL_MD = _SKILL_MD.split("---", 2)[-1]
_CRAFT_GUIDE = _SKILL_MD.strip().replace("{", "{{").replace("}", "}}")

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _CRAFT_GUIDE),
        (
            "system",
            "Write a tailored cover letter. Rules:\n"
            "1. Opening: name the role + company explicitly. Show specific awareness "
            "of what they do (use the company facts if provided).\n"
            "2. Body: 2-3 paragraphs covering the candidate's strongest matched "
            "skills with concrete evidence drawn from the retrieved resume bullets. "
            "If transferable skills are listed, frame positively.\n"
            "3. Do NOT mention missing skills or gaps.\n"
            "4. Closing: express enthusiasm + suggest next step.\n"
            "5. Tone: professional, warm. Length: 250-350 words.\n"
            "6. Use JD keywords naturally — don't keyword-stuff.\n"
            "7. Do not invent experience, companies, dates, or numbers.",
        ),
        (
            "human",
            "Candidate name: {full_name}\n\n"
            "Parsed JD:\n{parsed_jd}\n\n"
            "Gap analysis:\n{gap_analysis}\n\n"
            "Retrieved resume evidence (use these bullets verbatim or paraphrased):\n"
            "{retrieval_block}\n\n"
            "Company facts (may be empty):\n{company_facts}\n\n"
            "Write the cover letter.",
        ),
    ]
)
