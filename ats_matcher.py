"""
ats_matcher.py
--------------
Calculates an ATS-style keyword match score between a resume
and a job description using TF-IDF + Cosine Similarity.
"""
import re
from typing import Tuple, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _clean(text: str) -> str:
    """Lowercase and strip non-alphanumeric characters."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_keywords(text: str) -> set:
    """Return a set of meaningful words (no stop-words) from a block of text."""
    # Simple stop-word list for comparison
    stop_words = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "that", "this",
        "from", "by", "as", "it", "its", "not", "we", "you", "i",
    }
    words = set(_clean(text).split())
    return words - stop_words


def calculate_similarity(resume_text: str, job_description: str) -> Tuple[float, List[str]]:
    """
    Compute how closely a resume matches a job description using TF-IDF cosine similarity.

    Args:
        resume_text:     Plain text of the candidate's resume.
        job_description: Plain text of the target job description.

    Returns:
        A tuple of:
            score (float)          – similarity percentage from 0 to 100.
            missing_keywords (list) – important JD keywords absent from the resume.
    """
    if not resume_text.strip() or not job_description.strip():
        return 0.0, []

    cleaned_resume = _clean(resume_text)
    cleaned_jd = _clean(job_description)

    # --- TF-IDF Cosine Similarity ---
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform([cleaned_resume, cleaned_jd])
    except ValueError:
        # Happens when texts are empty after stop-word removal
        return 0.0, []

    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    score = round(float(similarity[0][0]) * 100, 1)

    # --- Missing Keywords ---
    resume_keywords = _extract_keywords(resume_text)
    jd_keywords = _extract_keywords(job_description)
    missing = sorted(jd_keywords - resume_keywords)

    # Filter to words with 4+ characters for relevance; cap at 20
    missing_filtered = [w for w in missing if len(w) >= 4][:20]

    return score, missing_filtered
