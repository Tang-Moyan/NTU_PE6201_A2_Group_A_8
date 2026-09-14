"""
A2_main - PRINTING
=====================================================================
Small, boring helpers so every test script and every report section
looks the same. Nothing here makes a decision.
=====================================================================
"""
import sys

WIDTH = 72

_OK = "  ok  "
_MISSING = " TODO "
_FAIL = " FAIL "


def h1(text):
    print()
    print("=" * WIDTH)
    print("  " + text)
    print("=" * WIDTH)


def h2(text):
    print()
    print("  " + text)
    print("  " + "-" * (WIDTH - 4))


def kv(key, value, width=26):
    print("  %-*s %s" % (width, key, value))


def bullet(text, indent=2):
    print(" " * indent + "- " + str(text))


def _state(marker, text, detail):
    print("[%s] %s%s" % (marker, text, ("  -  " + str(detail)) if detail else ""))


def ok(text, detail=""):
    _state(_OK, text, detail)


def todo(text, detail=""):
    _state(_MISSING, text, detail)


def fail(text, detail=""):
    _state(_FAIL, text, detail)


def table(headers, rows, aligns=None):
    """Fixed-width table. `rows` is a list of tuples of str-ables."""
    rows = [[("" if c is None else str(c)) for c in r] for r in rows]
    headers = [str(h) for h in headers]
    widths = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            if i < len(widths):
                widths[i] = max(widths[i], len(c))
    aligns = aligns or ["<"] * len(headers)

    def line(cells):
        return "  " + "  ".join(
            "%-*s" % (widths[i], c) if aligns[i] == "<"
            else "%*s" % (widths[i], c)
            for i, c in enumerate(cells))

    print(line(headers))
    print("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        print(line(r))


def paragraph(text, indent=2, width=WIDTH):
    """Wrap prose for the report preview, preserving blank lines."""
    import textwrap
    if not isinstance(text, str):
        text = str(text)
    out = []
    for block in text.split("\n\n"):
        block = " ".join(block.split())
        if not block:
            continue
        out.append(textwrap.fill(block, width=width - indent,
                                 initial_indent=" " * indent,
                                 subsequent_indent=" " * indent))
    print("\n\n".join(out))


def word_count(text):
    """Words of PROSE. Tables and figures do not count toward the 2,000."""
    if not isinstance(text, str):
        return 0
    return len(text.split())


def missing_report(missing, title="Still to fill in"):
    """Print the (path, Template) list produced by common.template."""
    if not missing:
        return
    h2(title)
    for path, tpl in missing:
        print("  %-34s %s" % (path, tpl.hint))
        if tpl.example is not None:
            print("  %-34s   e.g. %r" % ("", tpl.example))


def exit_code(problems):
    """0 when there is nothing outstanding, 1 otherwise."""
    return 1 if problems else 0


def die(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)
