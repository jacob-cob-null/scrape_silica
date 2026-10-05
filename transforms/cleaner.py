import re
import ftfy

def clean_text(raw_content: str) -> str | None:
    """
    Applies the 6-stage filter cascade to a raw content string.
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
        return None # Only drop completely empty comments

    # 5. Lexical Diversity (Removed)
    # Social media comments are often short or repetitive ("wow wow wow").
    # We no longer drop them for low lexical diversity.

    # 6. Alphabetic Density (Relaxed)
    # We allow heavy emoji use, but still drop comments that are 100% pure punctuation
    alphanumeric_chars = sum(c.isalnum() for c in text)
    if alphanumeric_chars == 0:
        return None

    return text
