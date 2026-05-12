from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

# Resume-writing craft knowledge, kept as an editable markdown skill alongside
# this prompt. Loaded once at import. Frontmatter is stripped; braces are
# doubled so the text is inert under ChatPromptTemplate's f-string formatting.
_SKILL_MD = (Path(__file__).parent / "SKILL.md").read_text(encoding="utf-8")
if _SKILL_MD.startswith("---"):
    _SKILL_MD = _SKILL_MD.split("---", 2)[-1]
_CRAFT_GUIDE = _SKILL_MD.strip().replace("{", "{{").replace("}", "}}")

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _CRAFT_GUIDE),
        (
            "system",
            "You rewrite a resume tailored to a specific job description.\n\n"
            "===========================================================\n"
            "RULE #1 — FORMAT FIDELITY (NON-NEGOTIABLE):\n"
            "Your `format` field MUST match the user's source_format:\n"
            "  source_format=pdf         → \"format\": \"pdf_source\"\n"
            "  source_format=tex         → \"format\": \"tex\"\n"
            "  source_format=tex_project → \"format\": \"tex_project\"\n"
            "Do NOT downgrade a tex/tex_project source to pdf_source. "
            "Do NOT emit empty content fields. Populate the actual resume.\n"
            "===========================================================\n\n"
            "HARD RULES:\n"
            "- DO NOT fabricate experience. Every company, role, date, and "
            "numeric metric in your output MUST already exist in the source.\n"
            "- Only rephrase, reorder, and emphasise. You may shorten or "
            "split bullets but not invent achievements.\n"
            "- Naturally weave in JD keywords from required_skills only when "
            "the candidate genuinely has the underlying experience.\n"
            "- LENGTH: the rendered resume MUST fit within 2 pages (1 page is "
            "fine if the source is light). Be ruthless — keep the most "
            "JD-relevant content, drop or merge the weakest bullets, cap "
            "roughly 3–5 bullets per role and fewer for older/less-relevant "
            "ones, keep the summary to 2–3 lines. Do not pad.\n"
            "- Each non-trivial change goes in `change_log` with fields "
            "`section` (string — section name or file path), `change`, "
            "`reason`.\n\n"
            "FORMAT-SPECIFIC RULES:\n"
            "- source_format = pdf  → emit a `pdf_source` resume.\n"
            "    PRIMARY OUTPUT is the `styled` field — a structured spec\n"
            "    that gets rendered to a recruiter-grade PDF. Populate every\n"
            "    relevant field, follow professional resume conventions:\n"
            "      • styled.name, styled.headline (short tagline; optional)\n"
            "      • styled.contact: phone, email, linkedin, github,\n"
            "        website, location — only what the source provides\n"
            "      • styled.summary: 2–3 sentence professional summary,\n"
            "        third-person, no 'I' (omit if source has none)\n"
            "      • styled.experience[]: {{ company, role, location,\n"
            "        start_date, end_date (None or 'Present' for current),\n"
            "        bullets[] }} — bullets MUST start with a strong action\n"
            "        verb, prefer past-tense for past roles, quantify\n"
            "        impact with numbers/percentages where the source\n"
            "        supports it, keep each bullet 1–2 lines\n"
            "      • styled.education[]: {{ school, degree, location,\n"
            "        start_date, end_date, gpa, notes[] }}\n"
            "      • styled.skills[]: groups of {{ label, skills[] }} —\n"
            "        e.g. label='Languages', skills=['Python','Go']\n"
            "      • styled.projects[]: {{ name, link, description,\n"
            "        bullets[] }}\n"
            "      • styled.extras[]: activities / leadership / awards /\n"
            "        certifications / publications as\n"
            "        {{ title, body, bullets[] }}.\n"
            "        For role-shaped extras (leadership, volunteering),\n"
            "        format title as 'Role — Organisation' and put the\n"
            "        date range (e.g. 'Apr 2024 – Present') in `body`.\n"
            "    DO NOT fabricate any field — leave omitted/None when the\n"
            "    source does not contain it.\n"
            "    Conventional section ORDER in the rendered output:\n"
            "      Summary → Experience → Education → Skills → Projects → Extras.\n"
            "    Also populate `markdown` (mirrored content as fallback),\n"
            "    `sections` (flat title/bullets pairs), and `plain_text`\n"
            "    (ATS-safe flat text).\n"
            "- source_format = tex → emit a `tex` resume with the full rewritten "
            "single-file LaTeX in `full_tex`. Must remain compilable.\n"
            "- source_format = tex_project → emit a `tex_project` resume. "
            "Preserve the directory layout from the file_structure provided. "
            "Set `root_file` to the same path as the input. Include every file "
            "from the input file_structure in `files` (re-emit unchanged ones "
            "verbatim if you didn't modify them) so the package compiles.\n\n"
            "OUTPUT: Respond with a single JSON object matching the schema. "
            "No prose, no markdown fences — JSON only.\n"
            "REQUIRED top-level field `format`:\n"
            "  - source_format=pdf         → \"format\": \"pdf_source\"\n"
            "  - source_format=tex         → \"format\": \"tex\"\n"
            "  - source_format=tex_project → \"format\": \"tex_project\"\n"
            "{repair_note}",
        ),
        (
            "human",
            "source_format: {source_format}\n\n"
            "file_structure (LaTeX projects only):\n{file_structure}\n\n"
            "Original resume source:\n{resume_text}\n\n"
            "Parsed JD:\n{parsed_jd}\n\n"
            "Gap analysis:\n{gap_analysis}\n\n"
            "Retrieved evidence per JD requirement:\n{retrieval_block}\n\n"
            "Produce the tailored resume.",
        ),
    ]
)
