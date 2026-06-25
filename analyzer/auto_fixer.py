import re
import os
import ast

def apply_rule_fix(file_content, line_number, category, error_message):
    """
    Applies rule-based regular expression repairs to common Python issues.
    """
    lines = file_content.splitlines()
    if not (0 < line_number <= len(lines)):
        return file_content, "Line number out of bounds. No rule-based fix applied."
        
    idx = line_number - 1
    target_line = lines[idx]
    explanation = ""
    
    # 1. Unused Imports
    if "unused import" in error_message.lower() or "unused import" in category.lower() or "f401" in error_message.lower():
        # Comment out the unused import
        lines[idx] = f"# {target_line}  # Removed: unused import"
        explanation = f"Commented out unused import on line {line_number}."
        
    # 2. Bare Except Block
    elif "bare except" in error_message.lower() or "except:" in target_line:
        # Replace except: with except Exception as e:
        new_line = re.sub(r"except\s*:", "except Exception as e:", target_line)
        if new_line != target_line:
            lines[idx] = new_line
            # If body is pass, let's keep it but add a print/logging or simple statement
            explanation = f"Replaced bare 'except:' with 'except Exception as e:' on line {line_number} to capture errors properly."
            
    # 3. Dangerous eval/exec
    elif "eval(" in target_line and ("eval" in error_message.lower() or "security" in category.lower()):
        # Replace eval with ast.literal_eval (requires import ast at top)
        new_line = target_line.replace("eval(", "ast.literal_eval(")
        lines[idx] = new_line
        
        # Ensure import ast is present in the file
        has_ast_import = any("import ast" in line for line in lines)
        if not has_ast_import:
            lines.insert(0, "import ast")
            explanation = f"Replaced 'eval()' with 'ast.literal_eval()' on line {line_number} for security and added 'import ast'."
        else:
            explanation = f"Replaced 'eval()' with 'ast.literal_eval()' on line {line_number} for security."
            
    # 4. Division by zero
    elif "/" in target_line and ("division by zero" in error_message.lower() or "zerodivision" in category.lower()):
        # Try to wrap divisor
        # e.g., total / len(numbers) -> total / len(numbers) if len(numbers) != 0 else 0
        match = re.search(r"(\w+)\s*/\s*len\((\w+)\)", target_line)
        if match:
            dividend, list_name = match.groups()
            replaced = f"{dividend} / len({list_name}) if len({list_name}) != 0 else 0"
            lines[idx] = target_line.replace(match.group(0), replaced)
            explanation = f"Added length check guard to prevent division by zero on line {line_number}."
        else:
            # General division fallback
            explanation = f"ZeroDivisionError detected on line {line_number}. Add a check: if divisor != 0 before division."
            
    # 5. Dead Code
    elif "dead code" in error_message.lower() or "unreachable code" in error_message.lower():
        # Comment out the line
        lines[idx] = f"# {target_line}  # Removed: unreachable dead code"
        explanation = f"Commented out unreachable dead code statement on line {line_number}."
        
    else:
        explanation = f"No rule-based templates match this error. Please use Gemini AI to generate a structural repair suggestion."
        
    return "\n".join(lines), explanation

def recommend_and_fix(file_content, file_path, line_number, category, error_message, gemini_client=None):
    """
    Coordinates bug correction using AI (if available) or falling back to regex rule sets.
    """
    fixed_code = None
    fix_type = "None"
    explanation = ""
    
    # 1. Try Gemini AI
    if gemini_client and gemini_client.is_configured:
        fixed_code = gemini_client.generate_fixed_code(
            file_content=file_content,
            file_path=file_path,
            line_number=line_number,
            category=category,
            error_message=error_message
        )
        if fixed_code:
            fix_type = "AI-Powered"
            explanation = f"Gemini AI successfully refactored and repaired the bug on line {line_number}."
            
    # 2. Fallback to Local Rules
    if not fixed_code:
        fixed_code, rule_explanation = apply_rule_fix(file_content, line_number, category, error_message)
        if fixed_code != file_content:
            fix_type = "Rule-Based"
            explanation = rule_explanation
        else:
            explanation = "Unable to automatically repair this type of error. Review the fix suggestions or ask the AI Chat assistant for help."
            fixed_code = file_content
            
    return fixed_code, fix_type, explanation
