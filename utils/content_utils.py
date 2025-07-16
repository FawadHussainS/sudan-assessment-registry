import re
from html import unescape
from datetime import datetime

def clean_html_content(html_content, max_length=200):
    """
    Clean HTML content and create a readable preview
    
    Args:
        html_content (str): Raw HTML content
        max_length (int): Maximum length of preview text
        
    Returns:
        str: Clean, readable text preview
    """
    if not html_content:
        return "No content available"
    
    # Remove script and style elements completely
    html_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert common HTML elements to readable text
    html_content = re.sub(r'<br\s*/?>', ' ', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<p[^>]*>', '\n', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'</p>', '\n', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<li[^>]*>', '• ', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<h[1-6][^>]*>', '\n', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'</h[1-6]>', '\n', html_content, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_content)
    
    # Decode HTML entities
    clean_text = unescape(clean_text)
    
    # Clean up whitespace
    clean_text = re.sub(r'\n\s*\n', '\n', clean_text)  # Remove multiple newlines
    clean_text = re.sub(r'[ \t]+', ' ', clean_text)     # Remove multiple spaces/tabs
    clean_text = clean_text.strip()
    
    # Replace newlines with spaces for preview
    clean_text = clean_text.replace('\n', ' ')
    
    # Remove extra whitespace
    clean_text = ' '.join(clean_text.split())
    
    # Truncate if too long
    if len(clean_text) > max_length:
        # Try to cut at a word boundary
        truncated = clean_text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # If we can find a space in the last 20%
            clean_text = truncated[:last_space] + "..."
        else:
            clean_text = truncated + "..."
    
    return clean_text

def format_date_for_display(date_string):
    """
    Format date string for consistent display
    
    Args:
        date_string (str): ISO format date string
        
    Returns:
        str: Formatted date string
    """
    if not date_string:
        return "No date"
    
    try:
        # Handle different date formats
        if 'T' in date_string:
            # ISO format with time
            date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            # Simple date format
            date_obj = datetime.strptime(date_string[:10], '%Y-%m-%d')
        
        return date_obj.strftime('%Y-%m-%d')
    except:
        # Fallback - just return first 10 characters if it looks like a date
        return date_string[:10] if len(date_string) >= 10 else date_string

def truncate_text(text, max_length=50):
    """
    Truncate text to specified length with ellipsis
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        
    Returns:
        str: Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."