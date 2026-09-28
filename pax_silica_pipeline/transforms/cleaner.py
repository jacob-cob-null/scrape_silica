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

    # 4. Length Floor
    tokens = text.split()
    chars = len(text)
    
    root_words = {'kuryente', 'tubig', 'bpo', 'china', 'sahod'}
    has_root_word = any(word.lower() in root_words for word in tokens)
    
    if len(tokens) < 4 or chars < 20:
        if not (len(tokens) >= 2 and has_root_word):
            return None

    # 5. Lexical Diversity
    if len(tokens) == 0:
        return None
    unique_tokens = len(set(tokens))
    if (unique_tokens / len(tokens)) < 0.35:
        return None

    # 6. Alphabetic Density
    if chars == 0:
        return None
    alphanumeric_chars = sum(c.isalnum() for c in text)
    if (alphanumeric_chars / chars) < 0.50:
        return None

    return text
