#!/usr/bin/env python3
"""validate.py — validate (and canonically reorder) an Ideogram 4 JSON caption.

Checks the caption against the official schema (ideogram-oss/ideogram4
docs/prompting.md + CaptionVerifier semantics). On success prints the MINIFIED
caption to stdout (ready to paste into CLIPTextEncode / pipe to generate.py).
Errors and warnings go to stderr.

Why this matters: Ideogram 4 renders many schema mistakes as the same gray
"Image blocked by safety filter" card it uses for NSFW — a malformed caption
often LOOKS like a censored one. Validate first.

Usage:
    validate.py caption.json          # validate file
    validate.py -                     # validate stdin
    validate.py --fix caption.json    # also canonically reorder keys
"""

import json
import re
import sys

HEX_RE = re.compile(r"^#[0-9A-F]{6}$")

STYLE_ORDER_PHOTO = ["aesthetics", "lighting", "photo", "medium", "color_palette"]
STYLE_ORDER_ART = ["aesthetics", "lighting", "medium", "art_style", "color_palette"]
ELEM_ORDER = {
    "obj": ["type", "bbox", "desc", "color_palette"],
    "text": ["type", "bbox", "text", "desc", "color_palette"],
}
TOP_ORDER = ["high_level_description", "style_description", "compositional_deconstruction"]

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def check_order(actual_keys, canonical, where):
    expected = [k for k in canonical if k in actual_keys]
    got = [k for k in actual_keys if k in canonical]
    if got != expected:
        warn(f"{where}: key order {got} should be {expected} (model was trained on canonical order)")
    unknown = [k for k in actual_keys if k not in canonical]
    if unknown:
        warn(f"{where}: unknown keys {unknown}")


def check_palette(p, limit, where):
    if not isinstance(p, list):
        err(f"{where}: color_palette must be a list of hex strings")
        return
    if len(p) > limit:
        err(f"{where}: color_palette has {len(p)} entries (max {limit})")
    for c in p:
        if not isinstance(c, str) or not HEX_RE.match(c):
            err(f"{where}: bad hex {c!r} (must be uppercase #RRGGBB)")


def check_bbox(b, where):
    if not (isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)):
        err(f"{where}: bbox must be [y_min, x_min, y_max, x_max] (4 numbers)")
        return
    y1, x1, y2, x2 = b
    for v in b:
        if not (0 <= v <= 1000):
            err(f"{where}: bbox value {v} outside 0-1000 normalized range")
    if y1 >= y2:
        err(f"{where}: bbox y_min ({y1}) must be < y_max ({y2}) — order is [y_min, x_min, y_max, x_max], origin top-left")
    if x1 >= x2:
        err(f"{where}: bbox x_min ({x1}) must be < x_max ({x2})")


def reorder(d, canonical):
    out = {k: d[k] for k in canonical if k in d}
    for k in d:
        if k not in out:
            out[k] = d[k]
    return out


def main():
    args = sys.argv[1:]
    fix = "--fix" in args
    args = [a for a in args if a != "--fix"]
    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    raw = sys.stdin.read() if args[0] == "-" else open(args[0], encoding="utf-8").read()

    try:
        cap = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(cap, dict):
        print("ERROR: caption must be a JSON object", file=sys.stderr)
        sys.exit(1)

    # ---- top level ----
    check_order(list(cap.keys()), TOP_ORDER, "top-level")
    hld = cap.get("high_level_description")
    if hld is None:
        warn("missing high_level_description (optional but strongly recommended)")
    elif not isinstance(hld, str):
        err("high_level_description must be a string")
    elif len(hld.split()) > 60:
        warn(f"high_level_description is {len(hld.split())} words — keep it to 1-2 sentences (~50 words); granular detail belongs in elements/background")

    # ---- style_description ----
    sd = cap.get("style_description")
    if sd is not None:
        if not isinstance(sd, dict):
            err("style_description must be an object")
        else:
            has_photo, has_art = "photo" in sd, "art_style" in sd
            if has_photo and has_art:
                err("style_description: use photo OR art_style, never both")
            if not has_photo and not has_art:
                err("style_description: must contain exactly one of photo / art_style")
            for req in ("aesthetics", "lighting", "medium"):
                if req not in sd:
                    err(f"style_description: missing required key {req!r}")
            order = STYLE_ORDER_PHOTO if has_photo else STYLE_ORDER_ART
            check_order(list(sd.keys()), order, "style_description")
            if "color_palette" in sd:
                check_palette(sd["color_palette"], 16, "style_description")
            if has_photo and sd.get("medium") not in (None, "photograph"):
                warn(f"style_description: photo variant usually pairs with medium 'photograph' (got {sd.get('medium')!r})")
            if fix:
                cap["style_description"] = reorder(sd, order)

    # ---- compositional_deconstruction ----
    cd = cap.get("compositional_deconstruction")
    if cd is None:
        err("missing compositional_deconstruction (REQUIRED)")
    elif not isinstance(cd, dict):
        err("compositional_deconstruction must be an object")
    else:
        check_order(list(cd.keys()), ["background", "elements"], "compositional_deconstruction")
        if not isinstance(cd.get("background"), str) or not cd.get("background", "").strip():
            err("compositional_deconstruction.background is required (non-empty string)")
        els = cd.get("elements")
        if not isinstance(els, list):
            err("compositional_deconstruction.elements is required (list)")
            els = []
        if fix:
            cap["compositional_deconstruction"] = reorder(cd, ["background", "elements"])
        for i, el in enumerate(els):
            where = f"elements[{i}]"
            if not isinstance(el, dict):
                err(f"{where}: must be an object")
                continue
            t = el.get("type")
            if t not in ELEM_ORDER:
                err(f"{where}: type must be 'obj' or 'text' (got {t!r})")
                continue
            if t == "text" and not isinstance(el.get("text"), str):
                err(f"{where}: text elements require a 'text' string (the literal characters to render)")
            if not isinstance(el.get("desc"), str) or not el.get("desc", "").strip():
                err(f"{where}: 'desc' is required (non-empty string)")
            if "bbox" in el:
                check_bbox(el["bbox"], where)
            if "color_palette" in el:
                check_palette(el["color_palette"], 5, where)
            check_order(list(el.keys()), ELEM_ORDER[t], where)
            if fix:
                els[i] = reorder(el, ELEM_ORDER[t])
        if len(els) == 0:
            warn("elements is empty — fine for pure-background images, otherwise add subjects")

    if fix:
        for k in list(cap.keys()):
            pass
        capr = reorder(cap, TOP_ORDER)
        cap.clear()
        cap.update(capr)

    minified = json.dumps(cap, separators=(",", ":"), ensure_ascii=False)
    # ~3.5 chars/token for mixed JSON; model hard cap is 2048 tokens
    est_tokens = len(minified) / 3.5
    if est_tokens > 2048:
        err(f"caption ≈{est_tokens:.0f} tokens — exceeds the 2048-token cap; trim descs/elements")
    elif est_tokens > 1800:
        warn(f"caption ≈{est_tokens:.0f} tokens — close to the 2048 cap")
    if "\\u" in minified and not any(ord(c) > 127 for c in raw):
        warn("caption contains \\uXXXX escapes — serialize with ensure_ascii=False, keep non-ASCII literal")

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s) — fix errors before generating "
              f"(schema errors often render as fake 'safety blocked' cards).", file=sys.stderr)
        sys.exit(1)
    print(f"OK — {len(warnings)} warning(s), ≈{est_tokens:.0f} tokens", file=sys.stderr)
    print(minified)


if __name__ == "__main__":
    main()
