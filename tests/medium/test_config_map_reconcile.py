#!/usr/bin/env python
"""
Regression check for ConfigMap reconciliation in roles/splunk_common (CSPL-5711).

Runs the real splunk_common task files against a temporary splunk.home on
localhost: remove_stale_sok_conf.yml, then the splunk.conf writer tasks taken
verbatim from roles/splunk_common/tasks/main.yml. Each scenario provisions twice
against the same splunk.home, under hash_behaviour=merge and =replace.

Requires ansible-playbook (ansible~=11.0 / ansible-core 2.18) on PATH or next to
the running interpreter; the tests are skipped otherwise.

    python3 -m pytest -sv tests/medium/test_config_map_reconcile.py
    python3 tests/medium/test_config_map_reconcile.py   # print a report

Set SPLUNK_ANSIBLE_ROOT to run the tasks from another checkout.
"""
from __future__ import absolute_import, print_function

import copy
import grp
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile

import pytest
import yaml

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.realpath(
    os.environ.get("SPLUNK_ANSIBLE_ROOT") or os.path.join(FILE_DIR, "..", "..")
)
TASKS_DIR = os.path.join(REPO_DIR, "roles", "splunk_common", "tasks")
FILTER_PLUGINS_DIR = os.path.join(REPO_DIR, "roles", "splunk_common", "filter_plugins")
HASH_BEHAVIOURS = ("merge", "replace")
REMOVAL_TASK_PREFIX = "Remove ConfigMap-owned options"
RECEIPT = ".{}.conf.splunk-ansible-managed.yml"


def find_ansible_playbook():
    sibling = os.path.join(os.path.dirname(sys.executable), "ansible-playbook")
    if os.path.exists(sibling):
        return sibling
    return shutil.which("ansible-playbook")


ANSIBLE_PLAYBOOK = find_ansible_playbook()


def conf_writer_tasks():
    """Return the splunk.conf writer tasks from main.yml, with absolute include paths."""
    with open(os.path.join(TASKS_DIR, "main.yml")) as stream:
        main_tasks = yaml.safe_load(stream)
    index = next(
        i for i, task in enumerate(main_tasks)
        if task.get("include_tasks") == "set_config_file.yml"
    )
    selected = [main_tasks[index]]
    # Any splunk.conf preparation directly before the writer loop runs too.
    for task in reversed(main_tasks[:index]):
        if "splunk.conf" not in json.dumps(task) or "include_tasks" in task:
            break
        selected.insert(0, task)
    selected = copy.deepcopy(selected)
    for task in selected:
        if "include_tasks" in task:
            task["include_tasks"] = os.path.join(TASKS_DIR, task["include_tasks"])
    return selected


def build_playbook(splunk_home, conf):
    user = pwd.getpwuid(os.getuid()).pw_name
    group = grp.getgrgid(os.getgid()).gr_name
    return [{
        "name": "Reconcile splunk.conf",
        "hosts": "localhost",
        "connection": "local",
        "gather_facts": False,
        "vars": {
            "ansible_become": False,
            "ansible_python_interpreter": sys.executable,
            "hide_password": False,
            "splunk": {"user": user, "group": group, "home": splunk_home, "conf": conf},
        },
        "tasks": [{"include_tasks": os.path.join(TASKS_DIR, "remove_stale_sok_conf.yml")}]
        + conf_writer_tasks(),
    }]


def run_playbook(workdir, splunk_home, conf, hash_behaviour):
    playbook = os.path.join(workdir, "site.yml")
    with open(playbook, "w") as stream:
        yaml.safe_dump(build_playbook(splunk_home, conf), stream, default_flow_style=False)
    config = os.path.join(workdir, "ansible.cfg")
    with open(config, "w") as stream:
        stream.write("[defaults]\nretry_files_enabled = False\nlocalhost_warning = False\n")
    env = dict(os.environ)
    env.update({
        "ANSIBLE_CONFIG": config,
        "ANSIBLE_HASH_BEHAVIOUR": hash_behaviour,
        "ANSIBLE_STDOUT_CALLBACK": "ansible.posix.json",
        "ANSIBLE_FILTER_PLUGINS": FILTER_PLUGINS_DIR,
        "ANSIBLE_LOCAL_TEMP": os.path.join(workdir, "tmp"),
        "ANSIBLE_NOCOLOR": "1",
    })
    proc = subprocess.run(
        [ANSIBLE_PLAYBOOK, "-i", "localhost,", playbook],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, universal_newlines=True, check=False,
    )
    if proc.returncode != 0:
        raise AssertionError("ansible-playbook failed:\n{}\n{}".format(proc.stdout[-4000:], proc.stderr[-4000:]))
    return removal_counts(json.loads(proc.stdout))


def removal_counts(report):
    """Count executed removal tasks (one per stanza) and option removals (loop items)."""
    tasks = items = 0
    for play in report["plays"]:
        for task in play["tasks"]:
            if not task["task"]["name"].startswith(REMOVAL_TASK_PREFIX):
                continue
            result = task["hosts"].get("localhost", {})
            results = result.get("results")
            if results is None:
                executed = 0 if result.get("skipped") else 1
            else:
                executed = sum(1 for item in results if not item.get("skipped"))
            if executed:
                tasks += 1
                items += executed
    return {"tasks": tasks, "options": items}


