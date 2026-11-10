#!/usr/bin/env python
"""
Checks that the splunk.conf writer tasks in roles/splunk_common skip options that
already match on disk (CSPL-5741), by running them on localhost through the
harness in test_config_map_reconcile.py.

Files must end up byte-for-byte and mode-for-mode the same as when every option is
written. "Every option" is produced here by a probe module that crashes, which the
tasks treat as "write everything". Set SPLUNK_ANSIBLE_BASELINE_ROOT to a checkout
from before CSPL-5741 to also compare against its tasks.

    python3 -m pytest -sv tests/medium/test_skip_unchanged_options.py
    SPLUNK_ANSIBLE_BASELINE_ROOT=/tmp/baseline python3 -m pytest -sv tests/medium/test_skip_unchanged_options.py
"""
from __future__ import absolute_import, print_function

import os
import shutil
import stat
import tempfile

import pytest

from test_config_map_reconcile import (
    ANSIBLE_PLAYBOOK, REPO_DIR, WRITE_TASK_PREFIX, entry, read_conf, removal_counts, run_playbook,
    write_file,
)

BASELINE_ROOT = os.environ.get("SPLUNK_ANSIBLE_BASELINE_ROOT")
LOCAL = "etc/apps/t/local"

CRASHING_STUB = """#!/usr/bin/python
import os
from ansible.module_utils.basic import AnsibleModule
os.kill(os.getpid(), 9)
"""

GARBAGE_STUB = """#!/usr/bin/python
from ansible.module_utils.basic import AnsibleModule
print("not json")
"""

needs_ansible = pytest.mark.skipif(ANSIBLE_PLAYBOOK is None, reason="ansible-playbook not available")


def stub_library(directory, source):
    os.makedirs(directory)
    with open(os.path.join(directory, "splunk_conf_pending.py"), "w") as stream:
        stream.write(source)
    return directory


@pytest.fixture(scope="module")
def crashing_library(tmp_path_factory):
    return stub_library(str(tmp_path_factory.mktemp("stub") / "library"), CRASHING_STUB)


def tricky_seed(home):
    local = os.path.join(home, LOCAL)
    write_file(os.path.join(local, "server.conf"), (
        "[general]\nserverName=idx-1\n# pass4SymmKey = old\n[general]\nsite = site1\n\n"
        "[sslConfig]\nsslVerifyServerCert   =   false\nsslVerifyServerCert = true\n"
    ))
    write_file(os.path.join(local, "indexes.conf"), "[main]\nhomePath = $SPLUNK_DB/main/db")
    write_file(os.path.join(local, "props.conf"), u"﻿[default]\nTRUNCATE = 10000\n")
    write_file(os.path.join(local, "limits.conf"), (
        "; comment\n[search]\n;max_searches_per_cpu = 1\nmax_searches_per_cpu = 2\n"
    ))
    write_file(os.path.join(home, "etc/apps/t/default/alert_actions.conf"), "[email]\nfrom = a@b\n")
    os.symlink("../default/alert_actions.conf", os.path.join(local, "alert_actions.conf"))


def tricky_conf(home):
    local = os.path.join(home, LOCAL)
    indexes = {"main": {"homePath": "$SPLUNK_DB/main/db", "maxTotalDataSizeMB": 500}}
    indexes.update(("akamai_%d" % i, dict(("key%d" % k, "v%d" % k) for k in range(14))) for i in range(5))
    return [
        entry("server", {
            "general": {"serverName": "idx-1", "pass4SymmKey": "new", "site": "site1"},
            "sslConfig": {"sslVerifyServerCert": "false"},
            "empty": {},
        }, local),
        entry("indexes", indexes, local),
        entry("props", {"default": {"TRUNCATE": "10000"}, "source::x": {"SHOULD_LINEMERGE": False}}, local),
        entry("limits", {"search": {"max_searches_per_cpu": 2, "ratio": 1.5, "blank": ""}}, local),
        entry("web", {"settings": {"y": True}}, local),
        # ini_file appends a line on every write of a multiline value, so it must be written exactly as before.
        entry("inputs", {"monitor:///var/log/x": {"index": "main", "blacklist": "a\nb"}}, local),
        entry("alert_actions", {"email": {"from": "c@d"}}, local),
        entry("outputs", {"tcpout": {"defaultGroup": "primary"}}),
    ]


