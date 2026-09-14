"""
A2_main - THE CODE INVENTORY
=====================================================================
Finds every place in this tree that still needs code written, so the
answer to "what is left to build" is a command rather than a memory.

    python A2_main/code_todo.py

TWO KINDS OF OUTSTANDING WORK, and they are deliberately different
mechanisms:

    TEMPLATE(...)   a DECISION or a piece of PROSE. Lives in an
                    answers_Dx.py, found by common.template, reported
                    by test_Dx.py.

    TODO(D3/gate)   CODE. Lives in the implementation, found here.

The marker syntax is

    # TODO(D<n>/<topic>): what has to be written, and why it matters

and it is deliberately grep-friendly, so it works from an editor too:

    grep -rn "TODO(D" A2_main

WHY A CONVENTION RATHER THAN A CHECKLIST FILE. A checklist in a
separate document drifts the moment someone writes the code and
forgets to tick it. A marker lives on the line it describes and
disappears when that line is written.
=====================================================================
"""
import os
import re

MARKER = re.compile(r"TODO\((D\d)\s*/\s*([\w-]+)\)\s*:?\s*(.*)")

SKIP_DIRS = {"__pycache__", "output", ".git"}
SKIP_FILES = {"codemap.py"}


def scan(root):
    """[(deliverable, topic, path, line_no, text)] across the tree."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if not name.endswith(".py") or name in SKIP_FILES:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            try:
                lines = open(path, encoding="utf-8").read().splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                m = MARKER.search(line)
                if not m:
                    continue
                deliverable, topic, text = m.groups()
                found.append((deliverable, topic, rel, i,
                              _continuation(text, lines, i)))
    found.sort(key=lambda r: (r[0], r[2], r[3]))
    return found


def _is_rule(text):
    """A separator line - '# -----' or a box-drawing rule. Not prose."""
    stripped = text.strip()
    return bool(stripped) and not any(ch.isalnum() for ch in stripped)


def _continuation(first, lines, index):
    """Join the wrapped lines that belong to a marker.

    A marker's explanation runs to three or four lines and only the
    first carries the TODO(...), so without this the inventory prints
    half a sentence and is useless as a work list.

    Markers appear in two places and they wrap differently:

        # TODO(D3/gate): ...        continuation lines start with '#'
        #   more of the sentence

        TODO(D2/toolset): ...       inside a docstring - no '#' at all,
          more of the sentence      just indentation

    So the mode is decided by the marker's own line, and both stop at a
    blank line, at a separator rule, or at the next marker. Getting the
    stop condition wrong is how an unrelated comment block ends up
    glued onto the end of a work item.
    """
    in_comment = lines[index - 1].lstrip().startswith("#")
    parts = [first.strip()]
    for line in lines[index:]:
        stripped = line.strip()
        if not stripped:
            break
        if in_comment:
            if not stripped.startswith("#"):
                break
            body = stripped.lstrip("#").strip()
        else:
            if stripped.startswith(('"""', "'''")):
                break
            body = stripped
        if not body or _is_rule(body) or MARKER.search(body):
            break
        parts.append(body)
    return " ".join(parts)


def by_deliverable(root):
    """{deliverable: [(topic, path, line, text), ...]}"""
    out = {}
    for deliverable, topic, path, line, text in scan(root):
        out.setdefault(deliverable, []).append((topic, path, line, text))
    return out
