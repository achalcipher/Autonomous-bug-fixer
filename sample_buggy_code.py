import os
import sys  # Unused import
import hashlib  # Security check (weak MD5 usage)

# Hardcoded password (Bandit security warning)
DATABASE_PASSWORD = "super_secret_password_123!"

def calculate_average(numbers):
    total = 0
    # Logical Error: NameError if 'count' is used before definition (if numbers is empty)
    for num in numbers:
        total += num
    
    # Bug: Potential ZeroDivisionError if numbers list is empty
    average = total / len(numbers)
    return average
    
    # Dead Code: Statement after return
    print("Average calculated successfully!")

def divide_numbers(a, b):
    try:
        # Potential ZeroDivisionError
        result = a / b
        return result
    except:
        # Bare except (AST / PyLint code smell)
        pass

def process_user_data(user_input):
    # Security risk: Dangerous use of eval() (Bandit / AST warning)
    cleaned_input = eval(user_input)
    
    # Type mismatch bug: Adding string to integer (Mypy type checking error)
    result = cleaned_input + 10
    
    # Unused local variable (PyLint warning)
    temp_var = 100
    
    return result

if __name__ == "__main__":
    print("Testing buggy code analysis...")
    
    # ZeroDivisionError triggered here
    avg = calculate_average([])
    
    # Security warning: Weak MD5 hashing (Bandit check)
    hash_obj = hashlib.md5(b"test")
    print("MD5 hash:", hash_obj.hexdigest())
