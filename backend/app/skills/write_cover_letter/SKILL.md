---
name: write-cover-letter
description: Cover-letter writing craft for the cover-letter step. Use when drafting a tailored cover letter from a parsed JD, gap analysis, retrieved resume evidence, and optional company facts — covers the hook, achievement-focused body, personalisation, tone/length, and what to avoid. Augments the write_cover_letter prompt; does not change pipeline logic, schema, or retrieval.
---

# write-cover-letter

You write a one-page, tailored cover letter. You receive the candidate's name,
the parsed JD, the gap analysis, retrieved resume bullets (your only source of
evidence), and possibly a few company facts. The surrounding pipeline owns the
output schema and the single-call + regenerate flow — this is craft guidance.

## Shape (3–4 short paragraphs, 250–350 words, one page)

1. **Header / greeting** — candidate name; address a person if known, else a
   role-specific greeting ("Dear Hiring Team"). Never "To whom it may concern".
2. **Hook** — open by naming the **role and company explicitly**, then land one
   of: a quantified achievement that maps to the JD's top requirement; a sharp
   statement of a problem the company has that the candidate can solve; a
   genuine, specific reason this company (use the company facts if provided).
   No "I am writing to apply for…".
3. **Body (1–2 paragraphs)** — the candidate's 2–4 strongest **matched** skills,
   each backed by concrete evidence from the retrieved resume bullets
   (verbatim or paraphrased). Lead with outcomes and numbers. Frame transferable
   skills positively. Tie each point back to a JD need — "you need X; here's
   where I did X."
4. **Close** — short. Restate fit in one line, express specific enthusiasm,
   propose a next step (a conversation/interview). Formal sign-off.

## Personalise — recruiters scan for alignment

- Mirror the JD's language for hard skills/tools; weave JD keywords in
  naturally, never stuff.
- Use the company facts to show you know what they do — a product, a recent
  launch, the mission. One concrete reference beats three vague compliments.
- Put the strongest JD-match in the first 2 sentences; recruiters skim.

## Don't

- **Don't restate the resume.** Go deeper on 2–4 stories; don't summarise the
  bullet list. A letter that reads like the resume is dead weight.
- **Don't mention gaps or missing skills.** No "although I lack…", no apologies.
- **Don't be generic.** A letter that would fit any company gets discarded.
  Every paragraph should be unusable for a different posting.
- **Don't make it about you.** Frame around "what I can do for you", not "what I
  want". No salary talk, no reasons for leaving a past job, nothing negative
  about a former employer.
- **Don't fabricate.** No company, title, date, or number that isn't in the
  retrieved evidence or the JD. No invented metrics.
- **Don't run long or get cute.** ≤ ~350 words, professional-warm tone, zero
  typos, no gimmicky openers or clichés ("I'm a perfect fit", "hard worker").

## Quick self-check

- [ ] Role + company named in the opening; hook is a concrete achievement or
  company-specific reason, not boilerplate?
- [ ] 2–4 matched skills, each with evidence from the retrieved bullets, each
  tied to a JD need?
- [ ] Outcomes/numbers present where the evidence supports them; none invented?
- [ ] No gaps mentioned; nothing negative; not about the candidate's wants?
- [ ] Doesn't just paraphrase the resume; adds motivation/context?
- [ ] One page, 250–350 words, warm-professional, clean?
- [ ] Every company/date/metric traceable to the evidence or JD?
