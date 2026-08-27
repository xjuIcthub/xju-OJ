"""Create the two small public demo problems used for OJ acceptance.

This file is intentionally runnable through ``manage.py shell`` so it does not
need to be copied into the backend image.  It is dry-run by default.  Set
``DEMO_PROBLEMS_MODE=apply`` to write the test-case directories and rows.
"""

import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from account.models import User
from options.options import SysOptions
from problem.models import Problem, ProblemDifficulty, ProblemIOMode, ProblemRuleType, ProblemTag
from utils.xss_filter import XSSHtml


SOURCE = "ICThub demo problems v1"
CREATOR_USERNAME = os.environ.get("SEED_DEMO_PROBLEMS_CREATOR", "winbeau")
MODE = os.environ.get("DEMO_PROBLEMS_MODE", "check").strip().lower()

AB_DISPLAY_ID = "demo-ab"
AB_TEST_CASE_ID = "demo-ab-v1"
AB_TAGS = ["demo", "arithmetic"]
AB_SAMPLES = [
    {"input": "1 2", "output": "3"},
    {"input": "-100 58", "output": "-42"},
]
AB_PAIRS = [
    (0, 0),
    (1, 2),
    (-1, 1),
    (-5, -7),
    (100, 200),
    (-100, 250),
    (12345, 67890),
    (-12345, 67890),
    (999999999, 1),
    (-1000000000, 1),
    (1000000000, 1000000000),
    (-1000000000, -1000000000),
    (214748364, 987654321),
    (-214748364, -987654321),
    (314159265, 271828182),
    (-314159265, 271828182),
    (42, -42),
    (7, 0),
    (-999999999, 999999999),
    (1000000000, -1000000000),
]

SPJ_DISPLAY_ID = "demo-spj"
SPJ_TEST_CASE_ID = "demo-spj-v1"
SPJ_TAGS = ["demo", "special-judge"]
SPJ_SAMPLES = [
    {"input": "5", "output": "1 2 3 4 5"},
    {"input": "4", "output": "4 1 3 2"},
]
SPJ_NS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 25, 31, 50, 64, 100, 127, 256, 512, 1000]

SPJ_CODE = r"""#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>

/* Accept any permutation of 1..n, with no extra non-whitespace output. */
int main(int argc, char **argv) {
    if (argc != 3) {
        return 2;
    }

    FILE *input = fopen(argv[1], "r");
    FILE *output = fopen(argv[2], "r");
    if (!input || !output) {
        if (input) fclose(input);
        if (output) fclose(output);
        return 2;
    }

    long long n;
    if (fscanf(input, "%lld", &n) != 1 || n < 1 || n > 1000000) {
        fclose(input);
        fclose(output);
        return 2;
    }

    unsigned char *seen = calloc((size_t)n + 1, sizeof(*seen));
    if (!seen) {
        fclose(input);
        fclose(output);
        return 2;
    }

    for (long long i = 0; i < n; ++i) {
        long long value;
        if (fscanf(output, "%lld", &value) != 1 || value < 1 || value > n || seen[value]) {
            free(seen);
            fclose(input);
            fclose(output);
            return 1;
        }
        seen[value] = 1;
    }

    int ch;
    do {
        ch = fgetc(output);
    } while (ch != EOF && isspace((unsigned char)ch));

    free(seen);
    fclose(input);
    fclose(output);
    return ch == EOF ? 0 : 1;
}
"""


def _ab_cases():
    return [{"input": f"{a} {b}\n", "output": f"{a + b}\n"} for a, b in AB_PAIRS]


def _spj_cases():
    return [{"input": f"{n}\n"} for n in SPJ_NS]


def _md5(value):
    return hashlib.md5(value.rstrip().encode("utf-8")).hexdigest()


def _case_info(cases, spj):
    info = {"spj": spj, "test_cases": {}}
    for index, case in enumerate(cases, start=1):
        input_name = f"{index}.in"
        item = {
            "input_name": input_name,
            "input_size": len(case["input"].encode("utf-8")),
        }
        if not spj:
            output_name = f"{index}.out"
            item.update({
                "output_name": output_name,
                "output_size": len(case["output"].encode("utf-8")),
                "stripped_output_md5": _md5(case["output"]),
            })
        info["test_cases"][str(index)] = item
    return info


def _case_files(cases, spj):
    files = {}
    for index, case in enumerate(cases, start=1):
        files[f"{index}.in"] = case["input"].encode("utf-8")
        if not spj:
            files[f"{index}.out"] = case["output"].encode("utf-8")
    return files


