import google.generativeai as genai
import os
import re

class GeminiClient:
    def __init__(self, api_key=None):
        """
        Initializes the Gemini Client. 
        Will try to read from argument or environment variable GEMINI_API_KEY.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.is_configured = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                self.is_configured = True
            except Exception as e:
                self.is_configured = False
                
    def get_fallback_explanation(self, category, error_message, code_snippet):
        """
        Provides detailed rule-based bug explanations when offline / key is missing.
        """
        category_lower = category.lower()
        msg_lower = error_message.lower()
        
        explanation = f"### [Offline Explanation] Bug Analysis\n"
        explanation += f"**Category:** {category} | **Error Message:** {error_message}\n\n"
        
        # 1. Syntax & Indentation
        if "syntax" in category_lower:
            explanation += ("**What happened:** Python encountered code that violates grammar rules. "
                            "Common causes include typos, mismatched quotes, missing brackets, or misuse of operator signs.\n\n"
                            "**How to fix:**\n"
                            "- Double-check the syntax elements in the snippet: `" + code_snippet + "`\n"
                            "- Ensure all opening symbols `(`, `[`, `{` have matching closing symbols.\n"
                            "- Check if you missed a comma separating list values or function arguments.")
        elif "indent" in category_lower:
            explanation += ("**What happened:** Python requires rigid indentation to establish code block structures. "
                            "This error occurs when space/tab indentation levels are inconsistent.\n\n"
                            "**How to fix:**\n"
                            "- Highlight the lines around the error and check if they are aligned with spaces vs tabs.\n"
                            "- Consistent 4-space blocks are recommended for Python.\n"
                            "- Review statements starting blocks like `def`, `class`, `if`, `for`, `try` to ensure child statements are indented.")
                            
        # 2. Logical & Runtime
        elif "zerodivision" in category_lower or "zero" in msg_lower:
            explanation += ("**What happened:** A division expression attempted to divide by `0`, which is mathematically undefined.\n\n"
                            "**How to fix:**\n"
                            "- Add a conditional guard: `if divisor != 0: result = dividend / divisor`\n"
                            "- Or catch it: \n"
                            "  ```python\n"
                            "  try:\n"
                            "      result = dividend / divisor\n"
                            "  except ZeroDivisionError:\n"
                            "      result = 0 # or log error\n"
                            "  ```")
        elif "security" in category_lower:
            explanation += ("**What happened:** Static scanning found a risk in your code. "
                            "Dangerous calls (e.g. `eval()`) or weak encryption algorithms make the code susceptible to injection or exploit.\n\n"
                            "**How to fix:**\n"
                            "- Avoid `eval()` or `exec()`. Use `ast.literal_eval()` for literal evaluations, or use serialization like JSON.\n"
                            "- Do not hardcode API tokens or passwords directly in code; load them from environment variables.")
        elif "unused" in msg_lower or "unused import" in category_lower:
            explanation += ("**What happened:** You imported a library or declared a variable but never referenced it. "
                            "This is a minor code smell that bloats workspace namespaces.\n\n"
                            "**How to fix:**\n"
                            "- Safe to delete this import line if it's not needed, or use the variable if it was simply forgotten.")
        elif "dead code" in msg_lower:
            explanation += ("**What happened:** Code was placed directly below a terminal control sequence (`return`, `break`, `continue`, `raise`). "
                            "The interpreter will exit before ever reaching these lines.\n\n"
                            "**How to fix:**\n"
                            "- Move the statements above the exit statement if they need to execute, otherwise delete them.")
        else:
            explanation += ("**What happened:** Static analyzer flagged this line. This could represent a style inconsistency, "
                            "potential name mapping failure, type variance, or import runtime block.\n\n"
                            "**How to fix:**\n"
                            "- Inspect the error message details and verify target variables are defined before access.\n"
                            "- Check for typos in function or module names.\n"
                            "- Standardize type casts where types mismatch (e.g. casting inputs via `int()` before calculation).")
                            
        return explanation

    def explain_bug(self, file_path, line_number, category, severity, error_message, code_snippet):
        """
        Asks Gemini for a detailed explanation of the bug. Falls back to static templates if offline.
        """
        if not self.is_configured:
            return self.get_fallback_explanation(category, error_message, code_snippet)
            
        prompt = f"""
