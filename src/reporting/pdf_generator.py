import io
import logging
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from src.state import AgentState

logger = logging.getLogger(__name__)

# --- STEP 23: PDF Template Architecture ---
def generate_neighborhood_report(state: AgentState) -> bytes:
    """Generates a branded A4 PDF report from the AgentState."""
    logger.info("Generating PDF Report...")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Branding & Header
    story.append(Paragraph(f"Awaas AI - Neighborhood Intelligence Report", styles['Title']))
    story.append(Paragraph(f"Location PIN: {state.pincode}", styles['Heading3']))
    story.append(Spacer(1, 12))

    # AI Summary
    story.append(Paragraph("AI Synthesis", styles['Heading2']))
    story.append(Paragraph(state.aisummary, styles['Normal']))
    story.append(Spacer(1, 12))

    # Risk Radar
    story.append(Paragraph("Risk Radar", styles['Heading2']))
    for risk in state.riskflags:
        story.append(Paragraph(f"- {risk}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Recommendation
    story.append(Paragraph("Investment Recommendation", styles['Heading2']))
    story.append(Paragraph(state.recommendation, styles['Normal']))
    story.append(Spacer(1, 12))

    # Source References
    story.append(Paragraph("Verified Data Sources", styles['Heading2']))
    for link in state.sourcelinks:
        # Format for clickable hyperlinks in PDF
        display_text = link.split(':', 1)[0]
        url = link.split(':', 1)[1].strip()
        safe_url = url.replace("&", "&amp;")
        link_html = f'<a href="{safe_url}" color="blue">{display_text}</a>'
        story.append(Paragraph(f"- {link_html}", styles['Normal']))
    
    story.append(Spacer(1, 24))
    story.append(Paragraph("Disclaimer: Data sourced from live Indian government open portals.", styles['Italic']))

    try:
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    except Exception as e:
        logger.error(f"PDF Generation failed: {str(e)}")
        return b""

# --- STEP 24: Markdown Report Formatter ---
def format_markdown_report(state: AgentState) -> str:
    """Formats the AgentState into a clean, shareable Markdown string."""
    logger.info("Generating Markdown Report...")
    
    md = f"## Awaas AI - Neighborhood Snapshot: {state.pincode}\n\n"
    
    md += "### AI Synthesis\n"
    md += f"{state.aisummary}\n\n"
    
    md += "### Risk Radar\n"
    for risk in state.riskflags:
        # Determine visual indicator based on keyword presence
        indicator = "[!]" if "CRITICAL" in risk or "High" in risk else "[*]"
        md += f"* {indicator} {risk}\n"
    md += "\n"
    
    md += "### Recommendation\n"
    md += f"{state.recommendation}\n\n"
    
    md += "### Sources\n"
    for link in state.sourcelinks:
        display_text = link.split(':', 1)[0]
        url = link.split(':', 1)[1].strip()
        md += f"* [{display_text}]({url})\n"
        
    md += "\n*Disclaimer: Generated autonomously via Indian open-data APIs.*"
    
    return md