def _definitions():
    return [
        {
            "display_id": AB_DISPLAY_ID,
            "test_case_id": AB_TEST_CASE_ID,
            "title": "A+B",
            "description": (
                "<p>给定两个整数 <code>a</code> 和 <code>b</code>，请计算并输出它们的和。</p>"
            ),
            "input_description": (
                "<p>一行包含两个整数 <code>a</code> 和 <code>b</code>，满足 "
                "<code>-10^9 &le; a,b &le; 10^9</code>。</p>"
            ),
            "output_description": "<p>输出 <code>a+b</code>。</p>",
            "hint": "<p>结果范围在有符号 32 位整数范围内。</p>",
            "samples": AB_SAMPLES,
            "cases": _ab_cases(),
            "spj": False,
            "spj_language": None,
            "spj_code": None,
            "spj_version": "",
            "tags": AB_TAGS,
        },
        {
            "display_id": SPJ_DISPLAY_ID,
            "test_case_id": SPJ_TEST_CASE_ID,
            "title": "Special Judge：合法排列",
            "description": (
                "<p>给定一个整数 <code>n</code>，请输出 <code>1</code> 到 <code>n</code> 的一个排列。</p>"
                "<p>排列的顺序不限，只要每个整数恰好出现一次即可。</p>"
            ),
            "input_description": "<p>一行包含一个整数 <code>n</code>，满足 <code>1 &le; n &le; 1000000</code>。</p>",
            "output_description": (
                "<p>输出恰好 <code>n</code> 个整数，它们必须是 <code>1..n</code> 的一个排列，"
                "整数之间使用空白分隔。</p>"
            ),
            "hint": "<p>例如 <code>n=4</code> 时，<code>4 1 3 2</code> 也是合法答案。</p>",
            "samples": SPJ_SAMPLES,
            "cases": _spj_cases(),
            "spj": True,
            "spj_language": "C",
            "spj_code": SPJ_CODE,
            "spj_version": hashlib.md5(("C:" + SPJ_CODE).encode("utf-8")).hexdigest(),
            "tags": SPJ_TAGS,
        },
    ]


def _test_case_score(definition):
    return [
        {
            "input_name": f"{index}.in",
            "output_name": "-" if definition["spj"] else f"{index}.out",
            "score": 0,
        }
        for index in range(1, len(definition["cases"]) + 1)
    ]


def _expected_info(definition):
    return _case_info(definition["cases"], definition["spj"])


def _assert_definition(definition):
    if len(definition["cases"]) != 20:
        raise RuntimeError(f"{definition['display_id']} must have exactly 20 test cases")
    if len(definition["samples"]) < 2:
        raise RuntimeError(f"{definition['display_id']} must have at least two samples")
    if definition["spj"] and not definition["spj_code"]:
        raise RuntimeError("SPJ source is empty")
    if not definition["spj"] and any("output" not in case for case in definition["cases"]):
        raise RuntimeError("standard-judge case is missing expected output")


def _regular_file(path):
    try:
        value = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(value.st_mode) and value.st_nlink == 1


def _verify_case_dir(directory, definition):
    expected_info = _expected_info(definition)
    expected_files = _case_files(definition["cases"], definition["spj"])
    info_path = directory / "info"
    if not _regular_file(info_path):
        raise RuntimeError(f"missing regular test-case info: {info_path}")
    try:
        actual_info = json.loads(info_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid test-case info: {info_path}") from exc
    if actual_info != expected_info:
        raise RuntimeError(f"test-case info mismatch: {directory}")

    allowed_extra = {f"{definition['test_case_id']}.zip"}
    actual_names = {item.name for item in directory.iterdir()}
    expected_names = set(expected_files) | {"info"}
    unexpected = actual_names - expected_names - allowed_extra
    if unexpected:
        raise RuntimeError(f"unexpected files in {directory}: {sorted(unexpected)}")
    for name, expected_content in expected_files.items():
        path = directory / name
        if not _regular_file(path) or path.read_bytes() != expected_content:
            raise RuntimeError(f"test-case file mismatch: {path}")


def _prepare_case_dir(definition, base_dir, created_dirs):
    directory = base_dir / definition["test_case_id"]
    if directory.exists():
        if not directory.is_dir():
            raise RuntimeError(f"test-case path is not a directory: {directory}")
        _verify_case_dir(directory, definition)
        return "existing"

    if MODE == "check":
        return "missing"

    base_dir.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".icthub-demo-", dir=base_dir))
    try:
        for name, content in _case_files(definition["cases"], definition["spj"]).items():
            path = temporary / name
            path.write_bytes(content)
            path.chmod(0o640)
        info_path = temporary / "info"
        info_path.write_text(json.dumps(_expected_info(definition), indent=2) + "\n", encoding="utf-8")
        info_path.chmod(0o640)
        temporary.chmod(0o710)
        temporary.rename(directory)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    created_dirs.append(directory)
    _verify_case_dir(directory, definition)
    return "created"


def _find_problem(definition):
    rows = list(Problem.objects.filter(_id=definition["display_id"], contest_id__isnull=True))
    if len(rows) > 1:
        raise RuntimeError(f"duplicate standalone display ID: {definition['display_id']}")
    return rows[0] if rows else None


