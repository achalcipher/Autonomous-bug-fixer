import os
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
import numpy as np

class BugReportPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_cover_page = True

    def header(self):
        if self.page_no() == 1:
            # Skip header on cover page
            return
            
        # Draw top banner line and title
        self.set_fill_color(30, 41, 59) # Slate Dark
        self.rect(0, 0, 210, 15, 'F')
        
        self.set_text_color(255, 255, 255)
        self.set_font('helvetica', 'B', 10)
        self.set_xy(10, 2)
        self.cell(0, 10, 'Autonomous Python Bug Detection and Fix Report', align='L')
        
        self.set_font('helvetica', 'I', 8)
        self.set_xy(10, 2)
        self.cell(0, 10, f'Project Run History Report', align='R')
        
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        
        # Draw thin bottom boundary line
        self.line(10, 282, 200, 282)
        
        self.cell(0, 10, f'Autonomous Bug Fixer System | Page {self.page_no()}/{{nb}}', align='C')

def generate_pdf_report(scan_summary, scan_details, output_path):
    """
    Generates a high-quality visual PDF report of scan results.
    """
    # Create matplotlib chart for embedding
    chart_path = None
    try:
        severities = ['Critical', 'High', 'Medium', 'Low']
        counts = [
            scan_summary.get('critical_count', 0),
            scan_summary.get('high_count', 0),
            scan_summary.get('medium_count', 0),
            scan_summary.get('low_count', 0)
        ]
        
        # Color coding
        colors = ['#EF4444', '#F97316', '#EAB308', '#3B82F6'] # Red, Orange, Gold, Blue
        
        # Filter to severities with counts > 0 for cleaner visuals
        active_sevs = []
        active_counts = []
        active_colors = []
        for s, c, col in zip(severities, counts, colors):
            if c > 0:
                active_sevs.append(s)
                active_counts.append(c)
                active_colors.append(col)
                
        if not active_counts:
            # Default empty chart if no issues found
            active_sevs = ['No Issues']
            active_counts = [1]
            active_colors = ['#10B981'] # Green
            
        fig, ax = plt.subplots(figsize=(6, 4))
        wedges, texts, autotexts = ax.pie(
            active_counts, 
            labels=active_sevs, 
            autopct=lambda pct: f'{pct:.1f}%' if sum(counts) > 0 else '',
            startangle=140, 
            colors=active_colors,
            wedgeprops=dict(width=0.4, edgecolor='w') # Donut chart style
        )
        plt.setp(texts, size=10, weight="bold")
        plt.setp(autotexts, size=9, weight="bold")
        ax.set_title("Vulnerability & Bug Severity Distribution", fontsize=12, pad=20, weight="bold")
        
        # Write to temporary file
        chart_path = output_path.replace(".pdf", "_chart.png")
        plt.tight_layout()
        plt.savefig(chart_path, dpi=300)
        plt.close()
    except Exception as chart_err:
        print("Error generating chart for PDF:", chart_err)

    # Initialize FPDF
    pdf = BugReportPDF(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    
    # ------------------ COVER PAGE ------------------
    pdf.add_page()
    
    # Decorative Header Panel (Dark Blue/Slate)
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(0, 0, 210, 80, 'F')
    
    pdf.set_xy(10, 25)
    pdf.set_font('helvetica', 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(0, 10, 'Autonomous Bug Detection &\nFix Recommendation System', align='C')
    
    pdf.set_xy(10, 52)
    pdf.set_font('helvetica', 'I', 11)
    pdf.set_text_color(203, 213, 225)
    pdf.cell(0, 10, 'B.Tech Final Year Engineering Project Report Dossier', align='C')
    
    # Main Body elements
    pdf.set_text_color(30, 41, 59)
    pdf.set_xy(10, 95)
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'Project Evaluation Summary', ln=1, align='L')
    pdf.line(10, 105, 200, 105)
    pdf.ln(5)
    
    # Metadata Details Table
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(45, 8, 'Project Name:', border=1, fill=False)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(145, 8, str(scan_summary.get('project_name', 'Unknown')), border=1, ln=1)
    
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(45, 8, 'Scan Timestamp:', border=1, fill=False)
    pdf.set_font('helvetica', '', 10)
    # format timestamp nicely
    ts = scan_summary.get('timestamp', '')
    try:
        dt = datetime.fromisoformat(ts)
        formatted_ts = dt.strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        formatted_ts = ts
    pdf.cell(145, 8, formatted_ts, border=1, ln=1)
    
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(45, 8, 'Total Files Checked:', border=1, fill=False)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(145, 8, str(scan_summary.get('file_count', 0)), border=1, ln=1)
    
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(45, 8, 'Scan Run Status:', border=1, fill=False)
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(16, 185, 129) # green
    pdf.cell(145, 8, str(scan_summary.get('status', 'Completed')), border=1, ln=1)
    
    pdf.set_text_color(30, 41, 59)
    pdf.ln(10)
    
    # Add Pie Chart Image
    if chart_path and os.path.exists(chart_path):
        pdf.image(chart_path, x=45, y=145, w=120)
        
    # Page breaks for subsequent contents
    # ------------------ DETAILED LOGS PAGE ------------------
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, 'Executive Summary & Severity Counts', ln=1)
    pdf.line(10, 20, 200, 20)
    pdf.ln(5)
    
    # Severity Cards (Grid Layout)
    pdf.set_font('helvetica', 'B', 10)
    
    # Critical Box
    pdf.set_fill_color(254, 226, 226) # soft red
    pdf.set_text_color(220, 38, 38)
    pdf.cell(45, 15, f"CRITICAL: {scan_summary.get('critical_count', 0)}", border=1, fill=True, align='C')
    
    # High Box
    pdf.set_fill_color(255, 237, 213) # soft orange
    pdf.set_text_color(234, 88, 12)
    pdf.cell(45, 15, f"HIGH: {scan_summary.get('high_count', 0)}", border=1, fill=True, align='C')
    
    # Medium Box
    pdf.set_fill_color(254, 249, 195) # soft yellow
    pdf.set_text_color(161, 98, 7)
    pdf.cell(45, 15, f"MEDIUM: {scan_summary.get('medium_count', 0)}", border=1, fill=True, align='C')
    
    # Low Box
    pdf.set_fill_color(219, 234, 254) # soft blue
    pdf.set_text_color(37, 99, 235)
    pdf.cell(45, 15, f"LOW: {scan_summary.get('low_count', 0)}", border=1, fill=True, ln=1, align='C')
    
    pdf.set_text_color(30, 41, 59)
    pdf.ln(10)
    
    # Issues Table
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 8, 'Bug Log Summary Table', ln=1)
    
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(10, 8, 'S.No', border=1, fill=True, align='C')
    pdf.cell(45, 8, 'File Name', border=1, fill=True, align='C')
    pdf.cell(15, 8, 'Line', border=1, fill=True, align='C')
    pdf.cell(20, 8, 'Severity', border=1, fill=True, align='C')
    pdf.cell(30, 8, 'Category', border=1, fill=True, align='C')
    pdf.cell(70, 8, 'Issue Details', border=1, fill=True, ln=1, align='C')
    
    pdf.set_font('helvetica', '', 8)
    for idx, detail in enumerate(scan_details, 1):
        # Truncate strings to prevent multi-line breaks inside generic table cells
        filename = os.path.basename(detail.get('file_path', ''))
        if len(filename) > 22:
            filename = filename[:19] + "..."
            
        errmsg = detail.get('error_message', '')
        if len(errmsg) > 42:
            errmsg = errmsg[:39] + "..."
            
        pdf.cell(10, 7, str(idx), border=1, align='C')
        pdf.cell(45, 7, filename, border=1)
        pdf.cell(15, 7, str(detail.get('line_number', '')), border=1, align='C')
        
        # Color code severity inside table
        sev = detail.get('severity', 'Low')
        pdf.set_font('helvetica', 'B', 8)
        if sev == 'Critical':
            pdf.set_text_color(220, 38, 38)
        elif sev == 'High':
            pdf.set_text_color(234, 88, 12)
        elif sev == 'Medium':
            pdf.set_text_color(161, 98, 7)
        else:
            pdf.set_text_color(37, 99, 235)
            
        pdf.cell(20, 7, sev, border=1, align='C')
        pdf.set_text_color(30, 41, 59)
        pdf.set_font('helvetica', '', 8)
        
        pdf.cell(30, 7, detail.get('category', ''), border=1)
        pdf.cell(70, 7, errmsg, border=1, ln=1)
        
    # ------------------ DETAILED ERROR SHEETS ------------------
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, 'Detailed Error Logs & Fix Recommendations', ln=1)
    pdf.line(10, 20, 200, 20)
    pdf.ln(5)
    
    for idx, detail in enumerate(scan_details, 1):
        # Check if space is low before printing this block (requires ~60mm)
        if pdf.get_y() > 220:
            pdf.add_page()
            
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_fill_color(248, 250, 252) # light slate
        
        # Headline header
        severity = detail.get('severity', 'Low')
        category = detail.get('category', 'Bug')
        pdf.cell(0, 8, f"Bug #{idx}: [{severity}] {category} in {os.path.basename(detail.get('file_path',''))} (Line {detail.get('line_number','')})", border='TB', fill=True, ln=1)
        pdf.ln(2)
        
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(30, 5, "Error Message:", ln=0)
        pdf.set_font('helvetica', '', 9)
        pdf.multi_cell(0, 5, detail.get('error_message', ''))
        
        # If code snippet exists
        snippet = detail.get('code_snippet', '')
        if snippet:
            pdf.ln(1)
            pdf.set_font('helvetica', 'B', 9)
            pdf.cell(30, 5, "Offending Line:", ln=1)
            
            # Print code block in monospaced Courier
            pdf.set_font('courier', '', 8.5)
            pdf.set_fill_color(241, 245, 249)
            pdf.set_text_color(51, 65, 85)
            pdf.multi_cell(0, 5, f" {snippet} ", border=1, fill=True)
            
            # Reset font and color
            pdf.set_text_color(30, 41, 59)
            
        pdf.ln(1)
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(30, 5, "Recommended Fix:", ln=0)
        pdf.set_font('helvetica', '', 9)
        pdf.multi_cell(0, 5, detail.get('fix_suggestion', 'No suggestions provided.'))
        
        pdf.ln(6)
        
    # Save PDF
    pdf.output(output_path)
    
    # Cleanup temporary chart image
    if chart_path and os.path.exists(chart_path):
        try:
            os.remove(chart_path)
        except Exception:
            pass
            
    return output_path
