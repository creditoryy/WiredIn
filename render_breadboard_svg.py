# render_breadboard_svg.py (v2 realistic full-size board)
import json
from pathlib import Path

# Geometry (px)
CELL_W   = 18        # horizontal spacing between holes
CELL_H   = 18        # vertical spacing between holes
MARGIN_X = 48
MARGIN_Y = 36
RAIL_GAP = 8         # gap between + and - rail rows
TRENCH_H = 22        # central gap between A–E and F–J
HOLE_R   = 2.8

# Fine-tuning + rail styling
TOP_RAIL_OFFSET     = -6    # nudge whole top rail block up/down
TOP_RAIL_CLEARANCE  = 12    # extra gap between top rails and row A
BOTTOM_RAIL_OFFSET  = 2     # nudge bottom rail block
RAIL_LINE_WIDTH     = 3
RAIL_BAND_OFFSET    = 8     # distance from rail hole center to each colored line (sandwich holes)
RAIL_HOLE_OFFSET   = 0     # nudge rail holes up/down
RAIL_LINE_OFFSET   = 6     # nudge rail lines up/down

# Rail pair hole spacing (center-to-center distance = CELL_H + *_RAIL_GAP)
TOP_RAIL_GAP     = 0   # try 4–6 to tighten the top rails
BOTTOM_RAIL_GAP  = 0   # keep same as top for symmetry

# Rail hole grouping (top & bottom): 10 groups, each 5 holes wide, with a 1-column gap
RAIL_GROUPS          = 10   
RAIL_GROUP_SIZE      = 5     # holes per group (per rail row)
RAIL_GROUP_GAP_COLS  = 1     # blank "slot" between groups (no hole drawn)

# Column numbers (every N columns), rotated 90°
NUMBER_EVERY     = 5
NUM_FONT_SIZE    = 10
NUM_TOP_OFFSET   = 10   # pixels *below* the TOP blue (−) line
NUM_BOTTOM_OFFSET= 10   # pixels *above* the BOTTOM red (+) line

# Shift the column-number x position by N whole columns (can be negative)
NUMBER_X_OFFSET_COLS = -1   # set to 1 if labels appear one column to the LEFT

# Distance of row letters from the hole field edges
ROW_LABEL_EDGE_OFFSET = 10  # was effectively ~28 before; smaller = closer

# Hole shape (rounded square)
HOLE_W   = 6.0   # width in px
HOLE_H   = 6.0   # height in px
HOLE_RX  = 2.0   # corner radius

# Distance of +/– markers from the hole field edges
MARKER_EDGE_OFFSET = 10  # smaller = closer

ROW_LABELS = ['A','B','C','D','E','F','G','H','I','J']
ROW_INDEX  = {ch:i for i,ch in enumerate(ROW_LABELS)}

def tx_rot(x, y, t, angle=90, size=11, fill="#333"):
    # rotate around (x,y)
    return (
        f'<text x="{x}" y="{y}" font-family="monospace" font-size="{size}" '
        f'fill="{fill}" text-anchor="middle" dominant-baseline="middle" '
        f'transform="rotate({angle} {x} {y})">{t}</text>'
    )

def svg_header(w, h):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'

def tx(x,y,t,size=11,anchor="middle",fill="#333"):
    return f'<text x="{x}" y="{y}" font-family="monospace" font-size="{size}" text-anchor="{anchor}" fill="{fill}">{t}</text>'

def hole(x, y):
    # centered rounded-rect hole
    return (
        f'<rect x="{x - HOLE_W/2}" y="{y - HOLE_H/2}" '
        f'width="{HOLE_W}" height="{HOLE_H}" rx="{HOLE_RX}" ry="{HOLE_RX}" '
        f'fill="#222" />'
    )


def col_to_x(col):
    return MARGIN_X + col*CELL_W

def middle_row_y(row_idx, top_rails=True):
    y0 = MARGIN_Y
    if top_rails:
        y0 += (CELL_H*2 + TOP_RAIL_GAP + TOP_RAIL_CLEARANCE)
    if row_idx <= 4:
        return y0 + row_idx*CELL_H
    return y0 + 5*CELL_H + TRENCH_H + (row_idx-5)*CELL_H


def rails_y_positions(top=True):
    if top:
        gap  = TOP_RAIL_GAP
        base = MARGIN_Y + TOP_RAIL_OFFSET
    else:
        gap  = BOTTOM_RAIL_GAP
        base = board_height - MARGIN_Y - (CELL_H*2 + gap) + BOTTOM_RAIL_OFFSET

    y_plus  = base + CELL_H*0.5                  # '+' rail hole row center
    y_minus = base + CELL_H*1.5 + gap            # '−' rail hole row center
    return y_plus, y_minus

