# Autonomous Python Bug Detection and Fix Recommendation System

A B.Tech Final Year Project built with Streamlit, SQLite, Plotly, static analyzers, and Gemini AI. This tool analyzes Python codebases (single files or zipped directories), detects syntax/logical bugs, code smells, vulnerabilities, performance issues, provides visual metrics, generates PDF reports, and hosts a conversational AI assistant to explain and repair errors.

## Features

1. **Upload Formats**: Scan single `.py` files or complete project structures uploaded as `.zip` files.
2. **Multi-Engine Static Scanning**:
   - **AST Analyzer**: Finds code smells, dead code, infinite loops, bare excepts, division by zero, and dangerous functions (`eval`, `exec`).
   - **Compiler check**: Traps basic compilation and indentation errors.
   - **flake8**: Detects style issues and syntax flaws.
   - **pylint**: Code-quality scores and structural issues.
   - **mypy**: Type checking warnings.
   - **bandit**: Security risks (e.g. hardcoded secrets, weak hashes).
3. **Visual Analytics**: Interactive Plotly dashboard showing bug distributions, severity frequencies, and file-wise risk profiles.
4. **Auto-Fix Generator**: Highlights source code lines side-by-side with recommendations, and allows one-click auto-fixes.
5. **Interactive AI Chat Assistant**: Powered by Google Gemini to converse on specific bugs, explain coding concepts, and walk through correction strategies.
6. **SQLite Scan History**: Stores past scan metrics, detailed findings, and fixed code, accessible from a dedicated History page.
7. **Professional PDF Reports**: Visual, print-ready reports with executive summaries, diagrams, and detailed line-by-line debug listings.

---

## Installation & Setup

Ensure Python 3.9+ is installed.

### 1. Install Dependencies
Install all package dependencies via pip:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment variables (Optional)
To enable the AI Chat Assistant and advanced code correction, configure your Google Gemini API key. Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*Note: You can also enter the API key directly within the application sidebar.*

### 3. Run the Application
Start the Streamlit dashboard:
```bash
streamlit run app.py
```

---

## Project Structure

```
Autonomous_Bug_Fixer/
├── app.py                      # Streamlit application entry point
├── requirements.txt            # Package list
├── README.md                   # Setup documentation
├── sample_buggy_code.py        # Demo script containing errors
├── database/
│   └── db_manager.py           # SQLite interaction layer
├── utils/
│   └── file_handler.py         # File ingestion & ZIP archiving utilities
├── reports/
│   └── pdf_generator.py        # PDF reporter
├── ai/
│   └── gemini_client.py        # Google Gemini AI connection & fallback chat logic
└── analyzer/
    ├── compile_analyzer.py     # Syntax & indentation errors
    ├── ast_analyzer.py         # Structural analysis of logic & code smells
    ├── static_analyzer.py      # Subprocess execution for flake8/mypy/pylint/bandit
    └── auto_fixer.py           # Code correction and diffing engine
```
