import sys
import os

def analyze_syntax(code_content, file_path):
    """
    Attempts to compile the given Python code content to find SyntaxError or IndentationError.
    Returns a list of issue dictionaries.
    """
    issues = []
    basename = os.path.basename(file_path)
    
    try:
        # Attempt to compile the code
        compile(code_content, file_path, 'exec')
    except (SyntaxError, IndentationError) as e:
        # Determine error category
        category = "SyntaxError"
        if isinstance(e, IndentationError):
            category = "IndentationError"
            
        line_num = e.lineno
        offset = e.offset
        error_msg = e.msg
        
        # Get offending line snippet if available
        snippet = ""
        if e.text:
            snippet = e.text.strip()
        else:
            lines = code_content.splitlines()
            if line_num and 0 < line_num <= len(lines):
                snippet = lines[line_num - 1].strip()
                
        # Generate generic fix suggestion based on messages
        suggestion = "Review code structure and syntax rules."
        if "expected ':'" in error_msg.lower():
            suggestion = "Add a colon ':' at the end of the block header (e.g. after 'if', 'def', 'for', 'while', or 'class')."
        elif "unexpected indent" in error_msg.lower():
            suggestion = "Fix the indentation of this line. Ensure it matches the surrounding block's indentation level."
        elif "unindent does not match any outer indentation level" in error_msg.lower():
            suggestion = "Re-align the indentation level of this block to match the outer code block."
        elif "was never closed" in error_msg.lower() or "unclosed" in error_msg.lower():
            suggestion = "Verify that all opened parentheses '(', brackets '[', and braces '{' are closed with their matching closing symbols."
        elif "invalid syntax" in error_msg.lower():
            suggestion = "Correct syntax format. Check for typos, mismatched quotes, or missing operations/arguments."
        elif "unexpected EOF while parsing" in error_msg.lower():
            suggestion = "The file ended abruptly. Check if you have an unclosed loop, function, class body, or missing parenthesis."
            
        issues.append({
            "file_path": file_path,
            "line_number": line_num,
            "severity": "Critical",
            "category": category,
            "error_message": error_msg,
            "code_snippet": snippet,
            "fix_suggestion": suggestion
        })
        
    return issues