def _clean_rich_text(value):
    with XSSHtml() as parser:
        return parser.clean(value or "")


def _validate_existing(problem, definition, creator):
    if problem.created_by_id != creator.id and not problem.created_by.is_admin_role():
        raise RuntimeError(f"{definition['display_id']} exists with a different non-admin creator")
    expected_values = {
        "source": SOURCE,
        "test_case_id": definition["test_case_id"],
        "title": definition["title"],
        "description": _clean_rich_text(definition["description"]),
        "input_description": _clean_rich_text(definition["input_description"]),
        "output_description": _clean_rich_text(definition["output_description"]),
        "hint": _clean_rich_text(definition["hint"]),
        "samples": definition["samples"],
        "test_case_score": _test_case_score(definition),
        "spj": definition["spj"],
        "spj_language": definition["spj_language"],
        "spj_code": definition["spj_code"],
        "spj_version": definition["spj_version"],
        "rule_type": ProblemRuleType.ACM,
    }
    for field, expected in expected_values.items():
        if getattr(problem, field) != expected:
            raise RuntimeError(f"{definition['display_id']} exists with incompatible {field}")


def _create_problem(definition, creator, language_names):
    problem = Problem.objects.create(
        _id=definition["display_id"],
        title=definition["title"],
        description=definition["description"],
        input_description=definition["input_description"],
        output_description=definition["output_description"],
        samples=definition["samples"],
        test_case_id=definition["test_case_id"],
        test_case_score=_test_case_score(definition),
        hint=definition["hint"],
        languages=language_names,
        template={},
        created_by=creator,
        time_limit=1000 if not definition["spj"] else 2000,
        memory_limit=256,
        io_mode={"io_mode": ProblemIOMode.standard, "input": "input.txt", "output": "output.txt"},
        spj=definition["spj"],
        spj_language=definition["spj_language"],
        spj_code=definition["spj_code"],
        spj_version=definition["spj_version"],
        spj_compile_ok=definition["spj"],
        rule_type=ProblemRuleType.ACM,
        visible=True,
        difficulty=ProblemDifficulty.Low,
        source=SOURCE,
        total_score=0,
        statistic_info={},
        share_submission=False,
        last_update_time=now(),
    )
    for tag_name in definition["tags"]:
        tag, _ = ProblemTag.objects.get_or_create(name=tag_name)
        problem.tags.add(tag)
    return problem


def main():
    if MODE not in {"check", "apply"}:
        raise RuntimeError("DEMO_PROBLEMS_MODE must be check or apply")

    definitions = _definitions()
    for definition in definitions:
        _assert_definition(definition)

    creator = User.objects.filter(username=CREATOR_USERNAME).first()
    if creator is None:
        raise RuntimeError(f"creator user does not exist: {CREATOR_USERNAME}")
    if not creator.is_admin_role():
        raise RuntimeError(f"creator is not an OJ admin: {CREATOR_USERNAME}")

    base_dir = Path(settings.TEST_CASE_DIR)
    if MODE == "check" and not base_dir.exists():
        raise RuntimeError(f"test-case directory does not exist: {base_dir}")

    created_dirs = []
    directory_states = {}
    try:
        for definition in definitions:
            display_id = definition["display_id"]
            directory_states[display_id] = _prepare_case_dir(definition, base_dir, created_dirs)
            if directory_states[display_id] == "missing" and _find_problem(definition) is not None:
                raise RuntimeError(f"{display_id} exists but its test-case directory is missing")

        language_names = list(SysOptions.language_names)
        if not language_names:
            raise RuntimeError("SysOptions.language_names is empty")

        created = []
        existing = []
        repaired = []
        with transaction.atomic():
            for definition in definitions:
                problem = _find_problem(definition)
                if problem is None:
                    if MODE == "check":
                        created.append(definition["display_id"])
                        continue
                    _create_problem(definition, creator, language_names)
                    created.append(definition["display_id"])
                    continue

                _validate_existing(problem, definition, creator)
                if not problem.visible:
                    if MODE == "apply":
                        problem.visible = True
                        problem.save(update_fields=["visible"])
                        repaired.append(definition["display_id"])
                    else:
                        repaired.append(definition["display_id"])
                existing.append(definition["display_id"])

        print(f"demo-problems mode={MODE} creator={CREATOR_USERNAME}")
        for definition in definitions:
            display_id = definition["display_id"]
            print(
                f"{display_id}: cases=20 spj={str(definition['spj']).lower()} "
                f"test_case_id={definition['test_case_id']} files={directory_states[display_id]}"
            )
        print(f"created_or_would_create={len(created)} existing={len(existing)} repaired={len(repaired)}")
        if MODE == "check":
            print("check passed; no database or test-case files were changed")
        else:
            print("apply passed; demo problems are visible in the standalone OJ problem list")
    except Exception:
        if MODE == "apply":
            for directory in created_dirs:
                shutil.rmtree(directory, ignore_errors=True)
        raise


main()
