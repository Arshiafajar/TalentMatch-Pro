from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ─────────────────────────────────────────────
# EMBEDDING MODEL
# Loaded once at startup, reused for all requests
# ─────────────────────────────────────────────

model = SentenceTransformer('all-MiniLM-L6-v2')


def build_cv_summary(cv, max_total_chars=1200):
    field_limits = {
        "summary":        150,
        "skills_raw":     300,
        "experience_raw": 500,
        "education_raw":  150,
        "projects_raw":   200,
        "certifications": 100,
        "languages":      50
    }

    parts = []
    for field, limit in field_limits.items():
        content = cv.get(field, "").strip()
        if content:
            parts.append(content[:limit])

    summary = "\n".join(parts)
    return summary[:max_total_chars]


def embed_cvs(all_cvs):
    for filename, cv in all_cvs.items():
        summary        = build_cv_summary(cv)
        cv["embedding"] = model.encode(summary)
    return all_cvs


def rank_candidates(jd_text, all_cvs, top_n=20):
    jd_vector = model.encode(jd_text).reshape(1, -1)

    results = []
    for filename, cv in all_cvs.items():
        if "embedding" not in cv:
            summary        = build_cv_summary(cv)
            cv["embedding"] = model.encode(summary)

        cv_vector  = cv["embedding"].reshape(1, -1)
        similarity = cosine_similarity(jd_vector, cv_vector)[0][0]
        score      = round(float(similarity * 100), 1)
        results.append((filename, cv, score))

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_n]