def edit_between(home):
    """Change a value, delete an option and loosen a mode, as an admin or app might."""
    path = os.path.join(home, LOCAL, "indexes.conf")
    with open(path) as stream:
        content = stream.read()
    with open(path, "w") as stream:
        stream.write(content.replace("key3 = v3", "key3 = edited", 1).replace("key4 = v4\n", "", 1))
    limits = os.path.join(home, LOCAL, "limits.conf")
    if os.path.exists(limits):
        os.chmod(limits, 0o644)


def no_seed(home):
    pass


def snapshot(home):
    """{relative path: (mode, is symlink, bytes)} for every file under home."""
    files = {}
    for root, _, names in os.walk(home):
        for name in names:
            path = os.path.join(root, name)
            with open(path, "rb") as stream:
                files[os.path.relpath(path, home)] = (
                    stat.S_IMODE(os.lstat(path).st_mode), os.path.islink(path), stream.read(),
                )
    return files


def parse_conf(content):
    path = tempfile.mktemp(suffix=".conf")
    try:
        with open(path, "wb") as stream:
            stream.write(content)
        return read_conf(path)
    finally:
        os.remove(path)


def run_twice(seed, conf, edit, run1_library=None, run2_library=None, check=False, repo_dir=REPO_DIR):
    """Provision, edit, provision again; return snapshots and run-2 write counts."""
    workdir = tempfile.mkdtemp(prefix="cspl5741-")
    try:
        home = os.path.join(workdir, "splunk")
        os.makedirs(os.path.join(home, "etc", "system", "local"))
        os.makedirs(os.path.join(workdir, "tmp"))
        seed(home)
        run_playbook(workdir, home, conf(home), "merge", library_dir=run1_library, repo_dir=repo_dir)
        after_run1 = snapshot(home)
        edit(home)
        before_run2 = snapshot(home)
        report = run_playbook(
            workdir, home, conf(home), "merge", library_dir=run2_library, check=check, repo_dir=repo_dir,
        )
        return {
            "after_run1": after_run1,
            "before_run2": before_run2,
            "after_run2": snapshot(home),
            "writes": removal_counts(report, WRITE_TASK_PREFIX),
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@needs_ansible
def test_skipping_writes_the_same_files_as_writing_every_option(crashing_library):
    every = run_twice(tricky_seed, tricky_conf, edit_between, crashing_library, crashing_library)
    skipping = run_twice(tricky_seed, tricky_conf, edit_between)
    assert skipping["after_run1"] == every["after_run1"]
    assert skipping["after_run2"] == every["after_run2"]
    assert skipping["writes"]["options"] < every["writes"]["options"]
    if BASELINE_ROOT:
        baseline = run_twice(tricky_seed, tricky_conf, edit_between, repo_dir=BASELINE_ROOT)
        assert skipping["after_run1"] == baseline["after_run1"]
        assert skipping["after_run2"] == baseline["after_run2"]


@needs_ansible
def test_edited_values_are_repaired_and_only_they_are_written():
    def conf(home):
        return [entry("indexes", dict(
            ("idx_%d" % i, dict(("key%d" % k, "v%d" % k) for k in range(14))) for i in range(20)
        ), home + "/" + LOCAL)]

    result = run_twice(no_seed, conf, edit_between)
    assert result["writes"] == {"tasks": 1, "options": 2}
    # ini_file re-adds a deleted option at the end of its stanza, so compare values, not bytes.
    assert parse_conf(result["after_run2"][LOCAL + "/indexes.conf"][2]) == conf("HOME")[0]["value"]["content"]


@needs_ansible
def test_one_changed_option_in_a_large_stanza_writes_one_option():
    def conf_with(home, value):
        settings = dict(("capability_%d" % k, "enabled") for k in range(61))
        settings["capability_7"] = value
        return [entry("authorize", {"role_sc_admin": settings}, home + "/" + LOCAL)]

    workdir = tempfile.mkdtemp(prefix="cspl5741-")
    try:
        home = os.path.join(workdir, "splunk")
        os.makedirs(os.path.join(workdir, "tmp"))
        run_playbook(workdir, home, conf_with(home, "enabled"), "merge")
        report = run_playbook(workdir, home, conf_with(home, "disabled"), "merge")
        assert removal_counts(report, WRITE_TASK_PREFIX) == {"tasks": 1, "options": 1}
        assert read_conf(os.path.join(home, LOCAL, "authorize.conf"))["role_sc_admin"]["capability_7"] == "disabled"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@needs_ansible
def test_check_mode_reports_only_pending_options_and_changes_nothing(crashing_library):
    skipping = run_twice(tricky_seed, tricky_conf, edit_between, check=True)
    assert skipping["after_run2"] == skipping["before_run2"]
    every = run_twice(tricky_seed, tricky_conf, edit_between, run2_library=crashing_library, check=True)
    assert skipping["writes"]["options"] < every["writes"]["options"]


@needs_ansible
@pytest.mark.parametrize("stub", [CRASHING_STUB, GARBAGE_STUB], ids=["killed", "invalid_output"])
def test_probe_failure_writes_every_option(stub, crashing_library, tmp_path):
    library = stub_library(str(tmp_path / "library"), stub)
    every = run_twice(tricky_seed, tricky_conf, edit_between, crashing_library, crashing_library)
    failed = run_twice(tricky_seed, tricky_conf, edit_between, run2_library=library)
    assert failed["after_run2"] == every["after_run2"]
    assert failed["writes"] == every["writes"]


def run_once(seed, conf, library_dir=None, repo_dir=REPO_DIR):
    """Provision once over seeded files; return the snapshot."""
    workdir = tempfile.mkdtemp(prefix="cspl5741-")
    try:
        home = os.path.join(workdir, "splunk")
        os.makedirs(os.path.join(home, "etc", "system", "local"))
        os.makedirs(os.path.join(workdir, "tmp"))
        seed(home)
        run_playbook(workdir, home, conf(home), "merge", library_dir=library_dir, repo_dir=repo_dir)
        return snapshot(home)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def aliased_seed(home):
    write_file(os.path.join(home, "etc/apps/real/local/server.conf"), "[s]\na = original\n")
    os.symlink("real", os.path.join(home, "etc/apps/link"))


def aliased_conf(home):
    return [
        entry("server", {"s": {"a": "changed"}}, home + "/etc/apps/real/local"),
        entry("server", {"s": {"a": "original"}}, home + "/etc/apps/link/local"),
    ]


def overlapping_seed(home):
    write_file(os.path.join(home, LOCAL, "server.conf"), "[s]\na = original\n")


def overlapping_conf(home):
    return [entry("server", {" s ": {"a": "changed"}, "s": {"a": "original"}}, home + "/" + LOCAL)]


def header_prefix_seed(home):
    write_file(os.path.join(home, LOCAL, "server.conf"), "[s]x]\na = old\n")


def header_prefix_conf(home):
    return [entry("server", {"s": {"a": "new"}, "s]x": {"a": "old"}}, home + "/" + LOCAL)]


def templated_value_seed(home):
    write_file(os.path.join(home, LOCAL, "server.conf"), '[s]\nj = {"hello":"world"}\n')


def templated_value_conf(home):
    return [entry("server", {"s": {"j": '{"hello":"world"}'}}, home + "/" + LOCAL)]


def merged_map_and_list_conf(home):
    # What merge_dict produces when a list-form splunk.conf lands on a map-form one (the LM).
    return {
        "props": {"directory": home + "/" + LOCAL, "content": {"s": {"a": "1"}}},
        "key": "server",
        "value": {"content": {"kvstore": {"defaultKVStoreType": "local"}}},
    }


def option_syntax_conf(home):
    return [entry("server", {"s": {"a=b": "changed", "a": "original"}}, home + "/" + LOCAL)]


@needs_ansible
@pytest.mark.parametrize(("seed", "conf"), [
    (aliased_seed, aliased_conf), (overlapping_seed, overlapping_conf), (overlapping_seed, option_syntax_conf),
    (header_prefix_seed, header_prefix_conf), (templated_value_seed, templated_value_conf),
    (no_seed, merged_map_and_list_conf),
], ids=["same_file_through_symlinked_directory", "stanza_names_ini_file_merges", "option_name_with_equals",
        "stanza_header_prefix", "value_the_writer_templates_into_a_dict", "map_and_list_conf_merged"])
def test_writes_that_affect_each_other_end_as_the_full_path_does(seed, conf, crashing_library):
    skipping = run_once(seed, conf)
    assert skipping == run_once(seed, conf, library_dir=crashing_library)
    if BASELINE_ROOT:
        assert skipping == run_once(seed, conf, repo_dir=BASELINE_ROOT)
