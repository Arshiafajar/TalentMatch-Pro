import pdfplumber
import re
import glob
from datetime import datetime


# ─────────────────────────────────────────────
# SECTION DETECTION
# ─────────────────────────────────────────────

SECTION_HEADERS = {
    "experience":     ["experience", "work experience", "work experiences", "employment history", "career history"],
    "education":      ["education", "academic background", "qualifications"],
    "skills":         ["skills", "technical skills", "core competencies", "technologies"],
    "certifications": ["certification", "certifications", "licenses", "certificates"],
    "achievements":   ["achievement", "achievements", "awards", "honors"],
    "projects":       ["project", "projects", "key projects", "personal projects", "academic projects"],
    "languages":      ["languages", "language proficiency"],
    "summary":        ["summary", "objective", "profile", "about me", "professional summary"],
    "references":     ["references", "referees"],
    "interests":      ["interests", "hobbies", "volunteer", "extracurricular"]
}


def detect_section(line):
    line_stripped = line.strip()
    line_lower    = line_stripped.lower()

    if len(line_stripped) > 40:
        return None

    for section, keywords in SECTION_HEADERS.items():
        for keyword in keywords:
            if line_lower.startswith(keyword):
                return section
    return None


def split_sections(text):
    sections = {
        "experience":     "",
        "education":      "",
        "skills":         "",
        "certifications": "",
        "achievements":   "",
        "projects":       "",
        "languages":      "",
        "summary":        "",
        "references":     "",
        "interests":      ""
    }

    current_section = None

    for line in text.splitlines():
        detected = detect_section(line)
        if detected:
            current_section = detected
        elif current_section:
            sections[current_section] += line + "\n"

    return sections


# ─────────────────────────────────────────────
# READ PDF
# ─────────────────────────────────────────────

def read_cv(path_to_file):
    try:
        text = ""
        with pdfplumber.open(path_to_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Could not read file: {path_to_file} — {e}")
        return None


# ─────────────────────────────────────────────
# GLOBAL FIELDS
# ─────────────────────────────────────────────

def extract_global(text):
    data  = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    data["name"]  = lines[0] if lines else None

    email         = re.findall(r'[\w.\-+]+@[\w.\-]+\.\w+', text)
    data["email"] = email[0] if email else None

    phone         = re.findall(r'(\+?\d[\d\s\-]{8,15})', text)
    data["phone"] = phone[0].strip() if phone else None

    links         = re.findall(r'https?://\S+', text)
    data["links"] = links if links else []

    return data


# ─────────────────────────────────────────────
# SKILLS
# Keyword list = quick pre-filter signal only
# skills_raw   = full text, LLM reads this
# ─────────────────────────────────────────────

SKILLS_KEYWORDS = [
    "python", "sql", "excel", "power bi", "tableau",
    "machine learning", "deep learning", "nlp",
    "tensorflow", "pytorch", "scikit-learn", "keras",
    "java", "javascript", "react", "node.js",
    "data analysis", "data visualization",
    "statistics", "spark", "hadoop",
    "git", "docker", "aws", "azure", "gcp",
    "automation", "etl", "pandas", "numpy",
    "communication", "leadership", "project management",
    "mongodb", "postgresql", "mysql", "bigquery",
    "looker", "dbt", "airflow", "kubernetes",
    "opencv", "computer vision", "streamlit", "fastapi"
]


def extract_skills(skills_section_text, full_text=""):
    search_text = skills_section_text.strip() if skills_section_text.strip() else full_text
    found = []
    for skill in SKILLS_KEYWORDS:
        if len(skill) <= 2:
            pattern = rf'\b{re.escape(skill)}\b'
            if re.search(pattern, search_text, re.IGNORECASE):
                found.append(skill)
        else:
            if skill.lower() in search_text.lower():
                found.append(skill)
    return found


# ─────────────────────────────────────────────
# EXPERIENCE YEARS COMPUTATION
# ─────────────────────────────────────────────

def compute_years_experience(experience_raw):
    if not experience_raw.strip():
        return 0.0

    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "may": 5, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    date_token    = r'([A-Za-z]+\s+\d{4}|\d{2}/\d{4}|\d{4})'
    separator     = r'\s*(?:[–—\-]+|to)\s*'
    present_token = r'(present|current|now)'

    full_pattern = re.compile(
        rf'{date_token}{separator}(?:{date_token}|{present_token})',
        re.IGNORECASE
    )

    def parse_date_token(token):
        token = token.strip()
        if not token:
            return None
        if token.lower() in ["present", "current", "now"]:
            return datetime.today()
        if re.match(r'^\d{2}/\d{4}$', token):
            parts = token.split('/')
            month = int(parts[0])
            year  = int(parts[1])
            if 1 <= month <= 12:
                return datetime(year, month, 1)
            return None
        parts = token.split()
        if len(parts) == 2:
            month_str = parts[0][:3].lower()
            year      = int(parts[1])
            month     = month_map.get(month_str, 6)
            return datetime(year, month, 1)
        if len(parts) == 1 and parts[0].isdigit():
            return datetime(int(parts[0]), 6, 1)
        return None

    total_months = 0

    for line in experience_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        matches = full_pattern.findall(line)
        for match in matches:
            start_str = match[0]
            end_str   = match[1] if match[1] else match[2]
            start     = parse_date_token(start_str)
            end       = parse_date_token(end_str)
            if start and end and end >= start:
                months = (end.year - start.year) * 12 + (end.month - start.month)
                if 0 < months <= 180:
                    total_months += months

    return round(total_months / 12, 1)


# ─────────────────────────────────────────────
# MAIN PROCESSOR
# ─────────────────────────────────────────────

def process_cv(text):
    global_data = extract_global(text)
    sections    = split_sections(text)

    cv = {}
    cv.update(global_data)

    cv["raw_text"]               = text.strip()
    cv["skills"]                 = extract_skills(sections["skills"], full_text=text)
    cv["skills_raw"]             = sections["skills"].strip()
    cv["experience_raw"]         = sections["experience"].strip()
    cv["education_raw"]          = sections["education"].strip()
    cv["projects_raw"]           = sections["projects"].strip()
    cv["certifications"]         = sections["certifications"].strip()
    cv["achievements"]           = sections["achievements"].strip()
    cv["languages"]              = sections["languages"].strip()
    cv["summary"]                = sections["summary"].strip()
    cv["interests"]              = sections["interests"].strip()
    cv["total_years_experience"] = compute_years_experience(sections["experience"])
    cv["extraction_quality"]     = "ok" if len(text.strip()) > 200 else "poor — check manually"

    return cv


# ─────────────────────────────────────────────
# BATCH PROCESSOR
# Processes all PDFs in a given directory
# ─────────────────────────────────────────────

def process_cv_directory(directory_path):
    pdf_files = glob.glob(f"{directory_path}/*.pdf")

    if not pdf_files:
        print(f"No PDF files found in {directory_path}")
        return {}

    all_cvs = {}

    for path in pdf_files:
        text = read_cv(path)
        if text:
            all_cvs[path] = process_cv(text)
        else:
            print(f"  ⚠ Skipped: {path}")

    print(f"Processed {len(all_cvs)} CVs from {directory_path}")
    return all_cvs


# ─────────────────────────────────────────────
# SINGLE FILE PROCESSOR
# Used by FastAPI when processing uploaded files
# ─────────────────────────────────────────────

def process_single_cv(file_path):
    text = read_cv(file_path)
    if not text:
        return None
    return process_cv(text)