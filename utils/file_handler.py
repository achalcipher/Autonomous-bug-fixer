import os
import zipfile
import shutil
import tempfile
import chardet

def unzip_project(zip_file_bytes, extract_to):
    """
    Extracts a zip file (bytes) to a target directory.
    """
    os.makedirs(extract_to, exist_ok=True)
    temp_zip_path = os.path.join(extract_to, "temp_upload.zip")
    
    with open(temp_zip_path, "wb") as f:
        f.write(zip_file_bytes)
        
    with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
        # Extract files, filter out Mac OS X system metadata folder __MACOSX
        for member in zip_ref.namelist():
            if not member.startswith("__MACOSX") and not member.split('/')[-1].startswith('.'):
                zip_ref.extract(member, extract_to)
                
    os.remove(temp_zip_path)

def zip_project(dir_path, zip_output_path):
    """
    Creates a zip archive from a directory.
    """
    shutil.make_archive(zip_output_path.replace(".zip", ""), 'zip', dir_path)
    return zip_output_path

def find_python_files(dir_path):
    """
    Recursively scans the directory and returns list of paths to all Python files.
    """
    python_files = []
    for root, _, files in os.walk(dir_path):
        # Ignore common virtual env, git, or cache directories
        ignore_dirs = {'.git', 'venv', '.venv', 'env', '__pycache__', '.mypy_cache', '.pytest_cache'}
        if any(ignore in root.split(os.sep) for ignore in ignore_dirs):
            continue
            
        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                python_files.append(full_path)
    return python_files

def read_file_content(file_path):
    """
    Safely reads file contents by detecting encoding. Fallback to utf-8 or latin-1.
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
        
        # Check encoding
        result = chardet.detect(raw_data)
        encoding = result['encoding'] or 'utf-8'
        
        try:
            return raw_data.decode(encoding)
        except UnicodeDecodeError:
            return raw_data.decode('latin-1')
    except Exception as e:
        # Fallback
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as read_err:
            return f"# Error reading file {os.path.basename(file_path)}: {str(read_err)}"

def write_file_content(file_path, content):
    """
    Writes contents to a file with UTF-8 encoding.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def cleanup_dir(dir_path):
    """
    Removes directory and all its contents.
    """
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)
