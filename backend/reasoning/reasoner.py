import json
import time
from groq import Groq


# ─────────────────────────────────────────────
# LLM REASONING
# Uses Groq/Llama for development
# Swap client for Anthropic in production
# ─────────────────────────────────────────────

def build_reasoning_prompt(jd_text, cv):
    from ranker.ranker import build_cv_summary
    candidate_text = build_cv_summary(cv, max_total_chars=2000)

    return f"""You are a recruitment assistant analyzing a candidate's fit for a job.

CRITICAL RULES:
- Base your analysis ONLY on the candidate text provided below.
- Do NOT infer, assume, or add any skill, tool, or experience not explicitly written in the candidate text.
- If something the JD asks for is not in the candidate text, treat it as a gap.
- Every strength must be traceable to specific words in the candidate text.

JOB DESCRIPTION:
{jd_text}

CANDIDATE TEXT:
{candidate_text}

Respond ONLY with valid JSON in this exact format, no other text:

{{
  "fit_summary": "2-3 sentence overview of how well this candidate fits the role",
  "strengths": ["strength 1 with evidence", "strength 2", "strength 3"],
  "gaps": ["gap 1", "gap 2"],
  "recommendation": "Strong Yes" or "Yes" or "Maybe" or "No"
}}"""


def get_llm_reasoning(jd_text, cv, client):
    prompt = build_reasoning_prompt(jd_text, cv)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=700,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response.choices[0].message.content

    try:
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return None


def run_reasoning_on_candidates(jd_text, ranked_candidates, client, delay=2):
    results = []

    for i, (filename, cv, score) in enumerate(ranked_candidates, 1):
        print(f"Processing {i}/{len(ranked_candidates)}: {cv['name']} ({score}%)...")

        reasoning = get_llm_reasoning(jd_text, cv, client)

        cv["reasoning"] = reasoning if reasoning else {
            "fit_summary": "Could not generate reasoning — LLM error.",
            "strengths":   [],
            "gaps":        [],
            "recommendation": "Maybe"
        }

        results.append((filename, cv, score))
        time.sleep(delay)

    return results