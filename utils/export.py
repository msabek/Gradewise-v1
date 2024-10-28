from io import BytesIO
from typing import List, Dict
import pandas as pd
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

class ExportManager:
    # Define styles once at class level
    _pdf_styles = getSampleStyleSheet()
    _custom_styles = {
        'Title': ParagraphStyle(
            'CustomTitle',
            parent=_pdf_styles['Title'],
            fontSize=24,
            spaceAfter=30
        ),
        'Heading2': ParagraphStyle(
            'CustomHeading2',
            parent=_pdf_styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10
        ),
        'Normal': ParagraphStyle(
            'CustomNormal',
            parent=_pdf_styles['Normal'],
            fontSize=10,
            spaceBefore=5,
            spaceAfter=5
        ),
        'Code': ParagraphStyle(
            'CustomCode',
            parent=_pdf_styles['Normal'],
            fontName='Courier',
            fontSize=8,
            leftIndent=20,
            rightIndent=20
        )
    }

    @staticmethod
    def export_to_csv(assignments: List[Dict]) -> str:
        """Export assignments to CSV format"""
        df = pd.DataFrame([{
            'Assignment': a['filename'],
            'Score': a['grade']['score'],
            'Status': a['status'],
            'Feedback': a['grade']['feedback']
        } for a in assignments])
        return df.to_csv(index=False)

    @staticmethod
    def export_to_excel(assignments: List[Dict]) -> bytes:
        """Export assignments to Excel format"""
        summary_data = []
        details_data = []
        
        for assignment in assignments:
            summary_data.append({
                'Assignment': assignment['filename'],
                'Score': assignment['grade']['score'],
                'Status': assignment['status']
            })
            
            details_data.append({
                'Assignment': assignment['filename'],
                'Score': assignment['grade']['score'],
                'Status': assignment['status'],
                'Feedback': assignment['grade']['feedback'],
                'Improvements': '\n'.join(assignment['grade'].get('improvements', []))
            })
        
        with BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Summary sheet
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # Details sheet
                pd.DataFrame(details_data).to_excel(writer, sheet_name='Details', index=False)
                
                # Format worksheets
                workbook = writer.book
                for worksheet in writer.sheets.values():
                    worksheet.set_column('A:A', 30)  # Assignment column
                    worksheet.set_column('B:B', 10)  # Score column
                    worksheet.set_column('C:C', 15)  # Status column
                    worksheet.set_column('D:E', 50)  # Feedback and Improvements columns
            
            return buffer.getvalue()

    @staticmethod
    def export_to_pdf(assignments: List[Dict]) -> bytes:
        """Export assignments to PDF format"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        elements = []
        
        # Add title
        elements.append(Paragraph("Assignment Grading Results", ExportManager._custom_styles['Title']))
        
        # Add summary statistics
        total_assignments = len(assignments)
        successful = sum(1 for a in assignments if a['status'] == 'success')
        average_score = sum(a['grade']['score'] for a in assignments) / total_assignments if total_assignments > 0 else 0
        
        elements.append(Paragraph("Summary Statistics", ExportManager._custom_styles['Heading2']))
        stats_data = [
            ["Total Assignments", str(total_assignments)],
            ["Successfully Processed", f"{successful}/{total_assignments}"],
            ["Average Score", f"{average_score:.2f}/20"]
        ]
        
        stats_table = Table(stats_data)
        stats_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))
        
        # Add detailed results
        elements.append(Paragraph("Detailed Results", ExportManager._custom_styles['Heading2']))
        for assignment in assignments:
            elements.append(Paragraph(f"Assignment: {assignment['filename']}", ExportManager._custom_styles['Normal']))
            elements.append(Paragraph(f"Score: {assignment['grade']['score']}/20", ExportManager._custom_styles['Normal']))
            elements.append(Paragraph(f"Status: {assignment['status']}", ExportManager._custom_styles['Normal']))
            elements.append(Paragraph("Feedback:", ExportManager._custom_styles['Normal']))
            elements.append(Paragraph(assignment['grade']['feedback'], ExportManager._custom_styles['Code']))
            
            if assignment['grade'].get('improvements'):
                elements.append(Paragraph("Improvements:", ExportManager._custom_styles['Normal']))
                for improvement in assignment['grade']['improvements']:
                    elements.append(Paragraph(f"• {improvement}", ExportManager._custom_styles['Code']))
            
            elements.append(Spacer(1, 20))
        
        doc.build(elements)
        return buffer.getvalue()
