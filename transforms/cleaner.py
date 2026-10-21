import re
import ftfy

try:
    from langdetect import detect
except ImportError:
    detect = None

# Anchors that indicate high-signal project or geographic relevance
ANCHOR_RE = re.compile(
    r'\b(pax\s*silica|paxsilica|clark|tarlac|luzon|pilipinas|bayan|aeta|bcda|peza)\b',
    re.IGNORECASE
)

# Supported target languages for Philippine netizen discourse
TARGET_LANGS = {'en', 'tl', 'fil', 'ceb', 'id'}


def is_target_language(text: str) -> bool:
    """
    Language gate filtering out foreign language leakage (e.g. European tweets/posts)
    while strictly preserving English, Filipino/Tagalog, Taglish, Cebuano, and
    short project anchor expressions (e.g., 'No to pax silica').
    """
    if not text or not text.strip():
        return False

    # Anchor safeguard: if it explicitly names the project or location, keep it!
    if ANCHOR_RE.search(text):
        # Guard against PEZA homonym (e.g. Spanish/Galician 'peza' meaning 'piece'/'player')
        # Only gate if 'peza' is present without other Philippine context anchors
        if re.search(r'\bpeza\b', text, re.IGNORECASE) and not re.search(
            r'\b(pax|philippines|pilipinas|clark|tarlac|luzon|economic|bayan|aeta|bcda)\b',
            text,
            re.IGNORECASE,
        ):
            if detect is None:
                return True
            try:
                return detect(text) in TARGET_LANGS
            except Exception:
                return False
        return True

    cleaned = re.sub(r'[^\w\s]', '', text).strip()
    # Allow short social reactions (< 4 tokens) that statistical detectors struggle with
    if len(cleaned.split()) < 4:
        return True

    if detect is None:
        return True

    try:
        lang = detect(text)
        return lang in TARGET_LANGS
    except Exception:
        return True


def clean_text(raw_content: str) -> str | None:
    """
    Applies the 7-stage filter cascade to a raw content string.
    Returns the cleaned string, or None if it fails any stage.
    """
    if not isinstance(raw_content, str):
        return None

    # 1. Encoding Repair
    text = ftfy.fix_text(raw_content)

    # 2. PII Scrubbing
    # Strip @mentions
    text = re.sub(r'@\w+', '', text)
    # Strip phone numbers (basic pattern)
    text = re.sub(r'\+?\d[\d -]{8,12}\d', '', text)
    # Strip email addresses
    text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '', text)

    # 3. Formatting Strip
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove Markdown link syntax: [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)

    text = text.strip()

    # 4. Length Floor (Relaxed to allow short comments)
    tokens = text.split()
    chars = len(text)

    if len(tokens) < 1 or chars == 0:
        return None  # Only drop completely empty comments

    # 5. Lexical Diversity (Removed)
    # Social media comments are often short or repetitive ("wow wow wow").
    # We no longer drop them for low lexical diversity.

    # 6. Alphabetic Density (Relaxed)
    # We allow heavy emoji use, but still drop comments that are 100% pure punctuation
    alphanumeric_chars = sum(c.isalnum() for c in text)
    if alphanumeric_chars == 0:
        return None

    # 7. Language Gate
    # Drops foreign language noise (e.g. European soccer tweets matching 'peza' homonym)
    # while strictly preserving English, Tagalog, Taglish, and Cebuano discourse,
    # with an anchor safeguard for critical project/location tokens (e.g. 'No to pax silica').
    if not is_target_language(text):
        return None

    return text
