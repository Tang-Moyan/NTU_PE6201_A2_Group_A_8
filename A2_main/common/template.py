"""
A2_main - THE TEMPLATE SENTINEL
=====================================================================
Every slot the team still has to fill in is a TEMPLATE object.

    RUNG = TEMPLATE("Which rung, 1-7?", example=7)

WHY AN OBJECT AND NOT None OR "TODO":

  - It is FALSY, so `if not answers.RUNG:` reads naturally.
  - It carries its own hint, so the test scripts can tell you what is
    missing WITHOUT a separate checklist that drifts out of date.
  - It prints as «TODO: ...», so a half-finished report is still
    readable and shows exactly where the holes are.
  - It refuses to be used as a number. A missing figure that silently
    became 0 would produce a confident, wrong cost model - which is
    the one failure this whole assignment is arranged around noticing.

FILL ONE IN by replacing the whole call:

    RUNG = TEMPLATE("Which rung, 1-7?", example=7)     # before
    RUNG = 7                                           # after

Never leave a TEMPLATE wrapped around your answer.
=====================================================================
"""


class Template:
    """A slot the team has not filled in yet."""

    __slots__ = ("hint", "example", "owner", "where")

    def __init__(self, hint, example=None, owner=None, where=None):
        self.hint = hint
        self.example = example
        self.owner = owner        # which deliverable/person this belongs to
        self.where = where        # a file or section it feeds

    # -- falsy, printable, and never silently numeric -----------------
    def __bool__(self):
        return False

    def __repr__(self):
        return "TEMPLATE(%r)" % (self.hint,)

    def __str__(self):
        return "\u00abTODO: %s\u00bb" % (self.hint,)

    def __format__(self, spec):
        return str(self)

    def __len__(self):
        return 0

    def __iter__(self):
        return iter(())

    def _refuse(self, *_a, **_k):
        raise TypeError(
            "This value is still a TEMPLATE and cannot be used in a "
            "calculation: %s\n"
            "Fill it in, or guard the call site with is_filled()." % self.hint)

    __add__ = __radd__ = __sub__ = __rsub__ = _refuse
    __mul__ = __rmul__ = __truediv__ = __rtruediv__ = _refuse
    __float__ = __int__ = __index__ = _refuse


def TEMPLATE(hint, example=None, owner=None, where=None):
    """Mark a slot the team must fill in. See the module docstring."""
    return Template(hint, example=example, owner=owner, where=where)


def is_template(value):
    return isinstance(value, Template)


def is_filled(value):
    """True when `value` contains no TEMPLATE anywhere inside it.

    Recurses, so a list of five statements where one is still a TEMPLATE
    counts as unfilled - which is the honest answer.
    """
    return not list(walk(value))


def walk(value, path=""):
    """Yield (dotted_path, Template) for every unfilled slot inside `value`."""
    if is_template(value):
        yield path or "<value>", value
        return
    if isinstance(value, dict):
        for k, v in value.items():
            yield from walk(v, "%s[%r]" % (path, k) if path else repr(k))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            yield from walk(v, "%s[%d]" % (path, i))


def audit_module(module):
    """Every unfilled slot in a module's public UPPERCASE names.

    Returns [(name_path, Template), ...] in declaration order where the
    interpreter preserves it.
    """
    out = []
    for name in vars(module):
        if name.startswith("_") or not name[0].isupper():
            continue
        for path, tpl in walk(getattr(module, name), name):
            out.append((path, tpl))
    return out


def completeness(module):
    """(filled_count, total_count, [(path, Template), ...]) for a module.

    `total` counts top-level UPPERCASE names, not leaves - it is the
    number a team reads as "how many answers does this deliverable want".
    """
    names = [n for n in vars(module)
             if not n.startswith("_") and n[0].isupper()]
    missing = audit_module(module)
    missing_names = {p.split("[")[0] for p, _ in missing}
    return len(names) - len(missing_names), len(names), missing
