import html
import re
from html.parser import HTMLParser
from urllib.parse import urlparse


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


class RemoteProblemError(RuntimeError):
    pass


class HtmlNode:
    def __init__(self, tag="", attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []

    @property
    def classes(self):
        return set(self.attrs.get("class", "").split())

    def find_first(self, *, tag=None, class_name=None):
        if (tag is None or self.tag == tag) and (
                class_name is None or class_name in self.classes):
            return self
        for child in self.children:
            if isinstance(child, HtmlNode):
                result = child.find_first(tag=tag, class_name=class_name)
                if result is not None:
                    return result
        return None

    def find_all(self, *, tag=None, class_name=None):
        results = []
        if (tag is None or self.tag == tag) and (
                class_name is None or class_name in self.classes):
            results.append(self)
        for child in self.children:
            if isinstance(child, HtmlNode):
                results.extend(child.find_all(tag=tag, class_name=class_name))
        return results


class HtmlTreeParser(HTMLParser):
    void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                 "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = HtmlNode(tag.lower(), attrs)
        self.stack[-1].children.append(node)
        if node.tag not in self.void_tags:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(HtmlNode(tag.lower(), attrs))

    def handle_endtag(self, tag):
        tag = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


ALLOWED_RICH_TEXT_TAGS = {
    "p", "br", "pre", "code", "strong", "b", "em", "i", "u", "s",
    "ul", "ol", "li", "blockquote", "sub", "sup", "span", "div",
    "table", "thead", "tbody", "tr", "th", "td", "hr", "h1", "h2",
    "h3", "h4", "h5", "h6",
}


def parse_html_tree(content):
    parser = HtmlTreeParser()
    parser.feed(content)
    return parser.root


def node_text(node):
    parts = []

    def visit(item):
        if isinstance(item, str):
            parts.append(item)
            return
        if item.tag == "br":
            parts.append("\n")
            return
        for child in item.children:
            visit(child)

    visit(node)
    text = "".join(parts).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def render_rich_text(node, excluded_classes=None):
    excluded_classes = set(excluded_classes or [])

    def render(item):
        if isinstance(item, str):
            return html.escape(item)
        if item.tag in {"script", "style", "iframe", "object"}:
            return ""
        if item.classes & excluded_classes:
            return ""
        if item.tag == "img":
            return html.escape(item.attrs.get("alt", ""))
        body = "".join(render(child) for child in item.children)
        if item.tag not in ALLOWED_RICH_TEXT_TAGS:
            return body
        if item.tag in {"br", "hr"}:
            return f"<{item.tag}>"
        return f"<{item.tag}>{body}</{item.tag}>"

    return "".join(render(child) for child in node.children).strip()


def safe_external_url(value):
    parsed = urlparse(value.strip())
    return value.strip() if parsed.scheme in {"http", "https"} else ""


def _render_markdown_inline(value):
    escaped = html.escape(value)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", escaped)
    return escaped


def markdown_to_html(value):
    lines = str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output = []
    paragraph = []
    list_tag = None
    code_lines = None

    def close_paragraph():
        if paragraph:
            output.append("<p>" + "<br>".join(_render_markdown_inline(line) for line in paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_tag
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = None

    for line in lines:
        if code_lines is not None:
            if line.strip().startswith("```"):
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = None
            else:
                code_lines.append(line)
            continue
        if line.strip().startswith("```"):
            close_paragraph()
            close_list()
            code_lines = []
            continue
        if not line.strip():
            close_paragraph()
            close_list()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            close_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{_render_markdown_inline(heading.group(2))}</h{level}>")
            continue
        unordered = re.match(r"^\s*[-+*]\s+(.+)$", line)
        ordered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if unordered or ordered:
            close_paragraph()
            target = "ul" if unordered else "ol"
            if list_tag != target:
                close_list()
                output.append(f"<{target}>")
                list_tag = target
            output.append(f"<li>{_render_markdown_inline((unordered or ordered).group(1))}</li>")
            continue
        quote = re.match(r"^\s*>\s?(.*)$", line)
        if quote:
            close_paragraph()
            close_list()
            output.append(f"<blockquote>{_render_markdown_inline(quote.group(1))}</blockquote>")
            continue
        if re.fullmatch(r"\s*([-*_])(?:\s*\1){2,}\s*", line):
            close_paragraph()
            close_list()
            output.append("<hr>")
            continue
        close_list()
        paragraph.append(line)

    if code_lines is not None:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    close_paragraph()
    close_list()
    return "".join(output).strip()
