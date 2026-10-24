"""Build the proposal PDF from the editable Markdown sources.

Uses ReportLab only. This script formats documents; it is not a motor model.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/EV_Motor_Thermal_Monitoring_Proposal.pdf'
FONT_DIR = Path('/System/Library/Fonts/Supplemental')

for family, filename in [
    ('Body', 'Arial.ttf'), ('BodyBold', 'Arial Bold.ttf'),
    ('BodyItalic', 'Arial Italic.ttf'), ('Mono', 'Courier New.ttf'),
]:
    pdfmetrics.registerFont(TTFont(family, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='BodyItalic', boldItalic='BodyBold')

INK = colors.HexColor('#142B40')
TEAL = colors.HexColor('#087F8C')
MUTED = colors.HexColor('#526575')
LIGHT = colors.HexColor('#EDF5F6')
BORDER = colors.HexColor('#D5E1E7')
PAGE_W, PAGE_H = A4
WIDTH = PAGE_W - 104

STYLES = {
    'title': ParagraphStyle('title', fontName='BodyBold', fontSize=22.5, leading=27,
                            textColor=INK, spaceAfter=17, keepWithNext=True),
    'h1': ParagraphStyle('h1', fontName='BodyBold', fontSize=17.5, leading=22,
                         textColor=INK, spaceAfter=10, keepWithNext=True),
    'h2': ParagraphStyle('h2', fontName='BodyBold', fontSize=10.7, leading=14,
                         textColor=TEAL, spaceBefore=8, spaceAfter=5, keepWithNext=True),
    'p': ParagraphStyle('p', fontName='Body', fontSize=9.5, leading=13.3,
                        textColor=INK, spaceAfter=5.5, alignment=TA_LEFT,
                        splitLongWords=True, allowWidows=0, allowOrphans=0),
    'bullet': ParagraphStyle('bullet', fontName='Body', fontSize=9.5, leading=13.2,
                             textColor=INK, leftIndent=11, firstLineIndent=-8,
                             spaceAfter=4, splitLongWords=True),
    'cell': ParagraphStyle('cell', fontName='Body', fontSize=8.7, leading=11.8,
                           textColor=INK, splitLongWords=True),
    'th': ParagraphStyle('th', fontName='BodyBold', fontSize=8.7, leading=11.8,
                         textColor=colors.white, splitLongWords=True),
}


def inline(text: str) -> str:
    code = []
    def protect(match):
        code.append(html.escape(match.group(1)))
        return f'@@CODE{len(code)-1}@@'
    text = re.sub(r'`([^`]+)`', protect, text)
    text = html.escape(text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
    # Plain source URLs become active links in the PDF.
    text = re.sub(r'(https://[^\s<>]+)', r'<link href="\1" color="#087F8C">\1</link>', text)
    for index, value in enumerate(code):
        text = text.replace(f'@@CODE{index}@@', f'<font name="Mono" size="8.4">{value}</font>')
    return text


class Architecture(Flowable):
    def __init__(self):
        super().__init__()
        self.width = WIDTH
        self.height = 115

    def draw(self):
        c = self.canv
        bw = 150
        xs = [0, 171, 342]

        def box(x, y, title, lines):
            c.setFillColor(LIGHT)
            c.setStrokeColor(BORDER)
            c.roundRect(x, y, bw, 43, 6, stroke=1, fill=1)
            c.setFillColor(INK)
            c.setFont('BodyBold', 8.9)
            c.drawCentredString(x + bw/2, y + 29, title)
            c.setFont('Body', 8.1)
            for k, line in enumerate(lines):
                c.drawCentredString(x + bw/2, y + 16 - 10*k, line)

        def arrow(x1, y1, x2, y2):
            c.setStrokeColor(TEAL)
            c.setFillColor(TEAL)
            c.setLineWidth(1.3)
            c.line(x1, y1, x2, y2)
            p = c.beginPath()
            if x1 == x2:
                p.moveTo(x2, y2); p.lineTo(x2-3, y2+5); p.lineTo(x2+3, y2+5)
            else:
                p.moveTo(x2, y2); p.lineTo(x2-5, y2-3); p.lineTo(x2-5, y2+3)
            p.close()
            c.drawPath(p, fill=1, stroke=0)

        box(xs[0], 68, 'Operating measurements', ['Electrical signals, speed', 'coolant and ambient'])
        box(xs[1], 68, 'Causal input handling', ['Valid value, mask, age', 'history and fallback'])
        box(xs[2], 68, 'Thermal neural model', ['Heat-transfer state update', 'four virtual temperatures'])
        arrow(151, 89, 169, 89)
        arrow(322, 89, 340, 89)
        arrow(417, 67, 417, 53)
        box(xs[0], 8, 'Evaluation references', ['Measured target temperatures', 'excluded from model inputs'])
        box(xs[1], 8, 'Replay dashboard', ['Component estimates', 'advisory torque display'])
        box(xs[2], 8, 'Calibrated upper bounds', ['Separate calibration profiles', 'measured coverage and width'])
        # Bounds feed the replay panel, drawn right-to-left.
        c.setStrokeColor(TEAL); c.line(340, 29, 323, 29)
        p = c.beginPath(); p.moveTo(323,29); p.lineTo(328,26); p.lineTo(328,32); p.close()
        c.drawPath(p, fill=1, stroke=0)


def table_widths(rows):
    if rows[0][0] == 'Week':
        return [43, 167, WIDTH-210]
    if rows[0][0] in {'Planned path', 'Signal group'}:
        if len(rows[0]) == 2:
            return [150, WIDTH-150]
        return [91, 164, WIDTH-255]
    if len(rows[0]) == 2:
        return [192, WIDTH-192]
    if rows[0][0] == 'Scenario':
        return [103, 186, WIDTH-289]
    if rows[0][0] == 'Model':
        return [166, 146, WIDTH-312]
    return [WIDTH/len(rows[0])] * len(rows[0])


def make_table(rows):
    cells = [[Paragraph(inline(s), STYLES['th' if i == 0 else 'cell'])
              for s in row] for i, row in enumerate(rows)]
    t = Table(cells, colWidths=table_widths(rows), repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), INK),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [LIGHT, colors.white]),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 4.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.2),
        ('LINEBELOW', (0,-1), (-1,-1), .5, BORDER),
    ]))
    return [Spacer(1, 3), t, Spacer(1, 8)]


def parse_markdown(path: Path, first: bool = False):
    lines = path.read_text().splitlines()
    story = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1; continue
        if line == '<!-- pagebreak -->':
            story.append(PageBreak()); i += 1; continue
        if line == '<!-- architecture -->':
            story.extend([Architecture(), Spacer(1,5)]); i += 1; continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row = [s.strip() for s in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+', s) for s in row):
                    rows.append(row)
                i += 1
            story.extend(make_table(rows)); continue
        if line.startswith('## '):
            story.append(Paragraph(inline(line[3:]), STYLES['h2'])); i += 1; continue
        if line.startswith('# '):
            style = STYLES['title'] if first and not story else STYLES['h1']
            story.append(Paragraph(inline(line[2:]), style)); i += 1; continue
        if line.startswith('- '):
            story.append(Paragraph('- ' + inline(line[2:]), STYLES['bullet'])); i += 1; continue
        if re.match(r'^\d+\. ', line):
            story.append(Paragraph(inline(line), STYLES['bullet'])); i += 1; continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '|', '<!--', '- ')):
            paragraph.append(lines[i].strip()); i += 1
        story.append(Paragraph(inline(' '.join(paragraph)), STYLES['p']))
    return story


def decorate(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(TEAL)
    canvas.rect(52, PAGE_H-39, 18, 3, fill=1, stroke=0)
    canvas.setFont('BodyBold', 8)
    canvas.setFillColor(INK)
    canvas.drawString(78, PAGE_H-39, 'THERMOGUARD MOTOR')
    canvas.setFont('Body', 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W-52, PAGE_H-39, 'PROJECT PROPOSAL AND IMPLEMENTATION PLAN')
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(.4)
    canvas.line(52, 43, PAGE_W-52, 43)
    canvas.setFont('Body', 7.5)
    canvas.drawString(52, 30, '24 October 2026   /   Proposed study. Experiments pending.')
    canvas.drawRightString(PAGE_W-52, 30, str(doc.page))
    canvas.restoreState()


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=52, rightMargin=52,
                          topMargin=60, bottomMargin=57,
                          title='EV Motor Thermal Monitoring: Proposal and Implementation Plan',
                          author='Lakshya College Project',
                          subject='Fault-tolerant physics-guided thermal state estimation for EV motors')
    doc.addPageTemplates(PageTemplate(id='main', frames=[
        Frame(52, 57, WIDTH, PAGE_H-117, leftPadding=0, rightPadding=0,
              topPadding=0, bottomPadding=0)
    ], onPage=decorate))
    story = parse_markdown(ROOT/'docs/project_proposal.md', first=True)
    story.append(PageBreak())
    story.extend(parse_markdown(ROOT/'docs/implementation_plan.md'))
    story.append(PageBreak())
    story.extend(parse_markdown(ROOT/'docs/references.md'))
    doc.build(story)
    print(OUT)


if __name__ == '__main__':
    main()
