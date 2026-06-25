import streamlit as st
from streamlit_ace import st_ace
import os
import sys
import pandas as pd
import plotly.express as px
import tempfile
import shutil
import subprocess
from datetime import datetime

# Local imports
from database import db_manager
from utils import file_handler
from analyzer import compile_analyzer, ast_analyzer, static_analyzer, auto_fixer
from ai.gemini_client import GeminiClient
from reports import pdf_generator

# Page configuration
st.set_page_config(
    page_title="Autonomous Bug Fixer IDE",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize SQLite Database
db_manager.init_db()

# Target upload cache directory
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Helper: check for local linters
def check_linter_status():
    status = {}
    tools = {
        "pylint": "PyLint",
        "flake8": "Flake8",
        "mypy": "Mypy",
        "bandit": "Bandit"
    }
    for mod, label in tools.items():
        try:
            res = subprocess.run([sys.executable, "-m", mod, "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            status[label] = res.returncode == 0 or b"options" in res.stdout or b"usage" in res.stdout
        except Exception:
            status[label] = False
    return status

# --- Inject CSS Stylings ---
st.markdown("""
<style>
    /* Enforce Dark Theme globally */
    .stApp {
        background-color: #0b0f19 !important;
        color: #e2e8f0 !important;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #0b0f19 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
    }
    /* Style headers */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: #f1f5f9 !important;
    }
    /* Sidebar text colors */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #f8fafc !important;
    }
    /* Input element label visibility */
    .stSelectbox label, .stTextInput label, .stRadio label {
        color: #cbd5e1 !important;
    }
    /* Gradient banner header */
    .ide-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        border-left: 5px solid #3b82f6;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .ide-header h1 {
        margin: 0;
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.025em;
    }
    .ide-header p {
        margin: 5px 0 0 0;
        color: #94a3b8;
        font-size: 14px;
    }
    /* Terminal execution box styling */
    .terminal-box {
        background-color: #020617;
        color: #38bdf8;
        font-family: 'Courier New', Courier, monospace;
        padding: 15px;
        border-radius: 6px;
        border: 1px solid #1e293b;
        max-height: 250px;
        overflow-y: auto;
        white-space: pre-wrap;
        margin-bottom: 15px;
    }
    /* Buttons global dark styling */
    .stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 6px !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover, .stDownloadButton button:hover, [data-testid="stFormSubmitButton"] button:hover {
        background-color: #3b82f6 !important;
        color: white !important;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.5) !important;
    }
    /* Style file uploader dropzone */
    [data-testid="stFileUploaderDropzone"] {
        background-color: #1e293b !important;
        border: 2px dashed #475569 !important;
    }
    [data-testid="stFileUploaderDropzone"] p, 
    [data-testid="stFileUploaderDropzone"] span {
        color: #cbd5e1 !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        background-color: #0f172a !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
    }
    /* Metric Card styling overrides */
    .metric-card {
        padding: 18px;
        border-radius: 8px;
        border-left: 6px solid;
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        margin-bottom: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-card h4 {
        margin: 0 0 8px 0;
        color: #94a3b8 !important;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-card h2 {
        margin: 0;
        font-size: 28px;
        font-weight: 700;
    }
    /* Severity Score indicator */
    .score-badge {
        font-size: 22px;
        font-weight: 700;
        padding: 10px 15px;
        border-radius: 6px;
        text-align: center;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATES -----------------
# Default boilerplate code loaded on first load
DEFAULT_CODE = """# Welcome to Autonomous Bug Fixer IDE!
# Write or edit Python code below.
import os
import sys

def process_numbers(numbers):
    total = 0
    # BUG: name 'count' referenced before assignment if list is empty
    for item in numbers:
        total += item
        
    # BUG: Potential ZeroDivisionError if numbers is empty
    avg = total / len(numbers)
    return avg

def trigger_smells():
    try:
        # BUG: Division by zero (AST issue)
        val = 100 / 0
    except:
        # BUG: Bare except block (Code Smell)
        pass
        
    # BUG: Dangerous eval call (Security risk)
    cleaned = eval("2 + 2")
    return cleaned

if __name__ == "__main__":
    print("Executing sample functions...")
    # This will trigger ZeroDivisionError at runtime
    res = process_numbers([])
    print("Result:", res)
"""

if "editor_code" not in st.session_state:
    st.session_state["editor_code"] = DEFAULT_CODE
if "editor_key_counter" not in st.session_state:
    st.session_state["editor_key_counter"] = 0
if "api_key" not in st.session_state:
    st.session_state["api_key"] = os.getenv("GEMINI_API_KEY", "")
if "analysis_results" not in st.session_state:
    st.session_state["analysis_results"] = None
if "execution_output" not in st.session_state:
    st.session_state["execution_output"] = None
if "repaired_code" not in st.session_state:
    st.session_state["repaired_code"] = None
if "active_filename" not in st.session_state:
    st.session_state["active_filename"] = "sandbox.py"
if "workspace_files" not in st.session_state:
    st.session_state["workspace_files"] = {}
if "selected_issue_id" not in st.session_state:
    st.session_state["selected_issue_id"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "explanation" not in st.session_state:
    st.session_state["explanation"] = None

# Instantiate Gemini Client
ai_client = GeminiClient(api_key=st.session_state["api_key"])

# ----------------- ANALYSIS PIPELINE FUNCTION -----------------
def run_analysis_pipeline():
    code_string = st.session_state["editor_code"]
    
    # Save code to temp file for static analyzer
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "analyze_sandbox.py")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(code_string)
        
    try:
        # 1. Compile checks
        syntax_errors = compile_analyzer.analyze_syntax(code_string, temp_file)
        # 2. AST quality checks
        ast_issues = ast_analyzer.analyze_ast(code_string, temp_file)
        # 3. Running shell subprocess linters (pylint, flake8, mypy, bandit)
        static_issues = static_analyzer.run_static_analysis(temp_file)
        
        # Combine all issues
        all_issues = []
        all_issues.extend(syntax_errors)
        all_issues.extend(ast_issues)
        all_issues.extend(static_issues)
        
        # Normalise paths in error reports
        for issue in all_issues:
            issue["file_path"] = st.session_state["active_filename"]
            
        # Count severity frequencies
        critical_c = sum(1 for i in all_issues if i["severity"] == "Critical")
        high_c = sum(1 for i in all_issues if i["severity"] == "High")
        medium_c = sum(1 for i in all_issues if i["severity"] == "Medium")
        low_c = sum(1 for i in all_issues if i["severity"] == "Low")
        
        # Calculate Severity Score
        score = 100 - (critical_c * 20 + high_c * 12 + medium_c * 6 + low_c * 2)
        score = max(0, min(100, score))
        
        # Save results in SQLite
        scan_id = f"ide_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        db_manager.save_scan(
            scan_id=scan_id,
            project_name=f"IDE_{st.session_state['active_filename']}",
            file_count=1,
            critical_count=critical_c,
            high_count=high_c,
            medium_count=medium_c,
            low_count=low_c,
            status="Completed"
        )
        
        for issue in all_issues:
            db_manager.save_scan_detail(
                scan_id=scan_id,
                file_path=issue["file_path"],
                line_number=issue["line_number"],
                severity=issue["severity"],
                category=issue["category"],
                error_message=issue["error_message"],
                code_snippet=issue["code_snippet"],
                fix_suggestion=issue["fix_suggestion"],
                fixed_code=code_string # store snapshot of original file
            )
            
        summary = {
            "scan_id": scan_id,
            "project_name": f"IDE_{st.session_state['active_filename']}",
            "critical_count": critical_c,
            "high_count": high_c,
            "medium_count": medium_c,
            "low_count": low_c,
            "timestamp": datetime.now().isoformat()
        }
        
        st.session_state["analysis_results"] = {
            "summary": summary,
            "details": all_issues,
            "score": score
        }
        return all_issues
    except Exception as e:
        st.error(f"Analysis pipeline crashed: {str(e)}")
        return []
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ----------------- CODE RUNNER FUNCTION -----------------
def execute_code_sandboxed(code_string):
    """
    Saves current code and runs it in a subprocess, returning outputs and exit status.
    """
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, "run_sandbox.py")
    
    # Save script to temp file
    with open(temp_file_path, "w", encoding="utf-8") as f:
        f.write(code_string)
        
    start_time = datetime.now()
    try:
        proc = subprocess.run(
            [sys.executable, "-u", temp_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5  # Safeguard timeout
        )
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = "Execution Timeout: The program took longer than 5 seconds to run (potential infinite loop detected)."
        exit_code = -9
    except Exception as e:
        stdout = ""
        stderr = f"Subprocess startup error: {str(e)}"
        exit_code = -1
    finally:
        # Cleanup folder
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    elapsed = (datetime.now() - start_time).total_seconds()
    return stdout, stderr, exit_code, elapsed

# ----------------- SIDEBAR: SECONDARY CONTROLS -----------------
with st.sidebar:
    st.title("💻 Workspace & Configuration")
    
    # 🔑 AI Configuration
    st.subheader("🔑 AI Credentials")
    api_key_input = st.text_input("Gemini API Key", value=st.session_state["api_key"], type="password", help="Enter Google Gemini API Key to enable automated AI fixes.")
    if api_key_input != st.session_state["api_key"]:
        st.session_state["api_key"] = api_key_input
        st.rerun()
        
    if ai_client.is_configured:
        st.success("🟢 Gemini AI Enabled")
    else:
        st.warning("⚠️ Running Offline (Mock Fallbacks)")
        
    st.markdown("---")
    
    # 📁 Workspace file/ZIP ingestion
    st.subheader("📁 Ingest Codebase")
    upload_mode = st.radio("Ingest Type", ["Single .py File", "ZIP Project Folder"])
    uploaded_file = st.file_uploader("Upload File/Archive", type=["py", "zip"])
    
    if uploaded_file is not None:
        if st.button("📥 Load to Workspace", use_container_width=True):
            # Clean and setup uploads directory
            scan_id = f"workspace_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            workspace_root = os.path.join(UPLOADS_DIR, scan_id)
            os.makedirs(workspace_root, exist_ok=True)
            
            if upload_mode == "Single .py File" and uploaded_file.name.endswith(".py"):
                dest = os.path.join(workspace_root, uploaded_file.name)
                with open(dest, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state["workspace_files"] = {uploaded_file.name: dest}
                st.session_state["active_filename"] = uploaded_file.name
                
                # Load code directly
                code_content = file_handler.read_file_content(dest)
                st.session_state["editor_code"] = code_content
                st.session_state["editor_key_counter"] += 1
                st.success(f"Loaded single file `{uploaded_file.name}` into IDE!")
                st.rerun()
                
            elif upload_mode == "ZIP Project Folder" and uploaded_file.name.endswith(".zip"):
                try:
                    extract_path = os.path.join(workspace_root, "extracted")
                    file_handler.unzip_project(uploaded_file.read(), extract_path)
                    
                    # Traversal
                    found_files = file_handler.find_python_files(extract_path)
                    if found_files:
                        files_dict = {}
                        for f_path in found_files:
                            rel = os.path.relpath(f_path, extract_path)
                            files_dict[rel] = f_path
                            
                        st.session_state["workspace_files"] = files_dict
                        first_rel = sorted(list(files_dict.keys()))[0]
                        st.session_state["active_filename"] = first_rel
                        
                        # Load first code file
                        code_content = file_handler.read_file_content(files_dict[first_rel])
                        st.session_state["editor_code"] = code_content
                        st.session_state["editor_key_counter"] += 1
                        st.success(f"Extracted {len(found_files)} files! Select files from dropdown below.")
                        st.rerun()
                    else:
                        st.error("No valid Python files (.py) discovered inside the ZIP.")
                except Exception as zip_err:
                    st.error(f"Failed to process archive: {zip_err}")
                    
    # File selector dropdown if workspace exists
    if st.session_state["workspace_files"]:
        st.subheader("📄 Workspace Files")
        selected_file = st.selectbox(
            "Select active file to edit",
            options=sorted(list(st.session_state["workspace_files"].keys())),
            index=sorted(list(st.session_state["workspace_files"].keys())).index(st.session_state["active_filename"])
        )
        if selected_file != st.session_state["active_filename"]:
            st.session_state["active_filename"] = selected_file
            # Read and load code
            filepath = st.session_state["workspace_files"][selected_file]
            code_content = file_handler.read_file_content(filepath)
            st.session_state["editor_code"] = code_content
            st.session_state["editor_key_counter"] += 1
            st.rerun()
            
    st.markdown("---")
    
    # 📜 History of previous analysis
    st.subheader("📜 Load Past Analyses")
    history_scans = db_manager.get_all_scans()
    
    if history_scans:
        history_options = {f"{s['project_name']} ({s['timestamp'][:16].replace('T', ' ')})": s['scan_id'] for s in history_scans}
        selected_history = st.selectbox("Select historical run", list(history_options.keys()))
        
        if st.button("🔄 Restore Analysis", use_container_width=True):
            hist_scan_id = history_options[selected_history]
            summary = db_manager.get_scan_summary(hist_scan_id)
            details = db_manager.get_scan_details(hist_scan_id)
            
            # Find if there is code stored in details
            # Load code from first detail if available
            restored_code = DEFAULT_CODE
            for det in details:
                if det.get("fixed_code"):
                    # We can use original text or fixed code as restored code
                    restored_code = det.get("fixed_code")
                    break
                    
            st.session_state["editor_code"] = restored_code
            st.session_state["editor_key_counter"] += 1
            st.session_state["active_filename"] = f"restored_{summary['project_name']}.py"
            
            # Calculate Severity Score
            critical_c = summary.get("critical_count", 0)
            high_c = summary.get("high_count", 0)
            medium_c = summary.get("medium_count", 0)
            low_c = summary.get("low_count", 0)
            
            score = 100 - (critical_c * 20 + high_c * 12 + medium_c * 6 + low_c * 2)
            score = max(0, min(100, score))
            
            st.session_state["analysis_results"] = {
                "summary": summary,
                "details": details,
                "score": score
            }
            st.success("Restored database code and scan reports back into IDE!")
            st.rerun()
    else:
        st.info("No scan history saved in SQLite yet.")

# ----------------- MAIN LAYOUT: PYTHON IDE -----------------
st.markdown(f"""
<div class="ide-header">
    <h1>💻 Autonomous Python Bug Fixer IDE</h1>
    <p>Active File: <b>{st.session_state['active_filename']}</b> | Write, Execute, Analyze, and Auto-Fix Python scripts instantly inside the browser.</p>
</div>
""", unsafe_allow_html=True)

# 1. VS Code-like Code Editor (Ace Editor)
editor_key = f"ace_editor_key_{st.session_state['editor_key_counter']}"
editor_code = st_ace(
    value=st.session_state["editor_code"],
    language="python",
    theme="terminal",
    keybinding="vscode",
    font_size=14,
    tab_size=4,
    show_gutter=True,
    show_print_margin=False,
    wrap=True,
    auto_update=True,
    key=editor_key
)

# Keep session state updated with editor contents
if editor_code != st.session_state["editor_code"]:
    st.session_state["editor_code"] = editor_code
    # Clear stale results/explanations so they don't show old panels
    st.session_state["repaired_code"] = None
    st.session_state["repair_logs"] = None
    st.session_state["explanation"] = None

# Instant Syntax Warning Block (Under the editor)
# Performs a quick compiler check as they edit
quick_syntax_errors = compile_analyzer.analyze_syntax(st.session_state["editor_code"], "sandbox.py")
if quick_syntax_errors:
    syn = quick_syntax_errors[0]
    st.error(f"🚨 **Syntax Warning (Line {syn['line_number']}):** {syn['error_message']}")

# 2. Control Bar Row
col_b1, col_b2, col_b3, col_b4 = st.columns(4)

with col_b1:
    btn_run = st.button("▶️ Execute Code", use_container_width=True, help="Executes code in a sandbox subprocess and gets output.")
with col_b2:
    btn_analyze = st.button("🔍 Analyze Code", use_container_width=True, help="Runs ast quality checks and pylint/flake8/mypy/bandit linters.")
with col_b3:
    btn_autofix = st.button("🔧 Auto Fix Code", use_container_width=True, help="Queries Gemini AI or offline rules to sweep and fix all errors.")
with col_b4:
    btn_explain = st.button("💡 Explain Errors", use_container_width=True, help="Generates beginner-friendly explanations for selected diagnostic bugs.")

# ----------------- ACTION LOGIC & PANELS -----------------

# Logic A: Run Code
if btn_run:
    with st.spinner("Executing Python script..."):
        stdout, stderr, exit_code, duration = execute_code_sandboxed(st.session_state["editor_code"])
        st.session_state["execution_output"] = {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "duration": duration
        }

# Logic B: Analyze Code
if btn_analyze:
    with st.spinner("Analyzing code quality, security vulnerabilities, and logic..."):
        all_issues = run_analysis_pipeline()
        if all_issues:
            st.success(f"Analysis complete! Found {len(all_issues)} issues in codebase.")
        else:
            st.success("Analysis complete! No issues found.")

# Logic C: Auto Fix (Global sweep)
if btn_autofix:
    with st.spinner("Attempting autonomous codebase repair..."):
        code_string = st.session_state["editor_code"]
        
        # If there are active analysis results, we loop through and fix them sequentially.
        # Otherwise, we run a quick analysis first.
        details_to_fix = []
        if st.session_state["analysis_results"]:
            details_to_fix = st.session_state["analysis_results"]["details"]
        else:
            details_to_fix = run_analysis_pipeline()
                
        if not details_to_fix:
            st.info("No bugs detected in codebase! No auto-fix needed.")
            st.session_state["repaired_code"] = code_string
        else:
            # Perform sequential sweep repair
            current_code = code_string
            fixed_log = []
            
            # Sort details descending by line number so edits at bottom do not displace line numbers at top
            sorted_details = sorted(details_to_fix, key=lambda x: x["line_number"], reverse=True)
            
            # Deduplicate by line number to prevent double edit conflicts
            seen_lines = set()
            deduped_details = []
            for d in sorted_details:
                if d["line_number"] not in seen_lines:
                    seen_lines.add(d["line_number"])
                    deduped_details.append(d)
            
            # Apply fixes
            for issue in deduped_details:
                try:
                    fixed_code, fix_type, explanation = auto_fixer.recommend_and_fix(
                        file_content=current_code,
                        file_path=st.session_state["active_filename"],
                        line_number=issue["line_number"],
                        category=issue["category"],
                        error_message=issue["error_message"],
                        gemini_client=ai_client
                    )
                    if fixed_code != current_code:
                        current_code = fixed_code
                        fixed_log.append(f"Fixed Line {issue['line_number']} [{issue['category']}]: {explanation}")
                except Exception as repair_err:
                    fixed_log.append(f"Failed to fix Line {issue['line_number']}: {str(repair_err)}")
            
            st.session_state["repaired_code"] = current_code
            st.session_state["repair_logs"] = fixed_log
            if fixed_log:
                st.success("Proposed code repair generated successfully!")
            else:
                st.warning("No automatic corrections could be applied to the detected issues.")

# Logic D: Explain Errors
if btn_explain:
    if not st.session_state["analysis_results"]:
        st.warning("⚠️ Please run '🔍 Analyze Code' first to discover codebase issues before explaining them.")
    else:
        # Get active issue from selected label
        selected_label = st.session_state.get("selected_issue_label")
        details = st.session_state["analysis_results"]["details"]
        
        # Recreate options map to find the correct index
        issues_options = {}
        for i, issue in enumerate(details):
            emoji = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵"}.get(issue["severity"], "🔵")
            label = f"{emoji} Line {issue['line_number']} [{issue['category']}] - {issue['error_message'][:70]}..."
            issues_options[label] = i
            
        if selected_label in issues_options:
            active_issue = details[issues_options[selected_label]]
            with st.spinner("Generating educational bug explanation dossier..."):
                expl = ai_client.explain_bug(
                    file_path=st.session_state["active_filename"],
                    line_number=active_issue["line_number"],
                    category=active_issue["category"],
                    severity=active_issue["severity"],
                    error_message=active_issue["error_message"],
                    code_snippet=active_issue["code_snippet"]
                )
                st.session_state["explanation"] = expl
        else:
            st.error("Selected issue could not be resolved from active session diagnostics.")

# ----------------- DISPLAY PANELS -----------------

# PANEL 1: Execution Output Terminal
if st.session_state["execution_output"]:
    exec_data = st.session_state["execution_output"]
    st.subheader("▶️ Execution Output Panel")
    
    # Header stats
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        if exec_data["exit_code"] == 0:
            st.success("🟢 Execution Status: SUCCESS (Exit Code 0)")
        elif exec_data["exit_code"] == -9:
            st.error("🔴 Execution Status: TIMEOUT")
        else:
            st.error(f"🔴 Execution Status: FAILED (Exit Code {exec_data['exit_code']})")
    with col_e2:
        st.metric("Execution Duration", f"{exec_data['duration']:.3f} seconds")
    with col_e3:
        # Check if runtime errors/stderr exists and display warning
        if exec_data["stderr"]:
            st.warning("⚠️ Diagnostics: Runtime Errors Trapped")
        else:
            st.success("✅ Diagnostics: Clean Run")
            
    # Scrollable terminal window
    terminal_text = ""
    if exec_data["stdout"]:
        terminal_text += f"[STDOUT]\n{exec_data['stdout']}"
    if exec_data["stderr"]:
        if terminal_text:
            terminal_text += "\n\n"
        terminal_text += f"[STDERR / TRACEBACK]\n{exec_data['stderr']}"
    if not terminal_text:
        terminal_text = "[Program ran successfully, but produced no standard output]"
        
    st.markdown(f'<div class="terminal-box">{terminal_text}</div>', unsafe_allow_html=True)
    
    # Display runtime warning box if traceback was printed
    if "traceback" in exec_data["stderr"].lower() or "error" in exec_data["stderr"].lower():
        st.error("💡 **Runtime Bug Identified:** Review the stack trace above to pinpoint variable bindings or exception parameters.")

# PANEL 2: Analysis Results Dashboard
if st.session_state["analysis_results"]:
    res = st.session_state["analysis_results"]
    summary = res["summary"]
    details = res["details"]
    score = res["score"]
    
    st.markdown("---")
    st.subheader("📊 Code Diagnostics & Visual Analytics")
    
    col_d1, col_d2 = st.columns([1, 2])
    
    with col_d1:
        # Score Gauge
        score_color = "#ef4444" # red
        if score >= 80:
            score_color = "#10b981" # green
        elif score >= 50:
            score_color = "#eab308" # yellow
            
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; text-align: center; color: white;">
            <div style="font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 5px;">Code Health Score</div>
            <div class="score-badge" style="background-color: {score_color}; color: white; display: inline-block;">
                {score} / 100
            </div>
            <p style="margin: 5px 0 0 0; font-size: 13px; color: #cbd5e1;">Coded bugs and vulnerabilities scale metric.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        
        # Grid metrics
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.metric("Critical Bugs", summary["critical_count"])
            st.metric("High Risks", summary["high_count"])
        with col_g2:
            st.metric("Medium Quality", summary["medium_count"])
            st.metric("Low Style", summary["low_count"])
            
    with col_d2:
        # Visual Pie Chart
        if details:
            df_det = pd.DataFrame(details)
            fig_p = px.pie(
                df_det,
                names='severity',
                color='severity',
                color_discrete_map={'Critical': '#ef4444', 'High': '#f97316', 'Medium': '#eab308', 'Low': '#3b82f6'},
                hole=0.45,
                title="Bug Severity Breakdown"
            )
            fig_p.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=230)
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.success("No static analysis warnings! Clean code repository.")
            
    # List of issues
    st.markdown("#### Diagnostic Findings Log")
    if not details:
        st.info("No codebase issues found in details database.")
    else:
        # Let user select a bug to inspect
        issues_options = {}
        for i, issue in enumerate(details):
            emoji = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵"}.get(issue["severity"], "🔵")
            label = f"{emoji} Line {issue['line_number']} [{issue['category']}] - {issue['error_message'][:70]}..."
            issues_options[label] = i
            
        selected_issue_label = st.selectbox(
            "Select issue to review or explain",
            options=list(issues_options.keys()),
            key="selected_issue_label",
            on_change=lambda: st.session_state.update({"explanation": None})
        )
        selected_idx = issues_options[selected_issue_label]
        active_issue = details[selected_idx]
        
        # Show detail warning box
        st.info(f"**Diagnostic Details (Line {active_issue['line_number']}):**\n"
                f"- **Category:** `{active_issue['category']}` | **Severity:** `{active_issue['severity']}`\n"
                f"- **Message:** {active_issue['error_message']}\n"
                f"- **Snippet:** `{active_issue['code_snippet']}`\n"
                f"- **Suggestion:** {active_issue['fix_suggestion']}")
        
        # Show explanation if generated and persistent in session state
        if st.session_state["explanation"]:
            st.markdown("---")
            st.markdown("##### 💡 AI Bug Analysis Explanation")
            st.markdown(st.session_state["explanation"])
                
    # PDF Report Button
    st.markdown("---")
    col_pdf, _ = st.columns([1, 2])
    with col_pdf:
        # Build Report path
        report_fn = f"IDE_Report_{summary['scan_id']}.pdf"
        temp_pdf = os.path.join(tempfile.gettempdir(), report_fn)
        if st.button("📄 Compile PDF Analysis Report", use_container_width=True):
            with st.spinner("Generating document..."):
                try:
                    pdf_generator.generate_pdf_report(summary, details, temp_pdf)
                    with open(temp_pdf, "rb") as pf:
                        pdf_bytes = pf.read()
                    st.download_button(
                        label="📥 Save PDF to System",
                        data=pdf_bytes,
                        file_name=report_fn,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("PDF built successfully! Click button above to download.")
                except Exception as report_err:
                    st.error(f"Failed to compile PDF: {report_err}")

# PANEL 3: Auto-Fix Comparison Block
if st.session_state["repaired_code"] is not None:
    # Compare ignoring line ending differences
    norm_orig = st.session_state["editor_code"].replace("\r\n", "\n")
    norm_repaired = st.session_state["repaired_code"].replace("\r\n", "\n")
    has_changes = (norm_repaired != norm_orig)
    
    if has_changes:
        st.markdown("---")
        st.subheader("🔧 Proposed Auto-Fix Code Corrections")
        
        # Display repair logs/summary
        if st.session_state.get("repair_logs"):
            st.markdown("**Applied Repair Sweeps:**")
            for log in st.session_state["repair_logs"]:
                st.markdown(f"- {log}")
                
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.caption("Original Code Workspace")
            st.code(st.session_state["editor_code"], language="python")
            
        with col_c2:
            st.caption("Repaired Autocorrected Code")
            st.code(st.session_state["repaired_code"], language="python")
            
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if st.button("💾 Apply Proposed Repairs to Editor", use_container_width=True):
                st.session_state["editor_code"] = st.session_state["repaired_code"]
                st.session_state["editor_key_counter"] += 1
                st.session_state["repaired_code"] = None # Reset
                st.success("Proposed fixes written back to code editor workspace! You can run, execute, or re-scan now.")
                st.rerun()
                
        with col_a2:
            # Download Fixed Code file
            st.download_button(
                label="📥 Download Fixed Code (.py)",
                data=st.session_state["repaired_code"],
                file_name=f"fixed_{st.session_state['active_filename']}",
                mime="text/x-python",
                use_container_width=True
            )
    else:
        # Show warning that no edits were made
        if st.session_state.get("repair_logs") is not None:
            st.markdown("---")
            st.warning("⚠️ No automatic corrections could be applied to the current code. Review the fix suggestions or ask the AI Chat assistant for help.")
