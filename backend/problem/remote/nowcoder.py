import html
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from .common import DEFAULT_USER_AGENT, RemoteProblemError


NOWCODER_BASE_URL = "https://www.nowcoder.com"
NOWCODER_ACM_BASE_URL = "https://ac.nowcoder.com"
NOWCODER_UUID_PATTERN = re.compile(r"^[A-Za-z0-9]{32}$")
NOWCODER_ACM_ID_PATTERN = re.compile(r"^(?:NC)?(\d+)$", re.I)
NOWCODER_LANGUAGE_MAP = {
    "c": {"name": "C", "id": "1"},
    "cpp": {"name": "C++", "id": "2"},
    "java": {"name": "Java", "id": "4"},
    "python3": {"name": "Python3", "id": "11"},
    "go": {"name": "Golang", "id": "17"},
    "javascript": {"name": "JavaScript", "id": "13"},
    "js": {"name": "JavaScript", "id": "13"},
}


class NowcoderProblemError(RemoteProblemError):
    pass


_NOWCODER_MATH_PATTERNS = (
    re.compile(r"\$\$.*?\$\$|\$[^$]+\$|\\\(.*?\\\)|\\\[.*?\\\]", re.S),
    re.compile(r"\\displaystyle.+$", re.S),
    re.compile(r"\b[A-Za-z](?:\s*,\s*[A-Za-z])?\\left.*?\\right", re.S),
    re.compile(r"\b[A-Za-z](?:_[A-Za-z0-9]+)?\s*(?:=|\\in)\s*\\\{.*?\\\}", re.S),
    re.compile(r"\b[A-Za-z](?:_[A-Za-z0-9]+)?\s*\\equiv\s*.*?\\pmod\{.*?\}", re.S),
    re.compile(r"\\equiv\^\{\\texttt\{\[[^\]]+\]\}\}"),
)


def _normalize_nowcoder_math_text(value):
    text = re.sub(r"\\hspace\{[^}]+\}", " ", str(value or ""))
    text = re.sub(r"\\bullet(?:\\,)?\s*", "• ", text)
    math_parts = []

    def protect(match):
        token = f"NOWCODERMATHPLACEHOLDER{len(math_parts)}X"
        expression = match.group(0).strip()
        if expression.startswith(("$", r"\(", r"\[")):
            math_parts.append(expression)
        else:
            math_parts.append(r"\(" + expression + r"\)")
        return token

    for pattern in _NOWCODER_MATH_PATTERNS:
        text = pattern.sub(protect, text)
    for index, expression in enumerate(math_parts):
        text = text.replace(f"NOWCODERMATHPLACEHOLDER{index}X", expression)
    return text


class _SafeRichTextParser(HTMLParser):
    allowed_tags = {
        "p", "br", "pre", "code", "strong", "b", "em", "i",
        "ul", "ol", "li", "blockquote", "sub", "sup"
    }
    void_tags = {"br"}
    blocked_tags = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.open_tags = []
        self.blocked_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.blocked_tags:
            self.blocked_depth += 1
            return
        if self.blocked_depth:
            return
        if tag == "img":
            alt = next((value for name, value in attrs if name.lower() == "alt"), "")
            if alt:
                self.parts.append(html.escape(alt))
            return
        if tag in self.allowed_tags:
            self.parts.append(f"<{tag}>")
            if tag not in self.void_tags:
                self.open_tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.blocked_tags and self.blocked_depth:
            self.blocked_depth -= 1
            return
        if self.blocked_depth:
            return
        if tag in self.open_tags:
            while self.open_tags:
                current = self.open_tags.pop()
                self.parts.append(f"</{current}>")
                if current == tag:
                    break

    def handle_data(self, data):
        if not self.blocked_depth:
            self.parts.append(html.escape(_normalize_nowcoder_math_text(data)))

    def result(self):
        while self.open_tags:
            self.parts.append(f"</{self.open_tags.pop()}>")
        return "".join(self.parts).strip()


class _PlainTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.blocked_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.blocked_depth += 1
        elif self.blocked_depth:
            return
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "img":
            alt = next((value for name, value in attrs if name.lower() == "alt"), "")
            if alt:
                self.parts.append(alt)

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style"} and self.blocked_depth:
            self.blocked_depth -= 1

    def handle_data(self, data):
        if not self.blocked_depth:
            self.parts.append(data)

    def result(self):
        text = "".join(self.parts).replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in text.split("\n")]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)


