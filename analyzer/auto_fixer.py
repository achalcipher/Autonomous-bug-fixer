import re
import os
import ast

def fix_division_by_zero(file_content, line_number):
    try:
        tree = ast.parse(file_content)
    except Exception:
        return file_content, False
        
    class DivVisitor(ast.NodeVisitor):
        def __init__(self):
            self.matching_nodes = []
        def visit_BinOp(self, node):
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                if getattr(node, 'lineno', None) == line_number:
                    self.matching_nodes.append(node)
            self.generic_visit(node)
            
    visitor = DivVisitor()
    visitor.visit(tree)
    
    if not visitor.matching_nodes:
        return file_content, False
        
    node = visitor.matching_nodes[0]
    op_symbol = {ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%"}[type(node.op)]
    left_str = ast.unparse(node.left)
    right_str = ast.unparse(node.right)
    replacement = f"({left_str} {op_symbol} {right_str} if {right_str} != 0 else 0)"
    
    lines = file_content.splitlines(keepends=True)
    start_line_idx = node.lineno - 1
    end_line_idx = node.end_lineno - 1
    start_col = node.col_offset
    end_col = node.end_col_offset
    
    prefix = "".join(lines[:start_line_idx]) + lines[start_line_idx][:start_col]
    suffix = lines[end_line_idx][end_col:] + "".join(lines[end_line_idx + 1:])
    
    return prefix + replacement + suffix, True

def fix_line_division(target_line):
    indented = "    " + target_line.strip()
    dummy_code = f"def _dummy():\n{indented}\n"
    
    try:
        tree = ast.parse(dummy_code)
    except Exception:
        return target_line, False
        
    class DivVisitor(ast.NodeVisitor):
        def __init__(self):
            self.matching_nodes = []
        def visit_BinOp(self, node):
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                self.matching_nodes.append(node)
            self.generic_visit(node)
            
    visitor = DivVisitor()
    visitor.visit(tree)
    
    if not visitor.matching_nodes:
        return target_line, False
        
    node = visitor.matching_nodes[0]
    op_symbol = {ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%"}[type(node.op)]
    left_str = ast.unparse(node.left)
    right_str = ast.unparse(node.right)
    
    pattern = re.escape(left_str) + r"\s*" + re.escape(op_symbol) + r"\s*" + re.escape(right_str)
    replacement = f"({left_str} {op_symbol} {right_str} if {right_str} != 0 else 0)"
    
    new_line, count = re.subn(pattern, replacement, target_line, count=1)
    if count > 0:
        return new_line, True
    return target_line, False

def apply_rule_fix(file_content, line_number, category, error_message):
    """
    Applies rule-based regular expression repairs to common Python issues.
    """
    # Detect line ending style
    line_ending = "\r\n" if "\r\n" in file_content else "\n"
    lines = file_content.splitlines()
    if not (0 < line_number <= len(lines)):
        return file_content, "Line number out of bounds. No rule-based fix applied."
        
    idx = line_number - 1
    target_line = lines[idx]
    explanation = ""
    changed = False
    
    # 1. Unused Imports
    if "unused import" in error_message.lower() or "unused import" in category.lower() or "f401" in error_message.lower():
        # Comment out the unused import
        lines[idx] = f"# {target_line}  # Removed: unused import"
        explanation = f"Commented out unused import on line {line_number}."
        changed = True
        
    # 2. Bare Except Block
    elif "bare except" in error_message.lower() or "except:" in target_line:
        # Replace except: with except Exception as e:
        new_line = re.sub(r"except\s*:", "except Exception as e:", target_line)
        if new_line != target_line:
            lines[idx] = new_line
            # If body is pass, let's keep it but add a print/logging or simple statement
            explanation = f"Replaced bare 'except:' with 'except Exception as e:' on line {line_number} to capture errors properly."
            changed = True
            
    # 3. Dangerous eval/exec
    elif "eval(" in target_line and ("eval" in error_message.lower() or "security" in category.lower()):
        # Replace eval with ast.literal_eval (requires import ast at top)
        new_line = target_line.replace("eval(", "ast.literal_eval(")
        lines[idx] = new_line
        changed = True
        
        # Ensure import ast is present in the file
        has_ast_import = any("import ast" in line for line in lines)
        if not has_ast_import:
            lines.insert(0, "import ast")
            explanation = f"Replaced 'eval()' with 'ast.literal_eval()' on line {line_number} for security and added 'import ast'."
        else:
            explanation = f"Replaced 'eval()' with 'ast.literal_eval()' on line {line_number} for security."
            
    # 4. Division by zero
    elif "/" in target_line and ("division by zero" in error_message.lower() or "zerodivision" in category.lower()):
        # Try AST-based file division fixer first
        fixed_content, ok = fix_division_by_zero(file_content, line_number)
        if ok:
            explanation = f"Added divisor check guard to prevent division by zero on line {line_number}."
            return fixed_content, explanation
            
        # Fallback to single-line AST division fixer
        new_line, ok = fix_line_division(target_line)
        if ok:
            lines[idx] = new_line
            explanation = f"Added divisor check guard to prevent division by zero on line {line_number}."
            changed = True
        else:
            # Try to wrap divisor using existing regex fallback
            match = re.search(r"(\w+)\s*/\s*len\((\w+)\)", target_line)
            if match:
                dividend, list_name = match.groups()
                replaced = f"{dividend} / len({list_name}) if len({list_name}) != 0 else 0"
                lines[idx] = target_line.replace(match.group(0), replaced)
                explanation = f"Added length check guard to prevent division by zero on line {line_number}."
                changed = True
            else:
                # Literal division fallbacks
                if "/ 0.0" in target_line:
                    lines[idx] = target_line.replace("/ 0.0", "/ 1.0")
                    explanation = f"Replaced division by zero with safe divisor 1.0 on line {line_number}."
                    changed = True
                elif "/0.0" in target_line:
                    lines[idx] = target_line.replace("/0.0", "/1.0")
                    explanation = f"Replaced division by zero with safe divisor 1.0 on line {line_number}."
                    changed = True
                elif "/ 0" in target_line:
                    lines[idx] = target_line.replace("/ 0", "/ 1")
                    explanation = f"Replaced division by zero with safe divisor 1 on line {line_number}."
                    changed = True
                elif "/0" in target_line:
                    lines[idx] = target_line.replace("/0", "/1")
                    explanation = f"Replaced division by zero with safe divisor 1 on line {line_number}."
                    changed = True
                else:
                    # General division fallback
                    explanation = f"ZeroDivisionError detected on line {line_number}. Add a check: if divisor != 0 before division."
            
    # 5. Dead Code
    elif "dead code" in error_message.lower() or "unreachable code" in error_message.lower():
        # Comment out the line
        lines[idx] = f"# {target_line}  # Removed: unreachable dead code"
        explanation = f"Commented out unreachable dead code statement on line {line_number}."
        changed = True
        
    if changed:
        return line_ending.join(lines), explanation
    else:
        explanation = f"No rule-based templates match this error. Please use Gemini AI to generate a structural repair suggestion."
        return file_content, explanation
 
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
            # Normalize line endings to compare content only
            norm_orig = file_content.replace("\r\n", "\n")
            norm_fixed = fixed_code.replace("\r\n", "\n")
            if norm_fixed != norm_orig:
                fix_type = "AI-Powered"
                explanation = f"Gemini AI successfully refactored and repaired the bug on line {line_number}."
            else:
                fixed_code = None
            
    # 2. Fallback to Local Rules
    if not fixed_code:
        fixed_code, rule_explanation = apply_rule_fix(file_content, line_number, category, error_message)
        # Normalize line endings to compare content only
        norm_orig = file_content.replace("\r\n", "\n")
        norm_fixed = fixed_code.replace("\r\n", "\n")
        if norm_fixed != norm_orig:
            fix_type = "Rule-Based"
            explanation = rule_explanation
        else:
            explanation = "Unable to automatically repair this type of error. Review the fix suggestions or ask the AI Chat assistant for help."
            fixed_code = file_content
            
    return fixed_code, fix_type, explanation
