import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bug_fixer.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initializes the database schema if it doesn't already exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create scans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            scan_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            project_name TEXT NOT NULL,
            file_count INTEGER DEFAULT 0,
            critical_count INTEGER DEFAULT 0,
            high_count INTEGER DEFAULT 0,
            medium_count INTEGER DEFAULT 0,
            low_count INTEGER DEFAULT 0,
            status TEXT NOT NULL
        )
    """)
    
    # Create scan details table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_details (
            detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            line_number INTEGER,
            severity TEXT NOT NULL,
            category TEXT NOT NULL,
            error_message TEXT NOT NULL,
            code_snippet TEXT,
            fix_suggestion TEXT,
            fixed_code TEXT,
            FOREIGN KEY (scan_id) REFERENCES scans (scan_id) ON DELETE CASCADE
        )
    """)
    
    # Create chat history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (scan_id) REFERENCES scans (scan_id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def save_scan(scan_id, project_name, file_count, critical_count, high_count, medium_count, low_count, status="Completed"):
    """Saves a new scan metadata record or updates an existing one."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT OR REPLACE INTO scans 
        (scan_id, timestamp, project_name, file_count, critical_count, high_count, medium_count, low_count, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (scan_id, timestamp, project_name, file_count, critical_count, high_count, medium_count, low_count, status))
    
    conn.commit()
    conn.close()

def save_scan_detail(scan_id, file_path, line_number, severity, category, error_message, code_snippet, fix_suggestion, fixed_code=None):
    """Saves a detailed issue found during a scan."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO scan_details 
        (scan_id, file_path, line_number, severity, category, error_message, code_snippet, fix_suggestion, fixed_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (scan_id, file_path, line_number, severity, category, error_message, code_snippet, fix_suggestion, fixed_code))
    
    conn.commit()
    conn.close()

def update_fixed_code(detail_id, fixed_code):
    """Updates the fixed code for a specific scan detail."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE scan_details
        SET fixed_code = ?
        WHERE detail_id = ?
    """, (fixed_code, detail_id))
    conn.commit()
    conn.close()

def save_chat_message(scan_id, role, message):
    """Saves an interactive chat assistant message to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO chat_history (scan_id, role, message, timestamp)
        VALUES (?, ?, ?, ?)
    """, (scan_id, role, message, timestamp))
    
    conn.commit()
    conn.close()

def get_chat_history(scan_id):
    """Retrieves chat message logs for a scan."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, message, timestamp 
        FROM chat_history 
        WHERE scan_id = ? 
        ORDER BY chat_id ASC
    """, (scan_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_scans():
    """Retrieves all scans, sorted newest to oldest."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT scan_id, timestamp, project_name, file_count, 
               critical_count, high_count, medium_count, low_count, status
        FROM scans 
        ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_scan_summary(scan_id):
    """Gets metadata for a specific scan."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_scan_details(scan_id):
    """Retrieves all issues associated with a specific scan."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT detail_id, scan_id, file_path, line_number, severity, category, 
               error_message, code_snippet, fix_suggestion, fixed_code
        FROM scan_details 
        WHERE scan_id = ?
        ORDER BY severity ASC, file_path ASC, line_number ASC
    """, (scan_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_scan(scan_id):
    """Deletes a scan and all its details and chat history."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scans WHERE scan_id = ?", (scan_id,))
    cursor.execute("DELETE FROM scan_details WHERE scan_id = ?", (scan_id,))
    cursor.execute("DELETE FROM chat_history WHERE scan_id = ?", (scan_id,))
    conn.commit()
    conn.close()
