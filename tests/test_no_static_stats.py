"""Fail if a statistic is typed into code or templates instead of coming from data."""
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_DIRS = ("collect", "web")
TEMPLATES = ROOT / "web" / "templates"
STATISTIC = (
    re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s?%"),   # 49%, 12.5 %
    re.compile(r"\b\d{1,3}(?:,\d{3})+\b"),         # 228,789
)
REFERENCE_BLOCK = re.compile(r"{%-?\s*call\s+reference\(.*?{%-?\s*endcall\s*-?%}", re.S)
JINJA_COMMENT = re.compile(r"{#.*?#}", re.S)
STRING_TOKENS = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)}


def find_statistics(text: str) -> list[str]:
    return [m.group(0) for pattern in STATISTIC for m in pattern.finditer(text)]


def python_strings(path: Path):
    with path.open("rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type in STRING_TOKENS:
                yield tok.start[0], tok.string


def test_detector_catches_examples():
    assert find_statistics('"49%"') == ["49%"]
    assert find_statistics("BGP 228,789 prefixes") == ["228,789"]
    assert find_statistics("12.5 % of sites") == ["12.5 %"]
    assert find_statistics("{:.1f}% %Y-%m-%d rgba(0,0,0,0) /32 2001:db8::") == []


def test_python_has_no_hardcoded_statistics():
    offenders = []
    for directory in PY_DIRS:
        for path in sorted((ROOT / directory).rglob("*.py")):
            for line, text in python_strings(path):
                offenders += [f"{path.relative_to(ROOT)}:{line}: {hit!r}" for hit in find_statistics(text)]
    assert offenders == []


def test_templates_have_no_hardcoded_statistics():
    offenders = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = JINJA_COMMENT.sub("", REFERENCE_BLOCK.sub("", path.read_text()))
        offenders += [f"{path.relative_to(ROOT)}: {hit!r}" for hit in find_statistics(text)]
    assert offenders == []


def test_collectors_have_no_fallback_data():
    offenders = []
    for path in sorted((ROOT / "collect").rglob("*.py")):
        offenders += [f"{path.relative_to(ROOT)}:{line}" for line, text in python_strings(path)
                      if "fallback" in text.lower()]
    assert offenders == []
