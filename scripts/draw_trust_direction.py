"""Future-direction schematic: a short result, then the reasoning that produced it."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(
    r"c:\Users\LIUSI\Desktop\NUS\DSS5105\DSS5105_26fall_Group10_TheGeneralManager-sCo-Pilot\evaluation\figures\trust_direction.png"
)

W, H = 3200, 1080
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


def main():
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 14, H), fill=BRASS)

    text(d, (56, 36), "FUTURE DIRECTION", KICK, BRASS)
    text(d, (56, 62), "Show the result, and why.", BOLD_L, INK)
    text(d, (56, 118), "Written out, one paragraph at a time. It sits on the data and the tools.", REG, MUTED)

    dy, dh = 176, 860
    gap = 28
    left_w = 1080
    lx = 48
    rx = lx + left_w + gap
    right_w = W - 48 - rx

    panel(d, (lx, dy, lx + left_w, dy + dh), "The result", "A FEW LINES")
    panel(d, (rx, dy, rx + right_w, dy + dh), "The why", "THE PATH TO THAT RESULT")

    # ----- Result -----
    cx, cy = lx + 32, dy + 130
    inner_w = left_w - 64
    rrect(d, (cx, cy, cx + inner_w, cy + 72), SOFT, radius=16)
    text(d, (cx + 22, cy + 12), "QUESTION", KICK, BRASS)
    text(d, (cx + 22, cy + 36), "How is the TrendCart order doing?", BOLD_M, INK)
    cy += 92

    rrect(d, (cx, cy, cx + inner_w, cy + 250), PAPER, LINE, 1, 16)
    text(d, (cx + 22, cy + 18), "ANSWER", KICK, BRASS)
    y = paragraph(
        d,
        cx + 22,
        cy + 52,
        "ORD-108 (Hoodie for TrendCart) is still in Assembly.",
        REG,
        INK,
        inner_w - 44,
    )
    y += 8
    y = paragraph(
        d,
        cx + 22,
        y,
        "Due 3 April. Days needed are longer than the days left.",
        REG,
        INK,
        inner_w - 44,
    )
    y += 8
    paragraph(
        d,
        cx + 22,
        y,
        "Likely to miss the due date.",
        REG,
        RED,
        inner_w - 44,
    )
    cy += 286
    paragraph(
        d,
        cx,
        cy,
        "The short result. The paragraphs on the right are how we arrived at it. Example only.",
        REG_S,
        MUTED,
        inner_w,
        5,
    )

    steps = [
        (
            "Start from the question",
            "The question is about one customer, TrendCart. Before any judgement, we resolve that to a single order: ORD-108, a hoodie that is still in progress. We do not answer from the previous reply.",
        ),
        (
            "Read what the data says",
            "The orders row is the starting fact. ORD-108 is in Assembly, and it is due on 3 April. Those two facts come from the row itself. Nothing has been inferred yet.",
        ),
        (
            "Let the tool make the comparison",
            "The risk check then asks whether the work still ahead fits before that date. Days needed are the longer of two readings: how long the remaining stages take at their recent pace, and at least one day for every stage still left. Python makes that comparison. The writing only reports it.",
        ),
        (
            "State why the conclusion follows",
            "Assembly, washing, and packing are still ahead, and the days they need run past 3 April. That is why the result says this order is likely to miss its due date.",
        ),
    ]
    cy = dy + 128
    box_l = rx + 32
    box_r = rx + right_w - 32
    box_w = box_r - box_l
    card_h = 158
    card_gap = 16
    spine_x = box_l + 28
    d.line(
        (spine_x, cy + 36, spine_x, cy + len(steps) * (card_h + card_gap) - card_gap - 118),
        fill=LINE,
        width=3,
    )
    for i, (title, body) in enumerate(steps):
        top = cy + i * (card_h + card_gap)
        rrect(d, (box_l, top, box_r, top + card_h), SOFT if i == 3 else PAPER, LINE, 1, 16)
        d.ellipse((spine_x - 14, top + 20, spine_x + 14, top + 48), fill=RED if i == 3 else BRASS)
        num = str(i + 1)
        nw = d.textlength(num, font=KICK)
        text(d, (spine_x - nw / 2, top + 24), num, KICK, WHITE)
        text(d, (box_l + 58, top + 22), title, BOLD_M, INK)
        paragraph(d, box_l + 58, top + 62, body, REG_S, INK if i == 3 else MUTED, box_w - 86, 5)

    im.save(OUT, "PNG")
    print(OUT)


if __name__ == "__main__":
    main()