def read_conf(path):
    """Parse a .conf file into {stanza: {option: value}}; None if missing."""
    if not os.path.exists(path):
        return None
    stanzas = {}
    current = None
    with open(path) as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = stanzas.setdefault(line[1:-1], {})
            elif "=" in line and current is not None:
                key, value = line.split("=", 1)
                current[key.strip()] = value.strip()
    return stanzas


def write_file(path, content):
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "w") as stream:
        stream.write(content)


def entry(key, content, directory=None):
    value = {"content": content}
    if directory is not None:
        value["directory"] = directory
    return {"key": key, "value": value}


# ---------------------------------------------------------------------------
# Scenarios. Each provides run1/run2 splunk.conf lists (as functions of
# splunk.home), optional seed/between hooks, and the files to report.
# ---------------------------------------------------------------------------

def six_files(home):
    apps = home + "/etc/apps"
    return [
        entry("server", {
            "general": {"serverName": "idx-1", "pass4SymmKey": "s3cret"},
            "sslConfig": {"sslVerifyServerCert": "false"},
        }),
        entry("outputs", {
            "tcpout": {"defaultGroup": "primary"},
            "tcpout:primary": {"server": "idx-a:9997", "useACK": "true"},
        }, apps + "/app1/local"),
        entry("inputs", {"splunktcp://9997": {"disabled": "0"}}, apps + "/app1/local"),
        entry("props", {
            "default": {"TRUNCATE": "10000"},
            "source::/var/log/app.log": {"sourcetype": "app"},
        }, apps + "/app2/local"),
        entry("limits", {"search": {"max_searches_per_cpu": "2"}}),
        entry("server", {
            "general": {"parallelIngestionPipelines": "2"},
            "sslConfig": {"sslVersions": "tls1.2"},
        }, apps + "/app3/local"),
    ]


SIX_FILES_REPORT = [
    "etc/system/local/server.conf",
    "etc/apps/app1/local/outputs.conf",
    "etc/apps/app1/local/inputs.conf",
    "etc/apps/app2/local/props.conf",
    "etc/system/local/limits.conf",
    "etc/apps/app3/local/server.conf",
]


def same_file(home):
    sok = home + "/etc/apps/100-sok/local"
    return [
        entry("outputs", {
            "cloud_processing_queue": {
                "remote_queue.type": "sqs_smartbus",
                "remote_queue.sqs_smartbus.encoding_format": "s2s",
                "remote_queue.sqs_smartbus.large_message_store.endpoint": "https://s3.example",
            },
            "tcpout": {"indexAndForward": "false"},
        }, sok),
        entry("outputs", {
            "tcpout": {"indexAndForward": "true", "defaultGroup": "sok_queue"},
            "remote_queue:sok_queue": {
                "remote_queue.type": "sqs_smartbus",
                "remote_queue.sqs_smartbus.endpoint": "https://sqs.example",
            },
        }, sok),
    ]


def overlap_seed(home):
    write_file(home + "/etc/apps/app_b/local/props.conf", "[shared]\nowned = manual_b\n")


def overlap(home):
    apps = home + "/etc/apps"
    return [
        entry("props", {"shared": {"owned": "a"}}, apps + "/app_a/local"),
        entry("props", {"shared": {"b_owned": "b"}}, apps + "/app_b/local"),
    ]


def dropped_seed(home):
    write_file(home + "/etc/apps/app_d/local/server.conf", "[general]\nmanual = kept\n")


def dropped_run1(home):
    return [entry("server", {
        "general": {"keep": "1", "drop": "2", "changed": "old"},
        "obsolete": {"dropme": "x"},
    }, home + "/etc/apps/app_d/local")]


def dropped_run2(home):
    return [entry("server", {
        "general": {"keep": "1", "changed": "new"},
    }, home + "/etc/apps/app_d/local")]


def emptied_seed(home):
    write_file(home + "/etc/apps/app_e/local/web.conf", "[settings]\nmanual = kept\n")


def emptied_run1(home):
    return [entry("web", {"settings": {"a": "1", "b": "2"}}, home + "/etc/apps/app_e/local")]


def emptied_run2(home):
    return [entry("web", {}, home + "/etc/apps/app_e/local")]


def drop_receipt(home):
    os.remove(os.path.join(home, "etc/apps/app1/local", RECEIPT.format("inputs")))


SCENARIOS = {
    "six_files_unchanged": {"run1": six_files, "report": SIX_FILES_REPORT},
    "six_files_missing_receipt": {"run1": six_files, "between": drop_receipt, "report": SIX_FILES_REPORT},
    "same_file_two_entries": {"run1": same_file, "report": ["etc/apps/100-sok/local/outputs.conf"]},
    "overlap_across_apps": {
        "seed": overlap_seed, "run1": overlap,
        "report": ["etc/apps/app_a/local/props.conf", "etc/apps/app_b/local/props.conf"],
    },
    "option_dropped": {
        "seed": dropped_seed, "run1": dropped_run1, "run2": dropped_run2,
        "report": ["etc/apps/app_d/local/server.conf"],
    },
    "all_settings_removed": {
        "seed": emptied_seed, "run1": emptied_run1, "run2": emptied_run2,
        "report": ["etc/apps/app_e/local/web.conf"],
    },
}


