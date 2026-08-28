import json
import re
from functools import lru_cache
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from .common import DEFAULT_USER_AGENT, RemoteProblemError, markdown_to_html


LUOGU_BASE_URL = "https://www.luogu.com.cn"
LUOGU_LANGUAGE_PREFERENCES = {
    "C": ("C",),
    "C++": ("CPP17", "CPP20", "Cpp14Gcc9"),
    "Java": ("Java21", "Java8"),
    "Python3": ("Python3", "PyPy3"),
    "Golang": ("Go",),
    "JavaScript": ("Node",),
}
LUOGU_LANGUAGE_FALLBACK = {
    "C": "2",
    "C++": "12",
    "Java": "33",
    "Python3": "7",
    "Golang": "14",
    "JavaScript": "9",
}


class LuoguProblemError(RemoteProblemError):
    pass


class _LentilleContextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script" and dict(attrs).get("id") == "lentille-context":
            self.capture = True

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.capture:
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def result(self):
        return "".join(self.parts).strip()


def parse_luogu_reference(reference):
    value = str(reference or "").strip()
    if "://" in value:
        parsed = urlparse(value)
        if parsed.hostname not in {"luogu.com.cn", "www.luogu.com.cn"}:
            raise LuoguProblemError("Only luogu.com.cn problem URLs are supported")
        match = re.search(r"/problem/([A-Za-z][A-Za-z0-9_-]*)/?$", parsed.path)
        value = match.group(1) if match else ""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise LuoguProblemError("Luogu problem ID must look like P1001 or a problem URL")
    return value.upper()


def parse_luogu_problem_page(content, expected_problem_id):
    parser = _LentilleContextParser()
    parser.feed(content)
    raw_context = parser.result()
    if not raw_context:
        raise LuoguProblemError("Unable to find Luogu problem data")
    try:
        context = json.loads(raw_context)
    except json.JSONDecodeError as exc:
        raise LuoguProblemError("Unable to decode Luogu problem data") from exc
    problem = (context.get("data") or {}).get("problem") or {}
    problem_id = str(problem.get("pid") or "").upper()
    if problem_id != expected_problem_id:
        raise LuoguProblemError("Luogu page problem ID does not match the request")

    statement = problem.get("contenu") or problem.get("content") or {}
    description_parts = [statement.get("background") or "", statement.get("description") or ""]
    samples = []
    for sample in problem.get("samples") or []:
        if isinstance(sample, (list, tuple)) and len(sample) >= 2:
            samples.append({"input": str(sample[0]), "output": str(sample[1])})

    limits = problem.get("limits") or {}
    time_limits = [value for value in limits.get("time") or [] if isinstance(value, (int, float))]
    memory_limits = [value for value in limits.get("memory") or [] if isinstance(value, (int, float))]
    if not time_limits or not memory_limits:
        raise LuoguProblemError("Unable to parse Luogu time or memory limits")
    return {
        "problem_id": problem_id,
        "title": str(problem.get("name") or statement.get("name") or problem_id),
        "description": markdown_to_html("\n\n".join(part for part in description_parts if part)),
        "input_description": markdown_to_html(statement.get("formatI") or ""),
        "output_description": markdown_to_html(statement.get("formatO") or ""),
        "hint": markdown_to_html(statement.get("hint") or ""),
        "samples": samples,
        "time_limit": max(1, round(max(time_limits))),
        "memory_limit": max(1, round(max(memory_limits) / 1024)),
        "accepted_language_ids": [str(value) for value in problem.get("acceptLanguages") or []],
        "difficulty_value": problem.get("difficulty"),
        "problem_type": problem.get("type"),
    }


@lru_cache(maxsize=1)
def _fetch_language_config():
    try:
        response = requests.get(
            f"{LUOGU_BASE_URL}/_lfe/config",
            headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        config = response.json().get("codeLanguages") or {}
    except (requests.RequestException, ValueError):
        return {}
    return {str(key): value for key, value in config.items() if isinstance(value, dict)}


def _map_languages(accepted_language_ids):
    accepted = set(accepted_language_ids)
    config = _fetch_language_config()
    by_type = {
        str(item.get("type")): language_id
        for language_id, item in config.items()
        if not item.get("disabled")
    }
    language_ids = {}
    for local_name, preferences in LUOGU_LANGUAGE_PREFERENCES.items():
        language_id = next(
            (by_type[item] for item in preferences if by_type.get(item) in accepted),
            None,
        )
        if language_id is None:
            fallback = LUOGU_LANGUAGE_FALLBACK[local_name]
            language_id = fallback if fallback in accepted else None
        if language_id is not None:
            language_ids[local_name] = language_id
    if not language_ids:
        raise LuoguProblemError("No supported local language was found for this Luogu problem")
    return language_ids


def fetch_luogu_problem(reference, timeout=30):
    problem_id = parse_luogu_reference(reference)
    url = f"{LUOGU_BASE_URL}/problem/{problem_id}"
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
        raise LuoguProblemError(f"Unable to fetch Luogu problem: {exc}") from exc
    if response.status_code != 200:
        raise LuoguProblemError(f"Luogu returned HTTP {response.status_code}")
    data = parse_luogu_problem_page(response.text, problem_id)
    language_ids = _map_languages(data["accepted_language_ids"])
    data.update({
        "remote_id": problem_id,
        "url": url,
        "languages": list(language_ids),
        "language_ids": language_ids,
    })
    return data
