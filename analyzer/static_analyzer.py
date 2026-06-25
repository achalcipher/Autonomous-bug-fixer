import subprocess
import sys
import json
import os

def run_tool(cmd, timeout=10):
    """
    Runs a shell command and returns stdout and stderr.
    """
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout expired during execution", -1
    except FileNotFoundError:
        return "", "Tool executable not found", -2
    except Exception as e:
        return "", f"Unexpected error: {str(e)}", -3

def run_pylint(file_path):
    """
    Executes pylint in JSON output mode and parses the result.
    """
    cmd = [sys.executable, "-m", "pylint", "--output-format=json", file_path]
    stdout, stderr, code = run_tool(cmd)
    
    issues = []
    if not stdout or "Tool executable not found" in stderr:
        return issues
        
    try:
        data = json.loads(stdout)
        for item in data:
            # Map Pylint category types to severity
            # Types: convention, refactor, warning, error, fatal
            pylint_type = item.get("type", "warning")
            if pylint_type in ("error", "fatal"):
                severity = "High"
            elif pylint_type == "warning":
                severity = "Medium"
            else:
                severity = "Low"
                
            category = "Code Quality"
            if pylint_type == "refactor":
                category = "Code Smell"
            elif pylint_type == "error":
                category = "Runtime Risk"
                
            issues.append({
                "file_path": file_path,
                "line_number": item.get("line", 1),
                "severity": severity,
                "category": category,
                "error_message": f"PyLint ({item.get('symbol')}): {item.get('message')}",
                "code_snippet": "",  # Filled later by code manager
                "fix_suggestion": f"Check PyLint standard for rules concerning {item.get('symbol')}."
            })
    except Exception:
        pass # Skip if parsing fails
        
    return issues

def run_bandit(file_path):
    """
    Executes bandit in JSON output mode and parses security warnings.
    """
    cmd = [sys.executable, "-m", "bandit", "-f", "json", "-q", file_path]
    stdout, stderr, code = run_tool(cmd)
    
    issues = []
    if not stdout or "Tool executable not found" in stderr:
        return issues
        
    try:
        data = json.loads(stdout)
        results = data.get("results", [])
        for item in results:
            severity_map = {
                "HIGH": "High",
                "MEDIUM": "Medium",
                "LOW": "Low"
            }
            severity = severity_map.get(item.get("issue_severity"), "Medium")
            
            issues.append({
                "file_path": file_path,
                "line_number": item.get("line_number", 1),
                "severity": severity,
                "category": "Security",
                "error_message": f"Bandit ({item.get('test_id')}): {item.get('issue_text')}",
                "code_snippet": item.get("code", "").strip(),
                "fix_suggestion": f"Resolve Bandit security warning {item.get('test_id')}. {item.get('more_info', '')}"
            })
    except Exception:
        pass
        
    return issues

def run_flake8(file_path):
    """
    Executes flake8 and parses stdout text.
    """
    cmd = [sys.executable, "-m", "flake8", file_path]
    stdout, stderr, code = run_tool(cmd)
    
    issues = []
    if not stdout or "Tool executable not found" in stderr:
        return issues
        
    for line in stdout.splitlines():
        if not line:
            continue
        # Format: file_path:line:col: MSG
        parts = line.split(":", 3)
        if len(parts) >= 4:
            try:
                line_num = int(parts[1])
                msg = parts[3].strip()
                
                # Check for flake8 warning code (e.g. E225)
                code_prefix = msg.split()[0] if msg else ""
                severity = "Low"
                # Some flake8 warnings represent errors (e.g. F821 undefined name, F401 unused)
                if code_prefix.startswith("F") or code_prefix.startswith("E9"):
                    severity = "High"
                elif code_prefix.startswith("E") or code_prefix.startswith("W"):
                    severity = "Medium"
                    
                issues.append({
                    "file_path": file_path,
                    "line_number": line_num,
                    "severity": severity,
                    "category": "Style / Standard",
                    "error_message": f"Flake8 ({code_prefix}): {msg[len(code_prefix):].strip()}",
                    "code_snippet": "",
                    "fix_suggestion": "Follow PEP 8 styling conventions to resolve this layout rule."
                })
            except ValueError:
                continue
    return issues

def run_mypy(file_path):
    """
    Executes mypy type checks and parses type violations.
    """
    cmd = [sys.executable, "-m", "mypy", "--ignore-missing-imports", file_path]
    stdout, stderr, code = run_tool(cmd)
    
    issues = []
    if not stdout or "Tool executable not found" in stderr:
        return issues
        
    for line in stdout.splitlines():
        if "Success: no issues found" in line or not line:
            continue
        # Format: path:line: error/note: msg
        parts = line.split(":", 2)
        if len(parts) >= 3:
            try:
                line_num = int(parts[1])
                details = parts[2].strip()
                
                if "error:" in details:
                    msg = details.replace("error:", "").strip()
                    issues.append({
                        "file_path": file_path,
                        "line_number": line_num,
                        "severity": "Medium",
                        "category": "Type Error",
                        "error_message": f"Mypy: {msg}",
                        "code_snippet": "",
                        "fix_suggestion": "Clarify type annotations or declare variable types explicitly to satisfy the type checker."
                    })
            except ValueError:
                continue
    return issues

def run_static_analysis(file_path):
    """
    Runs all static linters and aggregates results.
    """
    all_issues = []
    
    # Run tools sequentially
    all_issues.extend(run_pylint(file_path))
    all_issues.extend(run_flake8(file_path))
    all_issues.extend(run_mypy(file_path))
    all_issues.extend(run_bandit(file_path))
    
    # Post-process: deduplicate and load code snippets if missing
    seen = set()
    deduped = []
    
    # Load code lines for snippet filling
    code_lines = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code_lines = f.readlines()
        except Exception:
            pass
            
    for issue in all_issues:
        key = (issue["line_number"], issue["category"], issue["error_message"])
        if key not in seen:
            seen.add(key)
            
            # Fill code snippet if empty
            if not issue["code_snippet"] and code_lines:
                line_idx = issue["line_number"] - 1
                if 0 <= line_idx < len(code_lines):
                    issue["code_snippet"] = code_lines[line_idx].strip()
                    
            deduped.append(issue)
            
    return deduped
