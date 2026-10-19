"""Future-direction schematic: daily briefing and weekly briefing."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(
    r"c:\Users\LIUSI\Desktop\NUS\DSS5105\DSS5105_26fall_Group10_TheGeneralManager-sCo-Pilot\evaluation\figures\briefing_direction.png"
)

W, H = 3200, 1240
PAPER = (246, 243, 238)
INK = (28, 25, 23)
BRASS = (140, 106, 61)
MUTED = (92, 86, 78)
CARD = (255, 252, 248)
LINE = (228, 221, 210)
WHITE = (255, 255, 255)
RED = (140, 61, 61)
GREEN = (44, 74, 62)
SOFT = (243, 235, 224)

REG = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
REG_S = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 18)
REG_XS = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
BOLD = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 28)
BOLD_L = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 40)
BOLD_M = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 22)
BOLD_S = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 18)
KICK = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 16)


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text(draw, xy, s, font, fill=INK):
    draw.text(xy, s, font=font, fill=fill)


def paragraph(draw, x, y, s, font, fill, max_w, gap=6):
    lines = wrap(draw, s, font, max_w)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + gap
    return y


def rrect(draw, box, fill, outline=None, width=1, radius=18):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def pill(draw, x, y, label, fg=BRASS, bg=SOFT):
    tw = draw.textlength(label, font=BOLD_S)
    h = 34
    rrect(draw, (x, y, x + tw + 28, y + h), bg, radius=17)
    draw.text((x + 14, y + 5), label, font=BOLD_S, fill=fg)
    return tw + 36


def panel(draw, box, title, kicker):
    rrect(draw, box, CARD, LINE, 2, 28)
    x, y, _, _ = box
    text(draw, (x + 32, y + 22), kicker, KICK, BRASS)
    text(draw, (x + 32, y + 46), title, BOLD_L, INK)


def mini_bars(draw, x, y, w, h, values, color):
    n = len(values)
    gap = 10
    bw = (w - gap * (n - 1)) / n
    top = max(values) or 1
    for i, v in enumerate(values):
        bh = h * (v / top)
        bx = x + i * (bw + gap)
        rrect(draw, (bx, y + h - bh, bx + bw, y + h), color, radius=6)


def main():
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 14, H), fill=BRASS)

    text(d, (56, 36), "FUTURE DIRECTION", KICK, BRASS)
    text(d, (56, 62), "Two briefings. One button.", BOLD_L, INK)
    text(
        d,
        (56, 118),
        "Pops up on the first login. Close with ×. Open again from Briefing.",
        REG,
        MUTED,
    )

    # ----- Daily -----
    dx, dy, dw, dh = 48, 176, 1536, 1020
    panel(d, (dx, dy, dx + dw, dy + dh), "Daily Briefing", "WORKDAYS  ·  NOT MONDAY MORNING")
    cx = dx + 32
    cy = dy + 130
    x = cx
    for lab in ("First login", "Auto popup", "× to close", "Briefing to reopen"):
        x += pill(d, x, cy, lab)
    cy += 56

    col_w = (dw - 64 - 20) // 2
    left = (cx, cy, cx + col_w, dy + dh - 28)
    right = (cx + col_w + 20, cy, dx + dw - 32, dy + dh - 28)
    rrect(d, left, PAPER, LINE, 1, 18)
    rrect(d, right, PAPER, LINE, 1, 18)

    text(d, (left[0] + 22, left[1] + 18), "ORDERS COMPLETED", KICK, BRASS)
    text(d, (left[0] + 22, left[1] + 44), "What finished", BOLD, INK)
    y = paragraph(
        d,
        left[0] + 22,
        left[1] + 88,
        "[Order] ([product] for [customer]) has been completed in time, or overdue for N days.",
        REG_XS,
        MUTED,
        col_w - 48,
        3,
    )
    y += 12
    y = paragraph(
        d,
        left[0] + 22,
        y,
        "ORD-014 (Beanie for Northwind) has been completed in time.",
        REG_S,
        GREEN,
        col_w - 48,
    )
    y += 8
    y = paragraph(
        d,
        left[0] + 22,
        y,
        "ORD-029 (Scarf for Harbor Knits) has been completed overdue for 3 days.",
        REG_S,
        RED,
        col_w - 48,
    )
    y += 18
    text(d, (left[0] + 22, y), "If overdue", BOLD_S, INK)
    y += 32
    y = paragraph(
        d,
        left[0] + 22,
        y,
        "Ask whether the manager needs an update email.",
        REG_S,
        MUTED,
        col_w - 48,
    )
    y += 10
    pill(d, left[0] + 22, y, "Send update email", WHITE, BRASS)

    text(d, (right[0] + 22, right[1] + 18), "ORDERS IN PROGRESS", KICK, BRASS)
    text(d, (right[0] + 22, right[1] + 44), "Likely to miss, before it is late", BOLD, INK)
    # schematic timeline
    tx, ty = right[0] + 28, right[1] + 130
    tw = col_w - 56
    d.line((tx, ty + 18, tx + tw, ty + 18), fill=LINE, width=4)
    dots = [0.08, 0.32, 0.55, 0.78]
    labels = ["ORD-062", "ORD-103", "ORD-108", "ORD-120"]
    for i, (p, lab) in enumerate(zip(dots, labels)):
        cxd = tx + int(tw * p)
        col = RED if i == 2 else BRASS
        d.ellipse((cxd - 9, ty + 9, cxd + 9, ty + 27), fill=col)
        text(d, (cxd - 36, ty + 36), lab, REG_XS, MUTED if i != 2 else RED)
    text(d, (tx, ty + 68), "Click an order to set an alert.", REG_S, MUTED)

    y = ty + 110
    rows = [
        (RED, "TODAY", "Still at the current stage, far from done. Highly likely to be overdue. Draft an apology email."),
        (GREEN, "IN TWO DAYS", "Show it when it can still be finished on time."),
        (BRASS, "IN ONE WEEK", "Seek help from a workshop."),
    ]
    for col, name, body in rows:
        d.ellipse((right[0] + 24, y + 6, right[0] + 36, y + 18), fill=col)
        text(d, (right[0] + 46, y), name, BOLD_S, INK)
        y += 28
        y = paragraph(d, right[0] + 46, y, body, REG_XS, MUTED, col_w - 80, 4)
        y += 10

    y += 6
    rrect(d, (right[0] + 18, y, right[2] - 18, y + 118), SOFT, radius=14)
    text(d, (right[0] + 34, y + 12), "STALL", BOLD_S, INK)
    paragraph(
        d,
        right[0] + 34,
        y + 42,
        "Normally reported on Monday. If a stall sits three standard deviations out, write it in the daily briefing.",
        REG_XS,
        MUTED,
        col_w - 80,
        4,
    )

    # ----- Weekly -----
    wx = dx + dw + 28
    panel(d, (wx, dy, W - 48, dy + dh), "Weekly Briefing", "MONDAY MORNING ONLY")
    cy = dy + 130
    x = wx + 32
    for lab in ("First login", "Auto popup", "× to close", "Briefing to reopen"):
        x += pill(d, x, cy, lab)
    cy += 56
    inner_l, inner_r = wx + 32, W - 80
    inner_w = inner_r - inner_l

    text(d, (inner_l, cy), "LAST WEEK'S SUM-UP", KICK, BRASS)
    cy += 32
    card_w = (inner_w - 28) // 3
    cards = [
        ("Weekly track", "Orders finished, and the overdue share."),
        ("Production log", "Knitting, washing, assembly, packing."),
        ("Products finished", "Product × brand, against pieces done."),
    ]
    bars = [
        [8, 11, 9, 14, 10],
        [12, 7, 15, 9],
        [6, 10, 8, 13, 7],
    ]
    stage_names = [None, ["Knit", "Wash", "Asm", "Pack"], None]
    for i, ((title_, blurb), vals) in enumerate(zip(cards, bars)):
        bx = inner_l + i * (card_w + 14)
        rrect(d, (bx, cy, bx + card_w, cy + 280), PAPER, LINE, 1, 16)
        text(d, (bx + 16, cy + 14), title_, BOLD_S, INK)
        paragraph(d, bx + 16, cy + 44, blurb, REG_XS, MUTED, card_w - 32, 3)
        mini_bars(d, bx + 18, cy + 130, card_w - 36, 100, vals, BRASS if i != 1 else GREEN)
        if stage_names[i]:
            bw = (card_w - 36 - 30) / 4
            for j, name in enumerate(stage_names[i]):
                text(d, (bx + 18 + j * (bw + 10), cy + 238), name, REG_XS, MUTED)
    cy += 296
    text(
        d,
        (inner_l, cy),
        "A week that has not finished yet: how to count it is still open.",
        REG_XS,
        MUTED,
    )
    cy += 36

    text(d, (inner_l, cy), "THIS WEEK'S TO-DO", KICK, BRASS)
    cy += 30
    y = paragraph(
        d,
        inner_l,
        cy,
        "Same in-progress view as the daily briefing: orders likely to miss a due date, with an alert on click.",
        REG_S,
        INK,
        inner_w,
        4,
    )
    y += 14
    rrect(d, (inner_l, y, inner_r, y + 210), SOFT, radius=16)
    text(d, (inner_l + 20, y + 16), "STALLED ORDERS", BOLD_S, INK)
    text(
        d,
        (inner_l + 20, y + 48),
        "Current rule: in progress, and idle for 3 or more working days.",
        REG_S,
        MUTED,
    )
    paragraph(
        d,
        inner_l + 20,
        y + 86,
        "ORD-107 has been stalled in Assembly for 6 days, while the average for this stage is 2 days. Unexpected delay. Pay more attention.",
        REG_S,
        INK,
        inner_w - 48,
        5,
    )

    im.save(OUT, "PNG")
    print(OUT)


if __name__ == "__main__":
    main()