You are an expert Python Debugger and Senior Software Architect.
Provide a clear, educational, and developer-friendly breakdown of the following Python bug.

CONTEXT DETAILS:
- File Name: {os.path.basename(file_path)}
- File Path: {file_path}
- Line Number: {line_number}
- Error Category: {category}
- Severity: {severity}
- Error Message: {error_message}

CODE SNIPPET CONTAINING BUG:
```python
{code_snippet}
```

Please structure your response with:
1. **Explain the Bug**: What is causing this error in clear, concise terms.
2. **How to Fix**: Actionable steps to resolve the issue.
3. **Corrected Code**: A small code snippet showing the fixed code.
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error querying Gemini AI: {str(e)}\n\n" + self.get_fallback_explanation(category, error_message, code_snippet)

    def generate_fixed_code(self, file_content, file_path, line_number, category, error_message):
        """
        Queries Gemini to repair the file contents. Returns the repaired code or None.
        """
        if not self.is_configured:
            return None  # Rule-based repair requires AST/regex, handled in auto_fixer
            
        prompt = f"""
You are an expert Python Debugger and Code Correction Engine.
You must repair a bug in the following Python file. Return the ENTIRE repaired file content.

BUG DETAILS:
- File Name: {os.path.basename(file_path)}
- File Path: {file_path}
- Line Number: {line_number}
- Error Category: {category}
- Error Message: {error_message}

FULL PYTHON FILE CONTENT:
```python
{file_content}
```

INSTRUCTIONS:
1. Fix the specified error on or around line {line_number}.
2. Ensure you DO NOT change any unrelated logic or structure.
3. Return the ENTIRE corrected Python code inside a single standard markdown code block starting with ```python.
4. Do NOT output explanations or notes. Just output the code block.
"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            # Extract code between ```python and ```
            match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return match.group(1)
            # Fallback if no block found but code is returned directly
            if "def " in text or "import " in text:
                return text.strip()
            return None
        except Exception:
            return None

    def chat_with_assistant(self, chat_history, user_message, scan_context_summary):
        """
        Interacts with the user, keeping context of past scans and conversation.
        """
        if not self.is_configured:
            # Fallback offline chat helper
            lower_msg = user_message.lower()
            if "hello" in lower_msg or "hi" in lower_msg:
                return "Hello! I am your local Bug Fixer assistant running in Offline Mode. Ask me about the bugs detected in your code, and I will try my best to explain them!"
            if "how to fix" in lower_msg or "fix" in lower_msg:
                return "Select an error from the 'Review & Fixes' tab to see detailed suggestions. In offline mode, I can provide static repair suggestions."
            return ("I'm currently running in Offline mode because no Gemini API key is configured. "
                    "For smart AI conversation, please enter your Gemini API key in the sidebar. "
                    "In offline mode, you can still view details on detected issues and check line-by-line lint feedback!")

        # Setup developer instructions/system prompt
        sys_instruction = f"""
You are an AI Coding Assistant named "BugFixer AI" developed for a B.Tech Final Year Project.
Your goal is to help developers debug, refactor, and write clean Python code.

You have access to the following project scan context:
{scan_context_summary}

INSTRUCTIONS:
1. Be helpful, concise, and professional.
2. If asked about specific bugs in the scan, refer to the scan details.
3. Provide code examples in Python using Markdown formatting.
"""
        
        # Build chat structure from history
        contents = []
        # Add system context as a primer message since some models do not support system_instruction argument directly
        contents.append({"role": "user", "parts": [f"System Instructions: {sys_instruction}\n\nUnderstood. Let's begin the chat."]})
        contents.append({"role": "model", "parts": ["Understood. I am BugFixer AI, ready to assist you with the code analysis. Please let me know how I can help!"]})
        
        for msg in chat_history[-15:]:  # Limit history to prevent context overflow
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [msg["message"]]})
            
        contents.append({"role": "user", "parts": [user_message]})
        
        try:
            response = self.model.generate_content(contents)
            return response.text
        except Exception as e:
            return f"Error generating message: {str(e)}"
