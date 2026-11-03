from pathlib import Path

import yaml
from jinja2 import Environment


TASKS_DIR = Path(__file__).resolve().parents[2] / "roles/splunk_common/tasks"
TASKS = yaml.safe_load((TASKS_DIR / "configure_users.yml").read_text())
MAIN = yaml.safe_load((TASKS_DIR / "main.yml").read_text())
PASSWORD = "us3r-pa55-do-not-leak"
USERS = {
    "obs": {"password": PASSWORD, "roles": ["observability_role"]},
    "auto": {"password": PASSWORD, "roles": ["automation_role", "user"]},
}


def task_named(name):
    return next(task for task in TASKS if task["name"] == name)


def main_index(task_file):
    return next(i for i, task in enumerate(MAIN) if task.get("include_tasks") == task_file)


def render_failures(results):
    task = task_named("Fail if a declared Splunk user could not be applied")
    template = Environment().from_string(task["vars"]["splunk_user_failures"])
    return template.render(splunk_user_apply={"results": results}, splunk={"users": USERS}).strip()


def test_users_applied_after_splunkd_start_and_user_seed_removal():
    configure = main_index("configure_users.yml")
    assert configure > main_index("start_splunk.yml")
    assert configure > main_index("clean_user_seed.yml")


def test_users_applied_only_when_declared():
    condition = MAIN[main_index("configure_users.yml")]["when"]
    expression = Environment().compile_expression(condition)
    assert expression(splunk={"users": USERS})
    assert not expression(splunk={"users": {}})
    assert not expression(splunk={"users": None})
    assert not expression(splunk={})


def test_password_handling_task_is_never_logged():
    apply = task_named("Create or update declared Splunk users")
    assert apply["no_log"] is True
    assert apply["failed_when"] is False


def test_failure_report_is_not_a_loop():
    # A loop item would carry the raw splunkd response into verbose output
    assert "loop" not in task_named("Fail if a declared Splunk user could not be applied")


def test_failure_report_empty_when_all_users_applied():
    results = [{"status": 201, "lookup": {"item": "obs"}}, {"status": 200, "lookup": {"item": "auto"}}]
    assert render_failures(results) == ""


def test_failure_report_names_users_and_redacts_passwords():
    results = [
        {"status": 201, "lookup": {"item": "obs"}},
        {"status": 400, "lookup": {"item": "auto"},
         "json": {"messages": [{"type": "ERROR", "text": "Role=automation_role is not valid " + PASSWORD}]}},
    ]
    report = render_failures(results)
    assert "'auto' (HTTP 400)" in report
    assert "Role=automation_role is not valid" in report
    assert "'obs'" not in report
    assert PASSWORD not in report


def test_failure_report_without_response():
    report = render_failures([{"lookup": {"item": "obs"}, "failed": False}])
    assert report == "'obs' (HTTP no response)"
