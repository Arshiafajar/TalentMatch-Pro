
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import uuid
import shutil
import os
from datetime import datetime
from groq import Groq

from parser.cv_parser  import process_single_cv
from parser.jd_parser  import parse_jd
from ranker.ranker     import rank_candidates
from reasoning.reasoner import run_reasoning_on_candidates
from bias.bias_audit   import run_bias_audit_smart




app = FastAPI(
    title="TalentMatch Pro",
    description="AI-powered CV Ranking and Screening System",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://talent-match-pro-brown.vercel.app",
        "https://*.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Groq client ────────────────────────────────

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── In-memory session store ────────────────────
sessions = {}


@app.get("/")
def root():
    return {
        "status"  : "running",
        "product" : "TalentMatch Pro",
        "version" : "1.0.0"
    }


@app.post("/session/create")
def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created_at" : datetime.now().isoformat(),
        "cvs"        : {},
        "jd"         : None,
        "results"    : None
    }
    return {"session_id": session_id}


@app.post("/session/{session_id}/upload-cvs")
async def upload_cvs(session_id: str, files: list[UploadFile] = File(...)):
    if session_id not in sessions:
        return {"error": "Session not found"}

    upload_dir = f"temp/{session_id}/cvs"
    os.makedirs(upload_dir, exist_ok=True)

    parsed_cvs = {}
    for file in files:
        file_path = f"{upload_dir}/{file.filename}"
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        cv_data = process_single_cv(file_path)
        if cv_data:
            parsed_cvs[file.filename] = cv_data

    sessions[session_id]["cvs"] = parsed_cvs

    return {
        "session_id"    : session_id,
        "cvs_processed" : len(parsed_cvs),
        "filenames"     : list(parsed_cvs.keys())
    }


class JDInput(BaseModel):
    jd_text : str
    top_n   : Optional[int] = 20

@app.post("/session/{session_id}/set-jd")
def set_jd(session_id: str, payload: JDInput):
    if session_id not in sessions:
        return {"error": "Session not found"}

    sessions[session_id]["jd"]    = payload.jd_text
    sessions[session_id]["top_n"] = payload.top_n

    return {
        "session_id" : session_id,
        "jd_length"  : len(payload.jd_text),
        "top_n"      : payload.top_n,
        "status"     : "JD saved"
    }


@app.post("/session/{session_id}/rank")
def rank(session_id: str):
    if session_id not in sessions:
        return {"error": "Session not found"}

    session = sessions[session_id]

    if not session.get("jd"):
        return {"error": "No JD set — call /set-jd first"}

    if not session.get("cvs"):
        return {"error": "No CVs uploaded — call /upload-cvs first"}

    jd_text = session["jd"]
    all_cvs = session["cvs"]
    top_n   = session.get("top_n", 20)

    # Step 1 — Rank by semantic similarity
    ranked = rank_candidates(jd_text, all_cvs, top_n=top_n)

    # Step 2 — LLM reasoning on top N
    ranked_with_reasoning = run_reasoning_on_candidates(
        jd_text, ranked, groq_client, delay=0.5
    )

    # Step 3 — Bias audit
    session_flags, candidate_flags = run_bias_audit_smart(ranked_with_reasoning)

    # Step 4 — Build results
    results = {
        "session_id"    : session_id,
        "jd_parsed"     : parse_jd(jd_text),
        "total_screened": len(all_cvs),
        "top_n"         : top_n,
        "generated_at"  : datetime.now().isoformat(),
        "session_flags" : session_flags,
        "candidates"    : [
            {
                "rank"          : rank,
                "filename"      : filename,
                "name"          : cv["name"],
                "email"         : cv["email"],
                "match_score"   : score,
                "recommendation": cv["reasoning"]["recommendation"],
                "fit_summary"   : cv["reasoning"]["fit_summary"],
                "strengths"     : cv["reasoning"]["strengths"],
                "gaps"          : cv["reasoning"]["gaps"],
                "bias_flags"    : candidate_flags.get(filename, []),
                "total_years_experience": cv["total_years_experience"]
            }
            for rank, (filename, cv, score) in enumerate(ranked_with_reasoning, 1)
        ]
    }

    sessions[session_id]["results"] = results
    return results


@app.get("/session/{session_id}/results")
def get_results(session_id: str):
    if session_id not in sessions:
        return {"error": "Session not found"}
    results = sessions[session_id].get("results")
    if not results:
        return {"error": "No results yet — call /rank first"}
    return results


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)