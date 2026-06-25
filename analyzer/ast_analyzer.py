import ast
import os

class BugHunterVisitor(ast.NodeVisitor):
    def __init__(self, file_path, code_lines):
        self.file_path = file_path
        self.code_lines = code_lines
        self.issues = []
        self.imported_names = {}  # alias_name -> (node, full_import_name)
        self.used_names = set()

    def add_issue(self, node, severity, category, message, suggestion):
        line_num = getattr(node, 'lineno', 1)
        snippet = ""
        if 0 < line_num <= len(self.code_lines):
            snippet = self.code_lines[line_num - 1].strip()
            
        self.issues.append({
            "file_path": self.file_path,
            "line_number": line_num,
            "severity": severity,
            "category": category,
            "error_message": message,
            "code_snippet": snippet,
            "fix_suggestion": suggestion
        })

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imported_names[name] = (node, alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            full_name = f"{node.module}.{alias.name}" if node.module else alias.name
            self.imported_names[name] = (node, full_name)
        self.generic_visit(node)

    def visit_Name(self, node):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # If we have something like `sys.exit`, sys is a Name
        self.generic_visit(node)

    def visit_Call(self, node):
        # Detect eval() and exec()
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in ('eval', 'exec'):
                self.add_issue(
                    node=node,
                    severity="High",
                    category="Security",
                    message=f"Dangerous call to '{func_name}()' detected.",
                    suggestion=f"Avoid using '{func_name}()' as it can execute arbitrary, untrusted input. Replace it with safe alternatives like json.loads() or ast.literal_eval()."
                )
        self.generic_visit(node)

    def visit_BinOp(self, node):
        # Detect division by zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            # Check if right side is a constant zero
            is_zero = False
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                is_zero = True
            elif isinstance(node.right, ast.Num) and node.right.n == 0: # support python < 3.8
                is_zero = True
                
            if is_zero:
                self.add_issue(
                    node=node,
                    severity="High",
                    category="Logical",
                    message="Division by zero detected.",
                    suggestion="Ensure the divisor is checked for zero or handle the potential ZeroDivisionError using a try-except block."
                )
        self.generic_visit(node)

    def visit_Try(self, node):
        # Detect empty except blocks
        for handler in node.handlers:
            if handler.type is None:
                # Bare except block
                # Check if body is just pass or constant expressions
                is_empty = False
                if len(handler.body) == 1:
                    stmt = handler.body[0]
                    if isinstance(stmt, ast.Pass):
                        is_empty = True
                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        is_empty = True
                
                if is_empty:
                    self.add_issue(
                        node=handler,
                        severity="Medium",
                        category="Code Smell",
                        message="Bare except block with 'pass' detected. This silences all exceptions (including KeyboardInterrupt and SystemExit), making debugging difficult.",
                        suggestion="Avoid bare except. Specify concrete exceptions (e.g. 'except ValueError:' or 'except Exception:') and log/print the error instead of suppressing it with 'pass'."
                    )
        self.generic_visit(node)

    def visit_While(self, node):
        # Detect infinite loops without loop controls (break, return, raise)
        is_infinite_test = False
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            is_infinite_test = True
        elif isinstance(node.test, ast.Name) and node.test.id == 'True':
            is_infinite_test = True
            
        if is_infinite_test:
            # Look for break, return, raise inside the loop body
            has_exit = False
            for subnode in ast.walk(node):
                if isinstance(subnode, (ast.Break, ast.Return, ast.Raise)):
                    has_exit = True
                    break
            if not has_exit:
                self.add_issue(
                    node=node,
                    severity="High",
                    category="Performance",
                    message="Potential infinite loop detected. 'while True' has no exit condition (break, return, or raise).",
                    suggestion="Add a check inside the loop body and call 'break' to terminate the loop when a condition is met, or use a proper loop guard condition."
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Detect dead code (statements after return, break, continue, raise)
        self.check_dead_code(node.body)
        self.generic_visit(node)

    def visit_If(self, node):
        self.check_dead_code(node.body)
        self.check_dead_code(node.orelse)
        self.generic_visit(node)

    def visit_For(self, node):
        self.check_dead_code(node.body)
        self.check_dead_code(node.orelse)
        self.generic_visit(node)

    def check_dead_code(self, statements):
        """Checks for statements appearing after an exit statement (return, break, continue, raise)."""
        exit_index = -1
        for i, stmt in enumerate(statements):
            if isinstance(stmt, (ast.Return, ast.Break, ast.Continue, ast.Raise)):
                exit_index = i
                break
        if exit_index != -1 and exit_index < len(statements) - 1:
            # There are statements after this!
            dead_node = statements[exit_index + 1]
            self.add_issue(
                node=dead_node,
                severity="Medium",
                category="Code Smell",
                message="Dead code detected. This code is located after a control transfer statement (return, break, continue, or raise) and will never be executed.",
                suggestion="Remove the unreachable code statements or place them before the exit statement if they are intended to run."
            )

def analyze_ast(code_content, file_path):
    """
    Parses code using AST and scans for patterns of bugs and smells.
    """
    issues = []
    lines = code_content.splitlines()
    
    try:
        root = ast.parse(code_content, file_path)
    except Exception:
        # If compilation fails, compile_analyzer catches it. We skip AST analysis here.
        return []

    visitor = BugHunterVisitor(file_path, lines)
    visitor.visit(root)
    
    # Check for unused imports after tree traversal
    for name, (node, full_name) in visitor.imported_names.items():
        if name not in visitor.used_names:
            # The import name was never used!
            visitor.add_issue(
                node=node,
                severity="Low",
                category="Code Smell",
                message=f"Unused import '{full_name}' detected.",
                suggestion="Remove this import statement to keep the code clean and reduce startup times."
            )
            
    return visitor.issues
