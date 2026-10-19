"""Build an editable Sprint 1 deck. All copy lives in text boxes or table cells."""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt
from lxml import etree

OUT = r"c:\Users\LIUSI\Desktop\NUS\DSS5105\DSS5105_26fall_Group10_TheGeneralManager-sCo-Pilot\Presentation_Group10_Sprint1.pptx"

INK = RGBColor(0x1C, 0x19, 0x17)
PAPER = RGBColor(0xF6, 0xF3, 0xEE)
BRASS = RGBColor(0x8C, 0x6A, 0x3D)
CARD = RGBColor(0xFF, 0xFC, 0xF8)
MUTED = RGBColor(0x5C, 0x56, 0x4E)
LINE = RGBColor(0xE4, 0xDD, 0xD2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Calibri"


def set_run(run, text, size, bold=False, color=INK, font=FONT):
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    r_pr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        node = r_pr.find(qn(tag))
        if node is None:
            node = etree.SubElement(r_pr, qn(tag))
        node.set("typeface", font)


def add_text(slide, l, t, w, h, lines, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    shape = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    shape.text_frame.paragraphs[0].alignment = align
    tf.paragraphs[0].space_after = Pt(0)
    # anchor
    body = tf._txBody
    body_pr = body.find(qn("a:bodyPr"))
    body_pr.set("anchor", {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}[anchor])
    if isinstance(lines, str):
        lines = [lines]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(6)
        p.level = 0
        content, is_bold, col, sz = line if isinstance(line, tuple) else (line, bold, color, size)
        run = p.add_run()
        set_run(run, content, sz, is_bold, col)
    return shape


def fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def rect(slide, l, t, w, h, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    fill(shape, color)
    return shape


def card(slide, l, t, w, h):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    fill(shape, CARD)
    shape.line.color.rgb = LINE
    shape.line.width = Pt(1)
    return shape


def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    rect(slide, 0, 0, 13.333, 7.5, PAPER)
    rect(slide, 0, 0, 0.12, 7.5, BRASS)
    return slide


def footer(slide, page, total=8):
    add_text(slide, 0.45, 7.12, 8, 0.28, "Group 10  ·  Sprint 1  ·  Edit the text in place", 11, color=MUTED)
    add_text(slide, 11.4, 7.12, 1.5, 0.28, f"{page} / {total}", 11, color=MUTED, align=PP_ALIGN.RIGHT)


def kicker(slide, text):
    add_text(slide, 0.5, 0.32, 12, 0.32, text, 13, True, BRASS)


def title(slide, text):
    add_text(slide, 0.5, 0.62, 12.2, 0.7, text, 32, True)


def build():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Presentation_Group10_Sprint1"
    prs.core_properties.subject = "SweaterCo GM Co-Pilot Sprint 1"

    # 1 title
    s = new_slide(prs)
    add_text(s, 0.55, 1.45, 12, 0.35, "DSS5105  ·  TRACK 1  ·  WEEK 9  ·  5 MINUTES", 14, True, BRASS)
    add_text(s, 0.55, 1.95, 12, 1.2, "The General Manager's Co-Pilot", 40, True)
    add_text(s, 0.55, 3.25, 11.5, 0.45, "Sprint 1 review  ·  Group 10  ·  16 October 2026", 22, color=MUTED)
    add_text(
        s, 0.55, 4.15, 11.4, 1.6,
        "One promise: the manager does not write SQL, and one question returns a result they can check. This is not a product launch. We are here to show the problem is worth solving, and that the first cut has already met a real question.",
        22,
    )
    footer(s, 1)

    # 2 problem
    s = new_slide(prs)
    kicker(s, "1   PROBLEM")
    title(s, "The manager asks all day, and cannot write SQL")
    add_text(s, 0.5, 1.48, 12.3, 0.7, "They move between the office, the floor, and meetings. The questions do not stop at 7:00. Today each one is a phone call to the planner, a wait, and an answer that is sometimes wrong.", 18)
    times = [
        ("7:00", "Did anything go wrong yesterday?"),
        ("9:40", "How is the TrendCart order doing?"),
        ("11:15", "800 hoodies by the 25th. Can we take it?"),
        ("14:30", "It hasn't moved in a week. Chase it."),
        ("17:00", "Remind me if packing is still behind."),
    ]
    x = 0.45
    for clock, line in times:
        card(s, x, 2.4, 2.4, 2.35)
        add_text(s, x + 0.15, 2.55, 2.1, 0.4, clock, 20, True, BRASS)
        add_text(s, x + 0.15, 3.1, 2.1, 1.35, line, 14)
        x += 2.55
    add_text(s, 0.5, 5.05, 12.3, 1.6, "The data is already in the database. The block is the query. Sundays are closed, remaining time is counted by stage, and overdue, stalled, and about to miss the due date are not the same thing. The goal is a co-pilot that takes these questions directly — not a dashboard, and not a chat toy.", 18)
    footer(s, 2)

    # 3 solution
    s = new_slide(prs)
    kicker(s, "1   SOLUTION")
    title(s, "The deliverable is a tool set, not a text box")
    add_text(s, 0.5, 1.5, 12.3, 1.05, "The manager asks in English. The model picks one written tool. Totals, comparisons, and days left are computed in Python. The model only states that result. A side effect is confirmed, then logged.", 18)
    card(s, 0.5, 2.75, 6.05, 3.9)
    card(s, 6.8, 2.75, 6.0, 3.9)
    add_text(s, 0.75, 2.95, 5.5, 0.4, "Narrow tools, not one run_sql", 16, True, BRASS)
    add_text(s, 0.75, 3.5, 5.5, 2.8, "One run_sql is flexible, and it invents joins. Narrow tools are reliable, and blind to questions we did not anticipate. We accept that second failure, and we write down what each tool does not do.", 18)
    add_text(s, 7.05, 2.95, 5.5, 0.4, "Sprint 1 proves the first cut", 16, True, BRASS)
    add_text(s, 7.05, 3.5, 5.5, 2.8, "The five questions are the destination. This round takes one of them — which orders will miss the due date — from English to a table that matches the rule. The scheduled briefing, self-firing watches, and real email come later.", 18)
    footer(s, 3)

    # 4 architecture
    s = new_slide(prs)
    kicker(s, "1   ARCHITECTURE")
    title(s, "The model picks the tool. Python does the arithmetic.")
    steps = [
        ("1", "The manager's English question"),
        ("2", "Clarify first\nNo field, refuse\nNo tool, refuse"),
        ("3", "The model picks one narrow tool"),
        ("4", "Python computes\nSQL stays here\nHidden from the manager"),
        ("5", "A few lines first\nWhy shows the source rows"),
    ]
    x = 0.4
    for i, (num, label) in enumerate(steps):
        card(s, x, 1.7, 2.3, 2.45)
        add_text(s, x + 0.12, 1.82, 2.05, 0.35, num, 14, True, BRASS)
        add_text(s, x + 0.12, 2.25, 2.05, 1.7, label, 14, True)
        if i < len(steps) - 1:
            add_text(s, x + 2.18, 2.55, 0.32, 0.4, "→", 18, True, BRASS, PP_ALIGN.CENTER)
        x += 2.58
    add_text(s, 0.5, 4.35, 12.3, 0.35, "Five kinds of tool are the minimum. Sprint 1 has already touched retrieval, an inspectable judgement, and tracing.", 16, True)
    kinds = [
        ("Retrieval", "Get the facts"),
        ("Judgement", "Define what normal is"),
        ("Tracing", "Answer why"),
        ("Discovery", "Find what nobody asked"),
        ("Action", "Confirm, then log"),
    ]
    x = 0.45
    for name, desc in kinds:
        card(s, x, 4.9, 2.4, 1.75)
        add_text(s, x + 0.12, 5.05, 2.15, 0.55, name, 14, True, BRASS)
        add_text(s, x + 0.12, 5.65, 2.15, 0.75, desc, 15)
        x += 2.55
    footer(s, 4)

    # 5 business value
    s = new_slide(prs)
    kicker(s, "2   BUSINESS VALUE")
    title(s, "We save the planner's morning, and the callbacks")
    add_text(s, 0.5, 1.5, 12.3, 0.7, "The brief names two stretches of time: the planner's half hour each morning, and every \"let me check and call you back\" during the day. We do not invent a dollar amount.", 18)
    values = [
        ("Faster", "The manager does not wait for someone else to write the SQL."),
        ("Clearer", "The first glance is a few lines. Source rows are one click away, under Why."),
        ("Sounder", "No selling price means we say so. Numbers come from a written rule, not mental arithmetic."),
    ]
    top = 2.4
    for label, body in values:
        card(s, 0.5, top, 12.3, 1.2)
        add_text(s, 0.75, top + 0.25, 2.2, 0.7, label, 24, True, BRASS, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, 3.15, top + 0.28, 9.3, 0.7, body, 20, anchor=MSO_ANCHOR.MIDDLE)
        top += 1.35
    footer(s, 5)

    # 6 progress
    s = new_slide(prs)
    kicker(s, "3   SPRINT 1 PROGRESS")
    title(s, "The first question runs. The full day does not.")
    add_text(s, 0.5, 1.55, 12.3, 0.35, "LIVE QUESTION", 14, True, BRASS)
    add_text(s, 0.5, 1.95, 12.3, 0.5, "Which orders are likely to miss their due dates?", 24, True)
    rows = [
        ("List", "ORD-029, ORD-108, ORD-103"),
        ("Evidence", "The numbers under Why come from Python, not from the model."),
        ("Our rule", "ORD-093 is still in WASHING, with two stages left, so days left is floored to 2.0. It is not ranked as nearly done."),
    ]
    top = 2.7
    for label, body in rows:
        card(s, 0.5, top, 12.3, 1.2)
        add_text(s, 0.75, top + 0.28, 2.8, 0.65, label, 18, True, BRASS, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, 3.6, top + 0.22, 8.9, 0.8, body, 18, anchor=MSO_ANCHOR.MIDDLE)
        top += 1.35
    footer(s, 6)

    # 8 risks
    s = new_slide(prs)
    kicker(s, "4   RISK")
    title(s, "These failures would change the plan")
    table = s.shapes.add_table(5, 4, Inches(0.45), Inches(1.65), Inches(12.4), Inches(5.1)).table
    table.columns[0].width = Inches(5.3)
    table.columns[1].width = Inches(1.5)
    table.columns[2].width = Inches(1.3)
    table.columns[3].width = Inches(4.3)
    data = [
        ["Risk", "Likelihood", "Impact", "Next step"],
        ["Vague wording. TrendCart has many orders, and the model picks one.", "High", "High", "Ask. Do not guess."],
        ["The model does the arithmetic and states a number that does not match.", "High", "High", "Numbers come only from Python tools."],
        ["No selling price in the data, and the model invents a revenue.", "Medium", "High", "Refuse. This is the worst failure."],
        ["Already seen: ord-099 returned nothing. The prose had days left; the table did not.", "High", "Medium", "Uppercase the id. Put used fields in the table."],
    ]
    for r, row in enumerate(data):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.text = ""
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            set_run(run, value, 12 if r else 14, bold=(r == 0), color=WHITE if r == 0 else INK)
            cell.fill.solid()
            cell.fill.fore_color.rgb = INK if r == 0 else (CARD if r % 2 else RGBColor(0xFB, 0xF7, 0xF1))
            cell.margin_left = Inches(0.12)
            cell.margin_right = Inches(0.08)
    footer(s, 7)

    # 9
    s = new_slide(prs)
    kicker(s, "5–6   ASSUMPTIONS  ·  SPRINT 2")
    title(s, "If an assumption fails, we change course")
    add_text(s, 0.5, 1.48, 6.1, 0.35, "Key assumptions", 16, True, BRASS)
    assumptions = [
        "1  The manager wants a few lines first, and source rows one click away.",
        "2  Factory day is 2026-04-01. Sundays are closed. Counting a Sunday into the average is already wrong.",
        "3  What a narrow tool cannot see is covered by stating what that tool does not do.",
        "4  One stage takes at least one working day. Output is factory-wide, so it cannot say which day one order stopped.",
        "5  Chase, note, and reminder require confirmation. Proactive alerts are a dial, not a switch.",
    ]
    top = 1.95
    for line in assumptions:
        add_text(s, 0.5, top, 6.15, 0.85, line, 14)
        top += 0.82
    card(s, 6.9, 1.48, 5.9, 4.7)
    add_text(s, 7.1, 1.65, 5.5, 0.35, "Sprint 2 roadmap and success", 16, True, BRASS)
    done = [
        "9:40  Several TrendCart orders: ask which one. Success: a clarification, not a guess.",
        "11:15  800 hoodies: an estimate with the assumptions stated, not a yes.",
        "Why it is at risk: go back to the source rows. Do not paraphrase the last reply.",
        "Held-out questions, including one with no answer and one feasibility check. Order-id case no longer misses.",
    ]
    top = 2.15
    for line in done:
        add_text(s, 7.1, top, 5.5, 0.9, line, 14)
        top += 0.95
    add_text(
        s, 0.5, 6.35, 12.3, 0.6,
        "The plan has already met one real question. Next round we test the rest of the manager's day.",
        16, True,
    )
    footer(s, 8)

    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
