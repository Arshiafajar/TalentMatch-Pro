import re
from datetime import datetime


# ─────────────────────────────────────────────
# BIAS AUDIT
# Flags awareness signals — not filters
# Recruiter dismisses or acknowledges each flag
# ─────────────────────────────────────────────

def run_bias_audit_smart(ranked_candidates):
    # Compute shortlist average graduation year
    grad_years = []
    for _, cv, _ in ranked_candidates:
        edu_text = cv.get("education_raw", "")
        years    = re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b', edu_text)
        if years:
            grad_years.append(max(int(y) for y in years))

    avg_grad_year = sum(grad_years) / len(grad_years) if grad_years else None

    # Session level flag — shown once
    session_flags = []
    names = [cv["name"] for _, cv, _ in ranked_candidates if cv.get("name")]
    if names:
        session_flags.append({
            "type":    "session_name_visibility",
            "message": f"This shortlist contains {len(names)} visible candidate names. Consider name-blind review for initial screening."
        })

    # Per candidate flags
    candidate_flags = {}

    for filename, cv, score in ranked_candidates:
        flags    = []
        edu_text = cv.get("education_raw", "")
        years    = re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b', edu_text)

        if years and avg_grad_year:
            candidate_grad = max(int(y) for y in years)
            diff           = avg_grad_year - candidate_grad

            if diff > 10:
                flags.append({
                    "type":    "age_outlier_older",
                    "message": f"Graduated ~{int(diff)} years before shortlist average ({candidate_grad} vs avg {int(avg_grad_year)}). Be mindful of age-related assumptions."
                })
            elif diff < -5:
                flags.append({
                    "type":    "age_outlier_younger",
                    "message": f"Graduated ~{abs(int(diff))} years after shortlist average ({candidate_grad} vs avg {int(avg_grad_year)}). Be mindful of assumptions about experience level."
                })

        if cv.get("total_years_experience", 0.0) == 0.0:
            flags.append({
                "type":    "experience_unverified",
                "message": "Years of experience could not be computed. Manually verify experience claims."
            })

        if cv.get("education_raw", "").strip():
            flags.append({
                "type":    "institution_visible",
                "message": "Institution name visible. Evaluate based on demonstrated skills, not institutional prestige."
            })

        candidate_flags[filename] = flags

    return session_flags, candidate_flags