def run_scenario(name, hash_behaviour):
    scenario = SCENARIOS[name]
    workdir = tempfile.mkdtemp(prefix="cspl5711-{}-{}-".format(name, hash_behaviour))
    try:
        home = os.path.join(workdir, "splunk")
        os.makedirs(os.path.join(home, "etc", "system", "local"))
        os.makedirs(os.path.join(workdir, "tmp"))
        if scenario.get("seed"):
            scenario["seed"](home)
        run1 = scenario["run1"](home)
        run2 = scenario.get("run2", scenario["run1"])(home)
        result = {"run1": run_playbook(workdir, home, run1, hash_behaviour)}
        result["after_run1"] = {f: read_conf(os.path.join(home, f)) for f in scenario["report"]}
        if scenario.get("between"):
            scenario["between"](home)
        result["run2"] = run_playbook(workdir, home, run2, hash_behaviour)
        result["after_run2"] = {f: read_conf(os.path.join(home, f)) for f in scenario["report"]}
        result["receipts"] = sorted(
            os.path.relpath(os.path.join(root, f), home)
            for root, _, files in os.walk(home) for f in files
            if f.endswith(".splunk-ansible-managed.yml")
        )
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


needs_ansible = pytest.mark.skipif(ANSIBLE_PLAYBOOK is None, reason="ansible-playbook not available")
behaviours = pytest.mark.parametrize("hash_behaviour", HASH_BEHAVIOURS)


def expected_six_files():
    home = "HOME"
    expected = {}
    for path, conf_entry in zip(SIX_FILES_REPORT, six_files(home)):
        expected[path] = conf_entry["value"]["content"]
    return expected


@needs_ansible
@behaviours
@pytest.mark.parametrize("name", ["six_files_unchanged", "six_files_missing_receipt"])
def test_restart_with_unchanged_config_removes_nothing(name, hash_behaviour):
    result = run_scenario(name, hash_behaviour)
    assert result["run2"] == {"tasks": 0, "options": 0}
    assert result["after_run1"] == expected_six_files()
    assert result["after_run2"] == expected_six_files()


@needs_ansible
@behaviours
def test_entries_for_the_same_file_keep_combined_settings(hash_behaviour):
    result = run_scenario("same_file_two_entries", hash_behaviour)
    expected = {
        "cloud_processing_queue": {
            "remote_queue.type": "sqs_smartbus",
            "remote_queue.sqs_smartbus.encoding_format": "s2s",
            "remote_queue.sqs_smartbus.large_message_store.endpoint": "https://s3.example",
        },
        # The later (SOK) entry wins the conflicting indexAndForward option.
        "tcpout": {"indexAndForward": "true", "defaultGroup": "sok_queue"},
        "remote_queue:sok_queue": {
            "remote_queue.type": "sqs_smartbus",
            "remote_queue.sqs_smartbus.endpoint": "https://sqs.example",
        },
    }
    path = "etc/apps/100-sok/local/outputs.conf"
    assert result["after_run1"][path] == expected
    assert result["after_run2"][path] == expected


@needs_ansible
@behaviours
def test_overlapping_stanza_in_another_app_is_preserved(hash_behaviour):
    result = run_scenario("overlap_across_apps", hash_behaviour)
    for state in ("after_run1", "after_run2"):
        assert result[state]["etc/apps/app_a/local/props.conf"] == {"shared": {"owned": "a"}}
        assert result[state]["etc/apps/app_b/local/props.conf"] == {
            "shared": {"owned": "manual_b", "b_owned": "b"},
        }


@needs_ansible
@behaviours
def test_dropped_option_is_removed_and_others_preserved(hash_behaviour):
    result = run_scenario("option_dropped", hash_behaviour)
    assert result["run2"] == {"tasks": 2, "options": 2}
    assert result["after_run2"]["etc/apps/app_d/local/server.conf"] == {
        "general": {"manual": "kept", "keep": "1", "changed": "new"},
        "obsolete": {},
    }


@needs_ansible
@behaviours
def test_all_desired_settings_removed_cleans_up_target(hash_behaviour):
    result = run_scenario("all_settings_removed", hash_behaviour)
    assert result["after_run1"]["etc/apps/app_e/local/web.conf"] == {
        "settings": {"manual": "kept", "a": "1", "b": "2"},
    }
    assert result["after_run2"]["etc/apps/app_e/local/web.conf"] == {"settings": {"manual": "kept"}}
    assert "etc/apps/app_e/local/" + RECEIPT.format("web") not in result["receipts"]


def main():
    if ANSIBLE_PLAYBOOK is None:
        sys.exit("ansible-playbook not available")
    report = {}
    for name in SCENARIOS:
        for hash_behaviour in HASH_BEHAVIOURS:
            report["{}/{}".format(name, hash_behaviour)] = run_scenario(name, hash_behaviour)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
