import re


# ─────────────────────────────────────────────
# JD PARSER
# Rule-based extraction for structured fields
# Skills and domain keywords handled by LLM
# ─────────────────────────────────────────────

def extract_min_experience(text):
    patterns = [
        r'(\d+)\+\s*years',
        r'minimum\s+(\d+)\s*years',
        r'at\s+least\s+(\d+)\s*years',
        r'(\d+)\s*[-–]\s*\d+\s*years',
        r'(\d+)\s*years\s*of\s*experience',
        r'experience\s*of\s*(\d+)\+?\s*years',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def extract_education_requirement(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["phd", "ph.d", "doctorate", "doctoral"]):
        return "phd"
    if any(w in text_lower for w in ["master", "msc", "m.sc", "mba", "m.s."]):
        return "master"
    if any(w in text_lower for w in ["bachelor", "bsc", "b.sc", "b.s.", "undergraduate", "degree"]):
        return "bachelor"
    if any(w in text_lower for w in ["diploma", "associate"]):
        return "diploma"
    return None


def extract_role_level(text, min_years=None):
    lines      = [l.strip() for l in text.splitlines() if l.strip()]
    title_text = " ".join(lines[:3]).lower()

    if any(w in title_text for w in ["lead", "principal", "head of", "director", "vp ", "vice president"]):
        return "lead"
    if any(w in title_text for w in ["senior", "sr.", "sr "]):
        return "senior"
    if any(w in title_text for w in ["junior", "jr.", "entry level", "entry-level", "intern", "summer"]):
        return "junior"
    if any(w in title_text for w in ["mid level", "mid-level", "intermediate"]):
        return "mid"

    if min_years is not None:
        if min_years <= 1:   return "junior"
        elif min_years <= 4: return "mid"
        elif min_years <= 7: return "senior"
        else:                return "lead"

    return "mid"


def parse_jd(jd_text):
    if not jd_text.strip():
        return None

    min_years  = extract_min_experience(jd_text)
    role_level = extract_role_level(jd_text, min_years)

    return {
        "min_experience_years":  min_years,
        "education_requirement": extract_education_requirement(jd_text),
        "role_level":            role_level,
        "raw_text":              jd_text.strip()
    }