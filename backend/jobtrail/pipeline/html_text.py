"""Turn an email body into (visible_text, hidden_text).
Hidden elements (display:none, visibility:hidden, font-size:0, white text, the `hidden` attribute)
are dropped from the visible text, so rules only see what a human would see. The hidden text is
returned separately so the injection detector can inspect it."""
from __future__ import annotations

import re
from html.parser import HTMLParser

from ..sources.base import Body

VOID = {"br", "img", "hr", "meta", "link", "input", "area", "base", "col", "embed", "source", "track", "wbr"}
BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section"}
SKIP_CONTENT = {"script", "style", "head", "title"}

_HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?:px|pt|em|%)?\s*(?:;|$)|opacity\s*:\s*0(?:\.0+)?\s*(?:;|$)"
    r"|(?<![-\w])color\s*:\s*(?:#fff(?:fff)?|white|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))"
    r"|position\s*:\s*absolute[^\"]*left\s*:\s*-\d{3,}",
    re.I,
)


def is_hidden(attrs: list[tuple[str, str | None]]) -> bool:
    d = {k.lower(): (v or "") for k, v in attrs}
    if "hidden" in d or d.get("aria-hidden") == "true":
        return True
    return bool(_HIDDEN_STYLE.search(d.get("style", "")))


class _Splitter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []  # (tag, hidden)
        self.visible: list[str] = []
        self.hidden: list[str] = []
        self.skip_depth = 0

    def _hidden_now(self) -> bool:
        return any(h for _, h in self.stack)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in SKIP_CONTENT:
            self.skip_depth += 1
            return
        if tag in BLOCK:
            (self.hidden if self._hidden_now() else self.visible).append("\n")
        if tag not in VOID:
            self.stack.append((tag, is_hidden(attrs)))

    def handle_startendtag(self, tag, attrs):
        if tag.lower() in BLOCK:
            (self.hidden if self._hidden_now() else self.visible).append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in SKIP_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                hidden = self._hidden_now()
                del self.stack[i:]
                if tag in BLOCK:
                    (self.hidden if hidden else self.visible).append("\n")
                break

    def handle_data(self, data):
        if self.skip_depth:
            return
        (self.hidden if self._hidden_now() else self.visible).append(data)


def _clean(parts: list[str]) -> str:
    text = "".join(parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def split_text(body: Body) -> tuple[str, str]:
    """Return (visible_text, hidden_text)."""
    if body.html:
        p = _Splitter()
        p.feed(body.html)
        p.close()
        return _clean(p.visible), _clean(p.hidden)
    return (body.text or "").strip(), ""


def raw_text(body: Body) -> str:
    """Everything, hidden parts included (what a naive integration would feed a model)."""
    if body.html:
        return re.sub(r"<[^>]+>", " ", body.html)
    return body.text or ""
