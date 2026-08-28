import re
from urllib.parse import urlparse

import requests

from .common import (DEFAULT_USER_AGENT, RemoteProblemError, node_text,
                     parse_html_tree, render_rich_text)


CODEFORCES_BASE_URL = "https://codeforces.com"
CODEFORCES_LANGUAGE_IDS = {
    # This is the language used by the verified standalone submission probe.
    "C++": "54",
}


class CodeforcesProblemError(RemoteProblemError):
    pass


def parse_codeforces_reference(reference):
    value = str(reference or "").strip()
    if "://" in value:
        parsed = urlparse(value)
        if parsed.hostname not in {"codeforces.com", "www.codeforces.com"}:
            raise CodeforcesProblemError("Only codeforces.com problem URLs are supported")
        match = re.search(
            r"/(?:problemset/problem|contest)/(\d+)/(?:problem/)?([A-Za-z][A-Za-z0-9]*)/?$",
            parsed.path,
        )
    else:
        match = re.fullmatch(r"(\d+)[\s\-_/]*([A-Za-z][A-Za-z0-9]*)", value)
    if not match:
        raise CodeforcesProblemError("Codeforces problem ID must look like 4A or a problem URL")
    contest_id = int(match.group(1))
    index = match.group(2).upper()
    return contest_id, index


def _parse_time_limit(value):
    match = re.search(r"([0-9.]+)\s*(milliseconds?|seconds?)", value, re.I)
    if not match:
        raise CodeforcesProblemError("Unable to parse Codeforces time limit")
    number = float(match.group(1))
    return max(1, round(number if match.group(2).lower().startswith("millisecond") else number * 1000))


def _parse_memory_limit(value):
    match = re.search(r"([0-9.]+)\s*(kilobytes?|megabytes?)", value, re.I)
    if not match:
        raise CodeforcesProblemError("Unable to parse Codeforces memory limit")
    number = float(match.group(1))
    if match.group(2).lower().startswith("kilobyte"):
        number /= 1024
    return max(1, round(number))


def _render_section(node):
    return render_rich_text(node, excluded_classes={"section-title"})


def parse_codeforces_problem_page(content, expected_contest_id, expected_index):
    root = parse_html_tree(content)
    statement = root.find_first(class_name="problem-statement")
    if statement is None:
        raise CodeforcesProblemError("Unable to find the Codeforces problem statement")
    header = statement.find_first(class_name="header")
    title_node = header.find_first(class_name="title") if header else None
    time_node = header.find_first(class_name="time-limit") if header else None
    memory_node = header.find_first(class_name="memory-limit") if header else None
    if not title_node or not time_node or not memory_node:
        raise CodeforcesProblemError("Unable to parse the Codeforces problem header")

    title = node_text(title_node)
    title = re.sub(rf"^{re.escape(expected_index)}\.\s*", "", title, flags=re.I).strip()
    input_node = statement.find_first(class_name="input-specification")
    output_node = statement.find_first(class_name="output-specification")
    sample_root = statement.find_first(class_name="sample-tests")
    if not input_node or not output_node or not sample_root:
        raise CodeforcesProblemError("Unable to parse Codeforces input, output, or samples")

    description_nodes = []
    header_seen = False
    for child in statement.children:
        if not hasattr(child, "classes"):
            continue
        if child is header:
            header_seen = True
            continue
        if child is input_node:
            break
        if header_seen:
            description_nodes.append(child)
    description = "".join(render_rich_text(node) for node in description_nodes).strip()

    samples = []
    for sample_node in sample_root.find_all(class_name="sample-test"):
        sample_input = sample_node.find_first(class_name="input")
        sample_output = sample_node.find_first(class_name="output")
        input_pre = sample_input.find_first(tag="pre") if sample_input else None
        output_pre = sample_output.find_first(tag="pre") if sample_output else None
        if input_pre is not None and output_pre is not None:
            samples.append({"input": node_text(input_pre), "output": node_text(output_pre)})
    if not samples:
        raise CodeforcesProblemError("No Codeforces samples were found")

    note = statement.find_first(class_name="note")
    return {
        "contest_id": expected_contest_id,
        "index": expected_index,
        "title": title,
        "description": description,
        "input_description": _render_section(input_node),
        "output_description": _render_section(output_node),
        "samples": samples,
        "hint": _render_section(note) if note else "",
        "time_limit": _parse_time_limit(node_text(time_node)),
        "memory_limit": _parse_memory_limit(node_text(memory_node)),
        "languages": list(CODEFORCES_LANGUAGE_IDS),
        "language_ids": dict(CODEFORCES_LANGUAGE_IDS),
    }


def _fetch_problem_metadata(contest_id, index):
    try:
        response = requests.get(
            f"{CODEFORCES_BASE_URL}/api/contest.standings",
            params={"contestId": contest_id},
            timeout=30,
        )
        payload = response.json()
    except (requests.RequestException, ValueError):
        return {}
    if payload.get("status") != "OK":
        return {}
    problems = (payload.get("result") or {}).get("problems") or []
    return next(
        (problem for problem in problems if str(problem.get("index", "")).upper() == index),
        {},
    )


def fetch_codeforces_problem(reference, timeout=30):
    contest_id, index = parse_codeforces_reference(reference)
    url = f"{CODEFORCES_BASE_URL}/problemset/problem/{contest_id}/{index}"
    try:
        response = requests.get(
            url,
            params={"locale": "en"},
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise CodeforcesProblemError(f"Unable to fetch Codeforces problem: {exc}") from exc
    if response.status_code != 200:
        raise CodeforcesProblemError(f"Codeforces returned HTTP {response.status_code}")
    return build_codeforces_problem_from_page(reference, response.text, url=url)


def build_codeforces_problem_from_page(reference, content, url=None):
    contest_id, index = parse_codeforces_reference(reference)
    url = url or f"{CODEFORCES_BASE_URL}/problemset/problem/{contest_id}/{index}"
    data = parse_codeforces_problem_page(content, contest_id, index)
    metadata = _fetch_problem_metadata(contest_id, index)
    if metadata.get("name"):
        data["title"] = metadata["name"]
    data.update({
        "remote_id": f"{contest_id}{index}",
        "url": url,
        "rating": metadata.get("rating"),
        "tags": metadata.get("tags") or [],
    })
    return data
