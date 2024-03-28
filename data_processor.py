from bs4 import BeautifulSoup
import re

def clean_html_and_markdown(text):
    # Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()

    # Basic Markdown cleaning (for more complex Markdown, consider using a library)
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # remove markdown links
    text = re.sub(r'\*\*?(.*?)\*\*?', r'\1', text)  # remove bold and italic
    text = re.sub(r'`{1,3}(.*?)`{1,3}', '', text)  # remove inline code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # remove code blocks
    text = re.sub(r'~~(.*?)~~', r'\1', text)  # remove strikethrough
    text = re.sub(r'\n{2,}', '\n', text)  # remove extra newlines

    return text.strip()

def remove_code_snippets(text):
    # Remove text that looks like code (simplified example)
    # You might need more sophisticated heuristics or parsing
    text = re.sub(r'^\s*[a-zA-Z_]+\(.*?\)\s*{', '', text, flags=re.MULTILINE)  # function-like lines
    # NOTE: probably not this one, as it would remove too much text
    text = re.sub(r'^\s*(if|for|while|switch)\s+.*', '', text, flags=re.MULTILINE)  # control structures
    return text

def remove_templates(text, templates):
    for template in templates:
        text = text.replace(template, '')
    return text

def retain_natural_language(text):
    # Use NLP or simpler heuristics to retain sentences likely to be natural language
    # For example, using spaCy to check for verbs in sentences
    import spacy
    nlp = spacy.load('en_core_web_sm')
    sentences = text.split('\n')
    retained_text = []
    for sentence in sentences:
        doc = nlp(sentence)
        if any(token.pos_ == 'VERB' for token in doc):
            retained_text.append(sentence)
    return '\n'.join(retained_text)

def clean_issue_text(text, templates):
    text = clean_html_and_markdown(text)
    text = remove_code_snippets(text)
    text = remove_templates(text, templates)
    text = retain_natural_language(text)
    return text