def parse_nowcoder_reference(reference):
    value = str(reference or "").strip()
    if "://" in value:
        parsed = urlparse(value)
        if parsed.hostname not in {"nowcoder.com", "www.nowcoder.com", "ac.nowcoder.com"}:
            raise NowcoderProblemError("Only nowcoder.com problem URLs are supported")
        acm_match = re.search(r"/acm/problem/(?:NC)?(\d+)(?:/|$)", parsed.path, re.I)
        terminal_match = re.search(r"/questionTerminal/([A-Za-z0-9]{32})(?:/|$)", parsed.path)
        if acm_match:
            return f"NC{acm_match.group(1)}"
        value = terminal_match.group(1) if terminal_match else ""
    acm_match = NOWCODER_ACM_ID_PATTERN.fullmatch(value)
    if acm_match:
        return f"NC{acm_match.group(1)}"
    if not NOWCODER_UUID_PATTERN.fullmatch(value):
        raise NowcoderProblemError(
            "Nowcoder problem ID must look like NC322024, an ACM problem URL, or a questionTerminal UUID"
        )
    return value


def _extract(pattern, content, field_name, required=True):
    match = re.search(pattern, content, re.S | re.I)
    if match:
        return match.group(1).strip()
    if required:
        raise NowcoderProblemError(f"Unable to parse Nowcoder {field_name}")
    return ""


def _safe_rich_text(fragment):
    parser = _SafeRichTextParser()
    parser.feed(fragment)
    return parser.result()


def _plain_text(fragment):
    parser = _PlainTextParser()
    parser.feed(fragment)
    return parser.result()


def _parse_time_limit(content):
    match = re.search(r"时间限制：[^<\n]*?([0-9.]+)\s*(毫秒|秒)", content)
    if not match:
        return 1000
    value = float(match.group(1))
    return max(1, round(value if match.group(2) == "毫秒" else value * 1000))


def _parse_memory_limit(content):
    match = re.search(r"空间限制：[^<\n]*?([0-9.]+)\s*([KMG])", content, re.I)
    if not match:
        return 256
    value = float(match.group(1))
    unit = match.group(2).upper()
    if unit == "K":
        value /= 1024
    elif unit == "G":
        value *= 1024
    return max(1, round(value))


def parse_nowcoder_problem_page(content, expected_uuid):
    problem_block = _extract(r"window\.problem\s*=\s*\{(.*?)\};", content, "problem metadata")
    numeric_id = _extract(r"\bid\s*:\s*(\d+)", problem_block, "numeric question ID")
    page_uuid = _extract(r"\buuid\s*:\s*['\"]([A-Za-z0-9]{32})['\"]", problem_block, "UUID")
    problem_type = int(_extract(r"\btype\s*:\s*(\d+)", problem_block, "problem type"))
    if page_uuid.lower() != expected_uuid.lower():
        raise NowcoderProblemError("Nowcoder page UUID does not match the requested problem")
    if problem_type != 4:
        raise NowcoderProblemError("Only public programming questions are supported")

    title_html = _extract(
        r'<h1[^>]*class="[^"]*js-question-title[^"]*"[^>]*>(.*?)</h1>',
        content,
        "title",
    )
    description_html = _extract(
        r'<div\s+class="nc-post-content"[^>]*>(.*?)</div>',
        content,
        "description",
    )
    input_html = _extract(
        r'<h5>\s*<b>\s*输入描述\s*:?\s*</b>\s*</h5>\s*<pre>(.*?)</pre>',
        content,
        "input description",
    )
    output_html = _extract(
        r'<h5>\s*<b>\s*输出描述\s*:?\s*</b>\s*</h5>\s*<pre>(.*?)</pre>',
        content,
        "output description",
    )

    sample_pattern = re.compile(
        r'<div\s+class="question-oi-hd"[^>]*>.*?</div>.*?'
        r'<h2>\s*输入\s*</h2>\s*<div\s+class="question-oi-cont"[^>]*>\s*<pre>(.*?)</pre>.*?'
        r'<h2>\s*输出\s*</h2>\s*<div\s+class="question-oi-cont"[^>]*>\s*<pre>(.*?)</pre>',
        re.S | re.I,
    )
    samples = [
        {"input": _plain_text(sample_input), "output": _plain_text(sample_output)}
        for sample_input, sample_output in sample_pattern.findall(content)
    ]

    support_lang = _extract(
        r"window\.supportLang\s*=\s*['\"]([^'\"]*)['\"]",
        content,
        "supported languages",
        required=False,
    )
    language_ids = {}
    languages = []
    for item in (part.strip().lower() for part in support_lang.split(",")):
        mapped = NOWCODER_LANGUAGE_MAP.get(item)
        if mapped and mapped["name"] not in languages:
            languages.append(mapped["name"])
            language_ids[mapped["name"]] = mapped["id"]
    if not languages:
        raise NowcoderProblemError("No supported local language was found for this Nowcoder problem")

    return {
        "kind": "question_terminal",
        "remote_id": page_uuid,
        "uuid": page_uuid,
        "question_id": numeric_id,
        "title": _plain_text(title_html),
        "description": _safe_rich_text(description_html),
        "input_description": _safe_rich_text(input_html),
        "output_description": _safe_rich_text(output_html),
        "samples": samples,
        "time_limit": _parse_time_limit(content),
        "memory_limit": _parse_memory_limit(content),
        "languages": languages,
        "language_ids": language_ids,
        "support_lang": support_lang,
        "problem_type": problem_type,
        "code_judge_type": _extract(
            r"window\.codeJudgeType\s*=\s*['\"]([^'\"]+)['\"]",
            content,
            "judge type",
            required=False,
        ),
    }


