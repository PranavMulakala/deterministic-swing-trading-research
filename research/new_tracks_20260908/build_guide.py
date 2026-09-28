"""Render the decision guide; does not read market data or alter strategy rules."""
from html import escape
from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name('DECISION_GUIDE.md')
OUTPUT = ROOT / 'output/pdf/two-new-paper-tracks-decision-guide.pdf'


def inline(text):
    parts = []
    cursor = 0
    for match in re.finditer(r'\[([^]]+)\]\((https?://[^)]+)\)', text):
        parts.append(escape(text[cursor:match.start()]))
        parts.append('<link href="' + escape(match[2], quote=True)
                     + '" color="#087562"><u>' + escape(match[1]) + '</u></link>')
        cursor = match.end()
    parts.append(escape(text[cursor:]))
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', ''.join(parts))


def footer(canvas, doc):
    width, _ = letter
    canvas.setStrokeColor(colors.HexColor('#dce4e9'))
    canvas.line(43, 38, width - 43, 38)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#607382'))
    canvas.drawString(43, 25, 'RESEARCH DESK | Draft proposals, no orders | 8 September 2026')
    canvas.drawRightString(width - 43, 25, str(doc.page))


def build():
    base = ParagraphStyle('body', fontName='Helvetica', fontSize=10.2,
                          leading=14, textColor=colors.HexColor('#182b3a'),
                          spaceAfter=8, alignment=TA_LEFT)
    title = ParagraphStyle('title', parent=base, fontName='Helvetica-Bold',
                           fontSize=21, leading=25, spaceAfter=13, keepWithNext=True)
    heading = ParagraphStyle('heading', parent=base, fontName='Helvetica-Bold',
                             fontSize=12, leading=16, spaceBefore=6,
                             spaceAfter=8, keepWithNext=True)
    bullet = ParagraphStyle('bullet', parent=base, leftIndent=12, bulletIndent=0,
                            spaceAfter=6)
    story = []
    for block in SOURCE.read_text().strip().split('\n\n'):
        if block == '---PAGE---':
            story.append(PageBreak())
        elif block.startswith('# '):
            story.append(Paragraph(inline(block[2:]), title))
        elif block.startswith('## '):
            story.append(Paragraph(inline(block[3:]), heading))
        elif block.startswith('- '):
            for line in block.splitlines():
                story.append(Paragraph(inline(line[2:]), bullet, bulletText='-'))
        elif re.match(r'\d+\. ', block):
            for line in block.splitlines():
                number, content = line.split('. ', 1)
                story.append(Paragraph(inline(content), bullet, bulletText=number+'.'))
        else:
            story.append(Paragraph(inline(block.replace('\n', ' ')), base))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=43,
                            rightMargin=43, topMargin=40, bottomMargin=49,
                            title='Two new paper research tracks - decision guide',
                            author='Research Desk')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == '__main__':
    build()
