"""Clean copies of three current results: same form, without Tools or Why."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(
    r"c:\Users\LIUSI\Desktop\NUS\DSS5105\DSS5105_26fall_Group10_TheGeneralManager-sCo-Pilot\evaluation\figures"
)

INK = (18, 32, 43)
PAPER = (244, 239, 230)
WHITE = (255, 255, 255)
MUTED = (93, 102, 95)
LINE = (210, 204, 194)
HEADER = (236, 232, 226)
TEAL = (22, 125, 120)
GRID = (217, 221, 216)
ORANGE = (224, 112, 58)
AMBER = (214, 154, 50)

REG = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 22)
REG_S = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
REG_XS = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 16)
BOLD = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 22)
BOLD_S = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 18)
BOLD_XS = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 16)


def rrect(draw, box, fill, outline=None, width=1, radius=12):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def tokens(parts):
    out = []
    for text, font, fill in parts:
        words = text.split(" ")
        for i, word in enumerate(words):
            if i:
                out.append((" ", font, fill))
            out.append((word, font, fill))
    return out


def rich(draw, x, y, parts, max_w, gap=7):
    line, width = [], 0
    lines = []
    for tok in tokens(parts):
        tw = draw.textlength(tok[0], font=tok[1])
        if width + tw > max_w and line and tok[0] != " ":
            lines.append(line)
            line, width = [], 0
        if tok[0] == " " and not line:
            continue
        line.append(tok)
        width += tw
    if line:
        lines.append(line)
    for line in lines:
        cx = x
        height = max(tok[1].size for tok in line)
        for word, font, fill in line:
            draw.text((cx, y), word, font=font, fill=fill)
            cx += draw.textlength(word, font=font)
        y += height + gap
    return y


def user_bubble(draw, right, y, text, max_w):
    words = text.split(" ")
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=REG) <= max_w - 36:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    tw = max(draw.textlength(line, font=REG) for line in lines)
    h = 18 + len(lines) * (REG.size + 6)
    box = (right - tw - 36, y, right, y + h)
    rrect(draw, box, INK, radius=14)
    ty = y + 10
    for line in lines:
        draw.text((box[0] + 18, ty), line, font=REG, fill=PAPER)
        ty += REG.size + 6
    return y + h


def crop(im, pad=36):
    bg = im.getpixel((0, 0))
    w, h = im.size
    last = 0
    for y in range(h):
        if any(im.getpixel((x, y)) != bg for x in range(0, w, 6)):
            last = y
    return im.crop((0, 0, w, min(h, last + pad)))


def card_clarify():
    W, H = 1680, 900
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    y = 28
    y = user_bubble(
        d,
        W - 28,
        y,
        "How should we resequence production to minimize orders delivered late over the next 7 days?",
        980,
    )
    y += 28
    x = 28
    d.text((x, y), "Which of these did you mean?", font=BOLD, fill=INK)
    y += 44
    options = [
        "I'll identify the orders most likely to miss their due dates in the next seven days so production can be resequenced around them.",
        "I'll provide today's production priorities in first-, second-, and third-priority groups with estimated days remaining.",
    ]
    for option in options:
        top = y
        bottom = rich(d, x + 16, y + 14, [(option, REG, INK)], W - 88, 6) + 8
        rrect(d, (x, top, W - 28, bottom), WHITE, LINE, 1, 8)
        rich(d, x + 16, top + 14, [(option, REG, INK)], W - 88, 6)
        y = bottom + 12
    field_top = y
    rrect(d, (x, field_top, W - 140, field_top + 44), WHITE, LINE, 1, 8)
    d.text((x + 14, field_top + 10), "Other", font=REG_S, fill=(160, 154, 146))
    rrect(d, (W - 128, field_top, W - 28, field_top + 44), INK, radius=8)
    label = "Send"
    lw = d.textlength(label, font=BOLD_S)
    d.text((W - 128 + (100 - lw) / 2, field_top + 10), label, font=BOLD_S, fill=PAPER)
    return crop(im)


def card_resequence():
    W, H = 1880, 1500
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    y = 28
    y = user_bubble(
        d,
        W - 28,
        y,
        "I'll identify orders likely to miss their due dates in the next 7 days so production can be resequenced around them.",
        1100,
    )
    y += 28
    x = 28
    max_w = W - 56
    y = rich(
        d,
        x,
        y,
        [("3 orders are likely to miss their due dates in the next 7 days: ORD-108, ORD-103, and ORD-062.", BOLD, INK)],
        max_w,
    )
    y += 10
    d.ellipse((x, y + 6, x + 14, y + 20), fill=ORANGE)
    y = rich(d, x + 24, y, [("ORD-108 & ORD-103 — High risk", BOLD, INK)], max_w - 24)
    y += 2
    y = rich(
        d,
        x + 24,
        y,
        [
            ("2,000 Scarves", REG, INK),
            (" | Harbor Knits | ", REG, MUTED),
            ("Due in 3 days", BOLD, INK),
        ],
        max_w - 24,
    )
    y = rich(
        d,
        x + 24,
        y,
        [
            ("2,000 Scarves", REG, INK),
            (" | Bright Basics | ", REG, MUTED),
            ("Due in 4 days", BOLD, INK),
        ],
        max_w - 24,
    )
    y += 4
    y = rich(
        d,
        x + 24,
        y,
        [
            ("Both are in ", REG, INK),
            ("Assembly", BOLD, INK),
            (", with ", REG, INK),
            ("Washing", BOLD, INK),
            (" and ", REG, INK),
            ("Packing", BOLD, INK),
            (" also remaining. Each needs an estimated ", REG, INK),
            ("8.4 working days", BOLD, INK),
            (", compared with only ", REG, INK),
            ("3", BOLD, INK),
            (" and ", REG, INK),
            ("4 working days", BOLD, INK),
            (" available.", REG, INK),
        ],
        max_w - 24,
    )
    y += 12
    d.ellipse((x, y + 6, x + 14, y + 20), fill=AMBER)
    y = rich(d, x + 24, y, [("ORD-062 — At risk", BOLD, INK)], max_w - 24)
    y += 2
    y = rich(
        d,
        x + 24,
        y,
        [
            ("2,000 Scarves", REG, INK),
            (" | Bright Basics | ", REG, MUTED),
            ("Due in 8 days", BOLD, INK),
        ],
        max_w - 24,
    )
    y += 4
    y = rich(
        d,
        x + 24,
        y,
        [
            ("It is still in ", REG, INK),
            ("Knitting", BOLD, INK),
            (", so all four production stages remain. Estimated work is ", REG, INK),
            ("10.6 working days", BOLD, INK),
            (", versus ", REG, INK),
            ("7 working days", BOLD, INK),
            (" available.", REG, INK),
        ],
        max_w - 24,
    )
    y += 12
    y = rich(
        d,
        x,
        y,
        [
            ("Resequencing focus: ", BOLD, INK),
            ("prioritize ORD-108, then ORD-103, while protecting capacity for ORD-062. Bright Basics has two 2,000-piece scarf orders moving through similar production stages, increasing pressure on the same workflow.", REG, INK),
        ],
        max_w,
    )
    y += 16
    d.line((x, y, W - 28, y), fill=LINE, width=1)
    y += 16
    d.text((x, y), "Orders likely to miss due dates in the next 7 days", font=BOLD_XS, fill=INK)
    y += 32
    headers = [
        "Order",
        "Customer",
        "Product",
        "Pieces",
        "Due date",
        "Current stage",
        "Remaining stages",
        "Working days to due",
    ]
    rows = [
        ["ORD-108", "Harbor Knits", "Scarf", "2000", "2026-04-03", "ASSEMBLY", "ASSEMBLY, WASHING, PACKING", "3"],
        ["ORD-103", "Bright Basics", "Scarf", "2000", "2026-04-04", "ASSEMBLY", "ASSEMBLY, WASHING, PACKING", "4"],
        ["ORD-062", "Bright Basics", "Scarf", "2000", "2026-04-08", "KNITTING", "KNITTING, ASSEMBLY, WASHING, PACKING", "7"],
    ]
    widths = [130, 170, 110, 100, 150, 170, 430, 210]
    table_w = sum(widths)
    left = x
    rrect(d, (left, y, left + table_w, y + 36 + 42 * 3), WHITE, LINE, 1, 8)
    d.rectangle((left, y, left + table_w, y + 36), fill=HEADER)
    cx = left
    for header, width in zip(headers, widths):
        d.text((cx + 12, y + 8), header, font=BOLD_XS, fill=MUTED)
        cx += width
    for r, row in enumerate(rows):
        ry = y + 36 + r * 42
        d.line((left, ry, left + table_w, ry), fill=LINE, width=1)
        cx = left
        for cell, width in zip(row, widths):
            d.text((cx + 12, ry + 10), cell, font=REG_XS, fill=INK)
            cx += width
    return crop(im)


def card_feasibility():
    W, H = 1680, 1400
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    y = 28
    y = user_bubble(
        d,
        W - 28,
        y,
        "Is it feasible to accept a new order for 2,000 scarves due on May 15, 2026?",
        980,
    )
    y += 28
    x = 28
    max_w = W - 56
    y = rich(
        d,
        x,
        y,
        [
            ("Under the current capacity heuristic, accepting ", REG, INK),
            ("2,000 scarves by May 15, 2026", BOLD, INK),
            (" is feasible only with workshops (", REG, INK),
            ("FEASIBLE_WITH_WORKSHOPS", BOLD, INK),
            (").", REG, INK),
        ],
        max_w,
    )
    y += 8
    y = rich(
        d,
        x,
        y,
        [
            ("The request was evaluated as ", REG, INK),
            ("ACCESSORIES", BOLD, INK),
            (". The model counts ", REG, INK),
            ("39 working days", BOLD, INK),
            (" and identifies ", REG, INK),
            ("PACKING", BOLD, INK),
            (" as the bottleneck, with median throughput of ", REG, INK),
            ("672 pieces per working day", BOLD, INK),
            (". Existing ", REG, INK),
            ("IN_PROGRESS", BOLD, INK),
            (" orders account for ", REG, INK),
            ("32,850 pieces", BOLD, INK),
            (", leaving estimated spare factory capacity at ", REG, INK),
            ("0", BOLD, INK),
            (". Eligible ", REG, INK),
            ("ACTIVE", BOLD, INK),
            (" workshops provide an estimated ", REG, INK),
            ("12,831.05 pieces", BOLD, INK),
            (" of overflow capacity, enough to cover the order.", REG, INK),
        ],
        max_w,
    )
    y += 8
    y = rich(
        d,
        x,
        y,
        [(
            "This is a planning estimate, not a delivery guarantee. It treats every IN_PROGRESS order's full quantity as competing demand because remaining quantities are unknown, uses the bottleneck median from the last 30 working days, does not model four-stage pipeline latency, assumes at most one new batch per workshop, and excludes SUSPENDED workshops.",
            REG,
            INK,
        )],
        max_w,
    )
    y += 18
    d.line((x, y, W - 28, y), fill=LINE, width=1)
    y += 16
    d.text((x, y), "Capacity estimate for 2,000 scarves by May 15, 2026", font=BOLD_S, fill=INK)
    y += 36
    plot_l, plot_r = x + 90, W - 48
    plot_t, plot_b = y, y + 340
    ymax = 14000
    for tick in (0, 3500, 7000, 10500, 14000):
        ty = plot_b - (tick / ymax) * (plot_b - plot_t)
        d.line((plot_l, ty, plot_r, ty), fill=GRID, width=1)
        label = f"{tick:,}" if tick else "0"
        d.text((x, ty - 10), label, font=REG_XS, fill=MUTED)
    values = [
        ("Requested order", 2000),
        ("Spare factory capacity", 0),
        ("Active workshop overflow", 12831),
    ]
    span = plot_r - plot_l
    slot = span / 3
    bar_w = 150
    for i, (name, value) in enumerate(values):
        bh = (value / ymax) * (plot_b - plot_t)
        cx = plot_l + slot * i + slot / 2
        if bh > 0:
            d.rectangle((cx - bar_w / 2, plot_b - bh, cx + bar_w / 2, plot_b), fill=TEAL)
        d.line((plot_l, plot_b, plot_r, plot_b), fill=GRID, width=1)
        label_w = d.textlength(name, font=REG_XS)
        if label_w > slot - 16:
            words = name.split(" ")
            mid = len(words) // 2
            for j, part in enumerate((" ".join(words[:mid]), " ".join(words[mid:]))):
                pw = d.textlength(part, font=REG_XS)
                d.text((cx - pw / 2, plot_b + 10 + j * 20), part, font=REG_XS, fill=MUTED)
        else:
            d.text((cx - label_w / 2, plot_b + 12), name, font=REG_XS, fill=MUTED)
    return crop(im, pad=56)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "result_clarify.png": card_clarify(),
        "result_resequence.png": card_resequence(),
        "result_feasibility.png": card_feasibility(),
    }
    for name, image in files.items():
        path = OUT / name
        image.save(path, "PNG")
        print(path)


if __name__ == "__main__":
    main()
