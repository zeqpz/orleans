"""Apply an exact (old -> new) edit to frontend/index.html AND record it in tools/nola/reskin_frontend.py, so the
reskin stays reproducible from a fresh base. Each old string must match exactly once in index.html.
  from edit import ed, css
  ed(old, new)     # an exact replacement
  css(block)       # CSS appended at the end of the voodoo stylesheet block
Writes go through a temp file and an atomic replace, retried, so a locked file can never be left truncated."""
import os, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML = os.path.join(ROOT, "frontend", "index.html")
SCRIPT = os.path.join(ROOT, "tools", "nola", "reskin_frontend.py")
MARK = "# ------------------------------------------------------------------ the voodoo look (appended to the stylesheet)"
CSS_END = "'''\nrep(\"</style>\\n</head>\", CSS + \"</style>\\n</head>\")"
NL = "\n"


def _write(path, text):
    tmp = path + ".tmp"
    for attempt in range(8):
        try:
            with open(tmp, "w", encoding="utf-8", newline=NL) as fh:
                fh.write(text)
            os.replace(tmp, path)
            return
        except OSError:
            time.sleep(.5 + attempt * .5)
    raise SystemExit("could not write " + path)


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def ed(old, new):
    s = _read(HTML)
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"index.html: {n} matches for {old[:80]!r}")
    t = _read(SCRIPT)
    assert t.count(MARK) == 1
    _write(HTML, s.replace(old, new))
    _write(SCRIPT, t.replace(MARK, f"rep({old!r},\n    {new!r})\n\n{MARK}", 1))


def css(block):
    s = _read(HTML)
    assert s.count("</style>\n</head>") == 1
    t = _read(SCRIPT)
    assert t.count(CSS_END) == 1, "CSS block end not found in reskin_frontend.py"
    _write(HTML, s.replace("</style>\n</head>", block + "</style>\n</head>"))
    _write(SCRIPT, t.replace(CSS_END, block + CSS_END))
