from django.db import migrations


RICH_TEXT_FIELDS = ("description", "input_description", "output_description", "hint")


def normalize_remote_problem_content(apps, schema_editor):
    from problem.remote.common import render_residual_markdown_links
    from problem.remote.nowcoder import _safe_rich_text

    Problem = apps.get_model("problem", "Problem")
    for problem in Problem.objects.filter(remote_oj__in=("LUOGU", "NOWCODER")).iterator():
        changed = []
        for field in RICH_TEXT_FIELDS:
            value = getattr(problem, field) or ""
            if problem.remote_oj == "LUOGU":
                normalized = render_residual_markdown_links(value)
            else:
                normalized = _safe_rich_text(value)
            if normalized != value:
                setattr(problem, field, normalized)
                changed.append(field)
        if changed:
            problem.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("problem", "0018_unique_public_remote_problem")]

    operations = [migrations.RunPython(normalize_remote_problem_content, migrations.RunPython.noop)]
