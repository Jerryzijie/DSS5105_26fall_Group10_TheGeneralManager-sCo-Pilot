"""Request-path diagram.

Pass travels to the right along the top, then down a clear rail into execution.
A stop drops straight down from its own step and ends. The two paths do not cross.
"""

import math
from PIL import Image, ImageDraw, ImageFont

OUT = r"c:\Users\LIUSI\Desktop\NUS\DSS5105\DSS5105_26fall_Group10_TheGeneralManager-sCo-Pilot\docs\architecture_request_path.png"

W, H = 2400, 1320
PAPER = (247, 244, 239)
INK = (28, 25, 23)
MUTED = (92, 86, 78)
BRASS = (140, 106, 61)
CARD = (255, 252, 248)
LINE = (206, 198, 186)
STOP = (122, 62, 48)
STOP_BG = (248, 240, 236)
PASS = (36, 78, 64)
PASS_BG = (232, 240, 236)

F = r"C:\Windows\Fonts\msyh.ttc"
FB = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FB if bold else F, size)


def round_rect(d, box, fill, outline, radius=16, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_block(d, box, lines, fnt, fill):
    x0, y0, x1, y1 = box
    gap = 6
    heights = [fnt.getbbox(line)[3] - fnt.getbbox(line)[1] for line in lines]
    total = sum(heights) + gap * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) / 2
    for line, h in zip(lines, heights):
        tw = d.textlength(line, font=fnt)
        d.text((x0 + (x1 - x0 - tw) / 2, y - 2), line, font=fnt, fill=fill)
        y += h + gap


def arrow(d, start, end, color=BRASS, width=4):
    d.line([start, end], fill=color, width=width)
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 13
    d.polygon(
        [
            end,
            (end[0] - size * math.cos(ang - 0.42), end[1] - size * math.sin(ang - 0.42)),
            (end[0] - size * math.cos(ang + 0.42), end[1] - size * math.sin(ang + 0.42)),
        ],
        fill=color,
    )


def poly_arrow(d, points, color):
    for a, b in zip(points, points[1:-1]):
        d.line([a, b], fill=color, width=4)
    arrow(d, points[-2], points[-1], color)


def box(d, rect, lines, kind="main"):
    style = {
        "stop": (STOP_BG, STOP, STOP, font(18, True)),
        "pass": (PASS_BG, PASS, PASS, font(20, True)),
        "main": (CARD, LINE, INK, font(20, True)),
    }
    fill, outline, color, fnt = style[kind]
    round_rect(d, rect, fill, outline)
    text_block(d, rect, lines, fnt, color)


def main():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((48, 32), "SweaterCo GM Co-Pilot", font=font(38, True), fill=INK)
    d.text(
        (48, 84),
        "Request path. The question moves right while it is allowed. A stop drops down and ends.",
        font=font(22),
        fill=MUTED,
    )

    labels = [
        ["Manager", "question"],
        ["POST", "/api/chat"],
        ["route_query"],
        ["assess_ambiguity"],
        ["assess_stored_data"],
        ["assess_tool_coverage"],
    ]
    stops = {
        2: ["Known-absent field", "refuse, no tool"],
        3: ["Two or more readings", "clarification, no lookup"],
        4: ["Field not stored", "missing_data"],
        5: ["No registered tool", "no_tool"],
    }

    left, gap = 48, 22
    bw, top_y0, top_y1 = 300, 160, 300
    rects = []
    for i, lines in enumerate(labels):
        x = left + i * (bw + gap)
        rect = (x, top_y0, x + bw, top_y1)
        rects.append(rect)
        box(d, rect, lines)
        if i:
            mid = (top_y0 + top_y1) // 2
            arrow(d, (rects[i - 1][2] + 3, mid), (rect[0] - 3, mid))

    for i, lines in stops.items():
        x0, _, x1, _ = rects[i]
        stop = (x0, 360, x1, 500)
        box(d, stop, lines, "stop")
        arrow(d, ((x0 + x1) // 2, top_y1 + 2), ((x0 + x1) // 2, 352), STOP)

    # Rail stays to the right of the last box, so it never enters a stop card.
    last = rects[-1]
    rail_x = last[2] + 70
    exec_y0, exec_y1 = 760, 940
    exec_specs = [
        (["LangGraph ReAct", "one registered tool"], "pass"),
        (["Python services", "read PostgreSQL"], "main"),
        (["Tool JSON", "+ trace"], "main"),
        (["draw or render_table", "display only"], "main"),
        (["Answer + Why"], "pass"),
    ]
    n2 = len(exec_specs)
    bw2 = (last[2] - left - gap * (n2 - 1)) // n2
    first_cx = left + bw2 // 2
    mid_y = (top_y0 + top_y1) // 2
    poly_arrow(
        d,
        [
            (last[2] + 2, mid_y),
            (rail_x, mid_y),
            (rail_x, 680),
            (first_cx, 680),
            (first_cx, exec_y0 - 2),
        ],
        PASS,
    )
    d.text((rail_x + 14, mid_y - 28), "allowed", font=font(16, True), fill=PASS)

    prev = None
    for i, (lines, kind) in enumerate(exec_specs):
        x = left + i * (bw2 + gap)
        rect = (x, exec_y0, x + bw2, exec_y1)
        box(d, rect, lines, kind)
        if prev:
            cy = (exec_y0 + exec_y1) // 2
            arrow(d, (prev[2] + 3, cy), (rect[0] - 3, cy), PASS)
        prev = rect

    notes = [
        "route_query runs before any model call. It stops selling price, revenue, profit, and worker names.",
        "The three assess gates run in order. A clicked clarification skips assess_ambiguity and is looked up as the chosen reading.",
        "After retrieval, exactly one of draw or render_table copies tool values. It does not recompute.",
        "Action tools return a proposal. Confirm writes a local audit row. Mail is not sent.",
        "FACTORY_TODAY = 2026-04-01. Sundays are excluded. production_log is factory-wide, date × stage.",
    ]
    y = 1000
    for line in notes:
        d.text((48, y), line, font=font(20), fill=MUTED)
        y += 42

    img.save(OUT, "PNG")
    print(OUT)


if __name__ == "__main__":
    main()
