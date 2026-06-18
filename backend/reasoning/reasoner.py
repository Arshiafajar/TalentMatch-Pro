import asyncio
import json
import time
from groq import Groq
from ranker.ranker import build_cv_summary

def build_reasoning_prompt(jd_text, cv):
    candidate_text = build_cv_summary(cv, max_total_chars=2000)
    return f"""You are a recruitment assistant analyzing a candidate's fit for a job.
CRITICAL RULES:
- Base your analysis ONLY on the candidate text provided below.
- Do NOT infer, assume, or add any skill not explicitly written.
JOB DESCRIPTION:
{jd_text}
CANDIDATE TEXT:
{candidate_text}
Respond ONLY with valid JSON in this exact format:
{{
  "fit_summary": "2-3 sentence overview",
  "strengths": ["strength 1 with evidence", "strength 2"],
  "gaps": ["gap 1", "gap 2"],
  "recommendation": "Strong Yes" or "Yes" or "Maybe" or "No"
}}"""

async def get_llm_reasoning_async(jd_text, cv, client):
    prompt = build_reasoning_prompt(jd_text, cv)
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=700,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        
        # Clean markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1].replace("json", "").strip()
        
        return json.loads(raw)
    except Exception:
        return None

async def run_reasoning_on_candidates_async(jd_text, ranked_candidates, client, max_concurrent=8):
    results = []
    tasks = []
    
    for filename, cv, score in ranked_candidates:
        task = get_llm_reasoning_async(jd_text, cv, client)
        tasks.append((filename, cv, score, task))
    
    # Process in batches to respect rate limits
    for i in range(0, len(tasks), max_concurrent):
        batch = tasks[i:i + max_concurrent]
        print(f"Processing batch {i//max_concurrent + 1}...")
        
        batch_results = await asyncio.gather(*[t[3] for t in batch])
        
        for (filename, cv, score, task), reasoning in zip(batch, batch_results):
            cv["reasoning"] = reasoning if reasoning else {
                "fit_summary": "Could not generate reasoning.",
                "strengths": [],
                "gaps": [],
                "recommendation": "Maybe"
            }
            results.append((filename, cv, score))
    
    return results

# ←←← Wrapper for sync call (FastAPI is sync)
def run_reasoning_on_candidates(jd_text, ranked_candidates, client, delay=0):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        run_reasoning_on_candidates_async(jd_text, ranked_candidates, client)
    )