def draw_grouped_rail_holes(columns, y_center, plus_row=True):
    """
    Draws power-rail holes as 10 groups of 5, spaced by 1 "blank column" gap.
    Groups are horizontally centered across the full rail width.

    columns: middle bus columns; we use its total width to center the groups.
    y_center: the y of the hole row center (already includes per-row offsets).
    plus_row: unused here but kept if you later want to vary styling.
    """
    parts = []
    total_group_cols = RAIL_GROUPS * RAIL_GROUP_SIZE + (RAIL_GROUPS - 1) * RAIL_GROUP_GAP_COLS
    total_width_px = columns * CELL_W

    # compute pixel-centered start x for the FIRST hole in the FIRST group
    groups_width_px = total_group_cols * CELL_W
    left_px = MARGIN_X + (total_width_px - groups_width_px) / 2

    # walk groups
    x = left_px
    for g in range(RAIL_GROUPS):
        # draw 5 holes
        for i in range(RAIL_GROUP_SIZE):
            parts.append(hole(x + (i+1) * CELL_W, y_center))  # (i+1) to keep offset similar to column grid feel
        # gap to next group (skip holes)
        if g < RAIL_GROUPS - 1:
            x += (RAIL_GROUP_SIZE + RAIL_GROUP_GAP_COLS) * CELL_W
    return "\n".join(parts)

def draw_rails(columns, top=True):
    y_plus, y_minus = rails_y_positions(top)
    width = columns * CELL_W
    x1 = MARGIN_X - 18
    x2 = MARGIN_X - 18 + width + 36

    parts = []

    # ONE line per rail:
    # '+' rail line placed ABOVE the + hole row
    parts.append(
        f'<line x1="{x1}" y1="{y_plus - RAIL_LINE_OFFSET}" '
        f'x2="{x2}" y2="{y_plus - RAIL_LINE_OFFSET}" '
        f'stroke="#e34444" stroke-width="{RAIL_LINE_WIDTH}"/>'
    )
    # '−' rail line placed BELOW the − hole row
    parts.append(
        f'<line x1="{x1}" y1="{y_minus + RAIL_LINE_OFFSET}" '
        f'x2="{x2}" y2="{y_minus + RAIL_LINE_OFFSET}" '
        f'stroke="#2a6de0" stroke-width="{RAIL_LINE_WIDTH}"/>'
    )

    # +/- markers (left & right) closer to the field
    x_left_mark  = MARGIN_X - MARKER_EDGE_OFFSET
    x_right_mark = MARGIN_X + columns*CELL_W + MARKER_EDGE_OFFSET

    parts.append(tx(x_left_mark,  y_plus+4,  "+", 14, "middle", "#e34444"))
    parts.append(tx(x_left_mark,  y_minus+4, "–", 14, "middle", "#2a6de0"))
    parts.append(tx(x_right_mark, y_plus+4,  "+", 14, "middle", "#e34444"))
    parts.append(tx(x_right_mark, y_minus+4, "–", 14, "middle", "#2a6de0"))



    # Rail holes in 5×2 groups (centered across the rail width)
    parts.append(
        draw_grouped_rail_holes(columns, y_plus  + RAIL_HOLE_OFFSET, plus_row=True)
    )
    parts.append(
        draw_grouped_rail_holes(columns, y_minus + RAIL_HOLE_OFFSET, plus_row=False)
    )



    return "\n".join(parts)

def draw_row_labels(columns, left=True, right=True):
    parts = []
    x_left  = MARGIN_X - ROW_LABEL_EDGE_OFFSET
    x_right = MARGIN_X + columns*CELL_W + ROW_LABEL_EDGE_OFFSET

    # A–E
    for i, ch in enumerate(ROW_LABELS[:5]):
        y = middle_row_y(i, top_rails=True)
        if left:  parts.append(tx_rot(x_left,  y, ch, 90))
        if right: parts.append(tx_rot(x_right, y, ch, 90))
    # F–J
    for i, ch in enumerate(ROW_LABELS[5:], start=5):
        y = middle_row_y(i, top_rails=True)
        if left:  parts.append(tx_rot(x_left,  y, ch, 90))
        if right: parts.append(tx_rot(x_right, y, ch, 90))
    return "\n".join(parts)