def parse_nowcoder_acm_problem_page(content, expected_problem_id):
    page_info = _extract(r"window\.pageInfo\s*=\s*\{(.*?)\};", content, "ACM problem metadata")
    page_problem_id = _extract(r"\bproblemId\s*:\s*['\"](\d+)['\"]", page_info, "ACM problem ID")
    question_id = _extract(r"\bquestionId\s*:\s*['\"](\d+)['\"]", page_info, "numeric question ID")
    problem_uuid = _extract(
        r"\buuid\s*:\s*['\"]([A-Za-z0-9]{32})['\"]",
        page_info,
        "UUID",
        required=False,
    )
    if page_problem_id != str(expected_problem_id):
        raise NowcoderProblemError("Nowcoder ACM page problem ID does not match the request")

    title_html = _extract(
        r'<div[^>]*class="[^"]*question-title[^"]*"[^>]*>(.*?)</div>',
        content,
        "title",
    )
    description_html = _extract(
        r'<div[^>]*class="[^"]*subject-question[^"]*"[^>]*>(.*?)</div>',
        content,
        "description",
    )
    input_html = _extract(
        r'<h2[^>]*>\s*输入描述\s*:?[\s\S]*?</h2>\s*<pre>(.*?)</pre>',
        content,
        "input description",
    )
    output_html = _extract(
        r'<h2[^>]*>\s*输出描述\s*:?[\s\S]*?</h2>\s*<pre>(.*?)</pre>',
        content,
        "output description",
    )

    sample_pattern = re.compile(
        r'<textarea[^>]*data-clipboard-text-id="input\d+"[^>]*>(.*?)</textarea>.*?'
        r'<textarea[^>]*data-clipboard-text-id="output\d+"[^>]*>(.*?)</textarea>',
        re.S | re.I,
    )
    samples = [
        {"input": _plain_text(sample_input), "output": _plain_text(sample_output)}
        for sample_input, sample_output in sample_pattern.findall(content)
    ]
    if not samples:
        raise NowcoderProblemError("No Nowcoder ACM samples were found")

    support_lang = _extract(
        r"window\.supportLang\s*=\s*['\"]([^'\"]*)['\"]",
        content,
        "supported languages",
        required=False,
    )
    language_ids = {}
    languages = []
    for item in (part.strip().lower() for part in support_lang.split(",")):
        mapped = NOWCODER_LANGUAGE_MAP.get(item)
        if mapped and mapped["name"] not in languages:
            languages.append(mapped["name"])
            language_ids[mapped["name"]] = mapped["id"]
    if not languages:
        raise NowcoderProblemError("No supported local language was found for this Nowcoder ACM problem")

    return {
        "kind": "acm",
        "remote_id": f"NC{page_problem_id}",
        "problem_id": page_problem_id,
        "question_id": question_id,
        "uuid": problem_uuid,
        "title": _plain_text(title_html),
        "description": _safe_rich_text(description_html),
        "input_description": _safe_rich_text(input_html),
        "output_description": _safe_rich_text(output_html),
        "samples": samples,
        "time_limit": _parse_time_limit(content),
        "memory_limit": _parse_memory_limit(content),
        "languages": languages,
        "language_ids": language_ids,
        "support_lang": support_lang,
        "problem_type": 4,
        "code_judge_type": _extract(
            r"window\.codeJudgeType\s*=\s*['\"]([^'\"]+)['\"]",
            content,
            "judge type",
            required=False,
        ),
        "tag_id": _extract(r"\btagId\s*:\s*['\"](\d+)['\"]", page_info, "tag ID", required=False),
    }


def fetch_nowcoder_problem(reference, timeout=20):
    problem_reference = parse_nowcoder_reference(reference)
    is_acm_problem = problem_reference.upper().startswith("NC")
    if is_acm_problem:
        problem_id = problem_reference[2:]
        url = f"{NOWCODER_ACM_BASE_URL}/acm/problem/{problem_id}"
    else:
        problem_id = problem_reference
        url = f"{NOWCODER_BASE_URL}/questionTerminal/{problem_reference}"
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise NowcoderProblemError(f"Unable to fetch Nowcoder problem: {exc}") from exc
    if response.status_code != 200:
        raise NowcoderProblemError(f"Nowcoder returned HTTP {response.status_code}")
    if is_acm_problem:
        data = parse_nowcoder_acm_problem_page(response.text, problem_id)
    else:
        data = parse_nowcoder_problem_page(response.text, problem_reference)
    data["url"] = url
    return data
