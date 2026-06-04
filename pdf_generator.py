import re
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

def create_pdf(markdown_text: str) -> bytes:
    """
    Converts basic markdown text containing headers, bold, and italics 
    into a PDF byte stream using reportlab.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    flowables = []
    
    lines = markdown_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            flowables.append(Spacer(1, 12))
            continue
            
        # Escape XML characters to prevent ReportLab crashes
        safe_line = escape(line)
        
        # Parse bold and italics
        safe_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_line)
        safe_line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', safe_line)
        
        # Handle Headers and Paragraphs
        if safe_line.startswith('# '):
            flowables.append(Paragraph(safe_line[2:], styles['Heading1']))
        elif safe_line.startswith('## '):
            flowables.append(Paragraph(safe_line[3:], styles['Heading2']))
        elif safe_line.startswith('### '):
            flowables.append(Paragraph(safe_line[4:], styles['Heading3']))
        elif safe_line.startswith('- ') or safe_line.startswith('* '):
            # Simplistic list item rendering as an indented paragraph
            flowables.append(Paragraph("&bull; " + safe_line[2:], styles['Normal']))
        else:
            flowables.append(Paragraph(safe_line, styles['Normal']))
            
    doc.build(flowables)
    return buffer.getvalue()