def draw_column_numbers(columns):
    """
    Rotated numbers at the rails:
      - Top: just BELOW the top blue (−) rail line
      - Bottom: just ABOVE the bottom red (+) rail line
      - Labels DECREASE left→right (e.g., 60,55,50,...,5 for 63 columns)
    """
    parts = []
    y_top_plus,  y_top_minus  = rails_y_positions(top=True)
    y_bot_plus,  y_bot_minus  = rails_y_positions(top=False)

    y_top_blue_line   = y_top_minus + RAIL_LINE_OFFSET
    y_bottom_red_line = y_bot_plus  - RAIL_LINE_OFFSET

    y_top_labels    = y_top_blue_line   + NUM_TOP_OFFSET
    y_bottom_labels = y_bottom_red_line - NUM_BOTTOM_OFFSET

    # rightmost multiple of NUMBER_EVERY not exceeding 'columns'
    start = (columns // NUMBER_EVERY) * NUMBER_EVERY  # e.g., 63 -> 60

    # Walk positions left→right (5,10,15,...) but values go 60,55,50,...
    count = start // NUMBER_EVERY
    for i in range(count):                # i = 0..(count-1)
        col   = (i + 1) * NUMBER_EVERY   # 5,10,15,...
        label = start - i * NUMBER_EVERY # 60,55,50,...
        x = col_to_x(col + NUMBER_X_OFFSET_COLS)
        parts.append(tx_rot(x, y_top_labels,    str(label), 90, size=NUM_FONT_SIZE))
        parts.append(tx_rot(x, y_bottom_labels, str(label), 90, size=NUM_FONT_SIZE))
    return "\n".join(parts)

def draw_middle(columns):
    parts = []

    # A..E rows (holes only)
    for i in range(5):  # rows 0..4
        y = middle_row_y(i, top_rails=True)
        for c in range(1, columns+1):
            parts.append(hole(col_to_x(c), y))

    # central trench
    y_top = middle_row_y(4, top_rails=True) + CELL_H/2
    parts.append(f'<rect x="{MARGIN_X-24}" y="{y_top}" width="{columns*CELL_W+48}" height="{TRENCH_H}" fill="#f0f2f5" rx="6"/>')

    # F..J rows (holes only)
    for i in range(5, 10):  # rows 5..9
        y = middle_row_y(i, top_rails=True)
        for c in range(1, columns+1):
            parts.append(hole(col_to_x(c), y))

    # subtle group tick marks every 5 columns (optional)
    for c in range(5, columns+1, 5):
        x = col_to_x(c)
        parts.append(f'<line x1="{x}" y1="{MARGIN_Y-4}" x2="{x}" y2="{MARGIN_Y+2}" stroke="#bbb" stroke-width="1"/>')

    return "\n".join(parts)


def pad_to_coords(pad: str):
    """
    Pads like 'A5', 'E5', 'F12', 'J63'
    -> (x,y) pixel center
    """
    pad = pad.strip().upper()
    row = pad[0]; col = int(pad[1:])
    x = col_to_x(col)
    y = middle_row_y(ROW_INDEX[row], top_rails=True)
    return x, y

def draw_resistor(p1, p2, label=""):
    (x1,y1) = pad_to_coords(p1)
    (x2,y2) = pad_to_coords(p2)
    line = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#9c642b" stroke-width="3" />'
    midx, midy = (x1+x2)/2, (y1+y2)/2 - 10
    txt = tx(midx, midy, label or "R", 11)
    return line + txt

def render_board(columns, rail_top=True, rail_bottom=True):
    global board_height
    height = MARGIN_Y
    if rail_top:
        height += (CELL_H*2 + RAIL_GAP)
    height += 10*CELL_H + TRENCH_H
    if rail_bottom:
        height += (CELL_H*2 + RAIL_GAP)
    height += MARGIN_Y
    width = MARGIN_X + columns*CELL_W + MARGIN_X
    board_height = height

    parts = [svg_header(width, height)]
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fbfbfb"/>')

    if rail_top:
        parts.append(draw_rails(columns, top=True))
    # ↓ numbers right after top rails
    parts.append(draw_column_numbers(columns))
    # ↓ holes and trench
    parts.append(draw_middle(columns))
    # ↓ rotated A–J on both sides (draw once)
    parts.append(draw_row_labels(columns, left=True, right=True))
    if rail_bottom:
        parts.append(draw_rails(columns, top=False))

    return width, height, "\n".join(parts) + "</svg>"


def main():
    cfg = json.loads(Path("breadboard_layout.json").read_text(encoding="utf-8"))
    columns     = int(cfg["board"]["columns"])
    rail_top    = bool(cfg["board"].get("rail_top", True))
    rail_bottom = bool(cfg["board"].get("rail_bottom", True))

    width, height, svg = render_board(columns, rail_top, rail_bottom)

    comp_svg = []
    for comp in cfg.get("components", []):
        typ = comp["type"].lower()
        if typ == "resistor":
            comp_svg.append(draw_resistor(comp["pins"][0], comp["pins"][1], comp.get("value","")))

    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Breadboard Preview</title>
<style>
  body {{ background:#eef1f5; margin:0; font-family:ui-sans-serif,system-ui; }}
  .wrap {{ max-width:{width}px; margin:24px auto; padding:12px; }}
  .card {{ background:#fff; border-radius:12px; box-shadow:0 8px 28px rgba(0,0,0,.08); padding:16px; }}
  pre {{ background:#f7f7f7; border-radius:8px; padding:12px; overflow:auto; }}
</style></head>
<body>
  <div class="wrap">
    <div class="card">
      <h2 style="margin:0 0 12px 0">Breadboard Preview (63 columns)</h2>
      {svg}
      {"".join(comp_svg)}
      <h3>Layout JSON</h3>
      <pre>{json.dumps(cfg, indent=2)}</pre>
    </div>
  </div>
</body></html>"""
    Path("breadboard_preview.html").write_text(html, encoding="utf-8")
    print("Wrote breadboard_preview.html — open it to view the realistic board.")

if __name__ == "__main__":
    main()
