"""Regression checks for safe, single-attempt Splunk process startup."""

from pathlib import Path

import yaml


TASK_FILE = (
    Path(__file__).resolve().parents[2]
    / "roles"
    / "splunk_common"
    / "tasks"
    / "start_splunk.yml"
)


def _task(name):
    tasks = yaml.safe_load(TASK_FILE.read_text(encoding="utf-8"))

    def walk(items):
        for task in items:
            yield task
            for child_key in ("block", "rescue", "always"):
                if child_key in task:
                    yield from walk(task[child_key])

    return next(task for task in walk(tasks) if task.get("name") == name)


def test_start_command_is_not_reissued_after_a_nonzero_result():
    task = _task("Start Splunk via CLI")

    assert task["failed_when"] is False
    assert "until" not in task
    assert "retries" not in task


def test_nonzero_start_waits_for_the_existing_process():
    task = _task("Wait for Splunk after a non-zero CLI start")

    assert " status " in task["command"]
    assert task["when"] == [
        "not splunk.enable_service",
        "start_splunk.rc | default(0) != 0",
    ]
    assert task["until"] == "start_splunk_status.rc == 0"
    assert task["failed_when"] == "start_splunk_status.rc != 0"
    assert task["retries"] == "{{ wait_for_splunk_retry_num }}"
    assert task["delay"] == "{{ retry_delay }}"
