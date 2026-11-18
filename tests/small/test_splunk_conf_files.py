#!/usr/bin/env python
"""Unit tests for combining list-form splunk.conf entries by effective file."""

from __future__ import absolute_import

import ast
import copy
import os
import sys

import jinja2
import pytest
import yaml

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.join(FILE_DIR, "..", "..")
sys.path.insert(0, os.path.join(REPO_DIR, "inventory"))
sys.path.insert(0, os.path.join(REPO_DIR, "roles", "splunk_common", "filter_plugins"))

import environ  # noqa: E402
import splunk_conf  # noqa: E402

SYSTEM_LOCAL = "/opt/splunk/etc/system/local"
SOK_LOCAL = "/opt/splunk/etc/apps/100-sok/local"

combine = splunk_conf.FilterModule().filters()["normalize_splunk_conf_entries"]


def entry(key, content, directory=None):
    value = {"content": content}
    if directory is not None:
        value["directory"] = directory
    return {"key": key, "value": value}


def conf_form(entries, form):
    if form == "map":
        return {item["key"]: item["value"] for item in entries}
    return entries


@pytest.mark.parametrize("earlier_form,later_form", [
    ("map", "map"), ("list", "list"), ("map", "list"), ("list", "map"),
])
def test_defaults_merge_combines_settings_for_the_same_target(earlier_form, later_form):
    earlier = conf_form([entry("server", {
        "general": {"serverName": "idx", "site": "site1"},
        "sslConfig": {"sslVersions": "tls1.2"},
    }, SOK_LOCAL)], earlier_form)
    later = conf_form([entry("server", {
        "general": {"site": "site2", "parallelIngestionPipelines": "2"},
        "kvstore": {"disabled": "true"},
    }, SOK_LOCAL)], later_form)

    merged = environ.merge_dict({"splunk": {"conf": earlier}}, {"splunk": {"conf": later}})
    conf = merged["splunk"]["conf"]

    if earlier_form == later_form == "map":
        assert isinstance(conf, dict)
    else:
        # Deduplication belongs to the downstream boundary, where home is final.
        assert isinstance(conf, list)
        assert len(conf) == 2
    assert writer_loop_items(merged["splunk"], combine(conf, SYSTEM_LOCAL)) == [entry("server", {
        "general": {"serverName": "idx", "site": "site2", "parallelIngestionPipelines": "2"},
        "sslConfig": {"sslVersions": "tls1.2"},
        "kvstore": {"disabled": "true"},
    }, SOK_LOCAL)]


@pytest.mark.parametrize("earlier_form,later_form", [
    ("map", "map"), ("list", "list"), ("map", "list"), ("list", "map"),
])
def test_defaults_merge_preserves_the_same_filename_in_different_directories(earlier_form, later_form):
    first = entry("server", {"general": {"site": "site1"}}, SYSTEM_LOCAL)
    second = entry("server", {"general": {"site": "site2"}}, SOK_LOCAL)
    earlier = {"splunk": {"conf": conf_form([first], earlier_form)}}
    later = {"splunk": {"conf": conf_form([second], later_form)}}

    merged = environ.merge_dict(earlier, later)
    conf = merged["splunk"]["conf"]

    assert writer_loop_items(merged["splunk"], combine(conf, SYSTEM_LOCAL)) == [first, second]


@pytest.mark.parametrize("earlier_form,later_form", [
    ("map", "map"), ("list", "list"), ("map", "list"), ("list", "map"),
])
@pytest.mark.parametrize("explicit_first", [False, True])
def test_defaults_merge_resolves_omitted_directory_using_final_home(earlier_form, later_form, explicit_first):
    default_directory = "/srv/splunk/etc/system/local"
    explicit_directory = "/srv/splunk/etc/./system//local/"
    first = entry("server", {"general": {"site": "site1", "serverName": "idx"}},
                  explicit_directory if explicit_first else None)
    second = entry("server", {"general": {"site": "site2"}},
                   None if explicit_first else explicit_directory)
    merged = environ.merge_dict(
        {"splunk": {"home": "/opt/splunk", "conf": conf_form([first], earlier_form)}},
        {"splunk": {"conf": conf_form([second], later_form)}},
    )
    # The home override arrives after the conf sources have already been merged.
    environ.merge_dict(merged, {"splunk": {"home": "/srv/splunk"}})
    conf = merged["splunk"]["conf"]

    assert writer_loop_items(merged["splunk"], combine(conf, default_directory)) == [entry("server", {
        "general": {"site": "site2", "serverName": "idx"},
    }, explicit_directory)]


def test_map_only_defaults_keep_mapping_for_equivalent_explicit_directories():
    merged = environ.merge_dict(
        {"splunk": {"conf": {"server": {
            "directory": SYSTEM_LOCAL, "content": {"general": {"serverName": "idx"}},
        }}}},
        {"splunk": {"conf": {"server": {
            "directory": SYSTEM_LOCAL + "/./", "content": {"general": {"site": "site1"}},
        }}}},
    )

    assert merged["splunk"]["conf"] == {"server": {
        "directory": SYSTEM_LOCAL + "/./",
        "content": {"general": {"serverName": "idx", "site": "site1"}},
    }}


@pytest.mark.parametrize("directory", [SYSTEM_LOCAL, "."])
def test_map_only_defaults_keep_omitted_and_different_explicit_directories_separate(directory):
    first = entry("server", {"general": {"site": "site1"}}, directory)
    second = entry("server", {"general": {"site": "site2"}})
    merged = environ.merge_dict(
        {"splunk": {"conf": conf_form([first], "map")}},
        {"splunk": {"conf": conf_form([second], "map")}},
    )
    default_directory = "/srv/splunk/etc/system/local"

    assert writer_loop_items(merged["splunk"], combine(merged["splunk"]["conf"], default_directory)) == [
        first, second,
    ]


@pytest.mark.parametrize("earlier_form,later_form", [("list", "map"), ("map", "list")])
def test_pcrs_web_survives_sok_defaults_loaded_from_files(tmp_path, earlier_form, later_form):
    web = entry("web", {"settings": {"enableSplunkWebSSL": True, "httpport": 8443}},
                "/opt/splunk/etc/apps/100-whisper/local")
    server = entry("server", {"general": {"serverName": "idx"}}, SOK_LOCAL)
    defaults = {"splunk": {"home": "/opt/splunk"}}
    sources = [
        {"splunk": {"conf": conf_form([web], earlier_form)}},
        {"splunk": {"password": "secret"}},
        {"splunk": {"conf": conf_form([server], later_form)}},
        {"splunk": {"conf": {"server": {"directory": SOK_LOCAL,
                                           "content": {"general": {"pass4SymmKey": "key"}}}}}},
    ]
    for index, source in enumerate(sources):
        source_file = tmp_path / ("defaults-%d.yml" % index)
        source_file.write_text(yaml.safe_dump(source))
        defaults = environ.mergeDefaultsFromFile(defaults, str(source_file))

    conf = defaults["splunk"]["conf"]
    assert writer_loop_items(defaults["splunk"], combine(conf, SYSTEM_LOCAL)) == [
        web,
        entry("server", {"general": {"serverName": "idx", "pass4SymmKey": "key"}}, SOK_LOCAL),
    ]


@pytest.mark.parametrize("filename,fact_name", [
    ("splunk_common/tasks/configure_indexer_cluster_prestart.yml", "idxc_prestart_server_conf_content"),
    ("splunk_indexer/tasks/indexer_clustering.yml", "idxc_server_conf_content"),
    ("splunk_indexer/tasks/setup_multisite.yml", "multisite_server_conf_content"),
])
@pytest.mark.parametrize("earlier_form,later_form", [
    ("map", "map"), ("list", "list"), ("map", "list"), ("list", "map"),
])
@pytest.mark.parametrize("earlier_directory", [None, SOK_LOCAL])
def test_indexer_checks_read_later_merged_server_stanzas(
        filename, fact_name, earlier_form, later_form, earlier_directory):
    variables = environ.merge_dict(
        {"splunk": {"home": "/opt/splunk", "conf": conf_form([
            entry("server", {"general": {"serverName": "idx"}}, earlier_directory),
        ], earlier_form)}},
        {"splunk": {"conf": conf_form([
            entry("server", {"replication_port-ssl://9887": {"disabled": "false"}}),
        ], later_form)}},
    )
    with open(os.path.join(REPO_DIR, "roles", filename)) as stream:
        tasks = yaml.safe_load(stream)
    all_tasks = tasks + [child for task in tasks for child in task.get("block", [])]
    list_form = isinstance(variables["splunk"]["conf"], list)
    task = next(task for task in all_tasks if fact_name in task.get("set_fact", {})
                and ("list format" in task.get("name", "")) == list_form)
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters.update(splunk_conf.FilterModule().filters())

    actual = ast.literal_eval(env.from_string(task["set_fact"][fact_name]).render(**variables))

    assert actual == {
        "general": {"serverName": "idx"},
        "replication_port-ssl://9887": {"disabled": "false"},
    }


@pytest.mark.parametrize("filename,fact_name", [
    ("indexer_clustering.yml", "idxc_server_conf_content"),
    ("setup_multisite.yml", "multisite_server_conf_content"),
])
@pytest.mark.parametrize("form", ["map", "list"])
def test_indexer_restores_only_system_local_ssl_stanzas(filename, fact_name, form):
    from ansible.plugins.filter.core import FilterModule as CoreFilters
    from ansible.plugins.test.core import TestModule as CoreTests

    conf = conf_form([
        entry("server", {
            "general": {"serverName": "app"},
            "replication_port-ssl://9999": {"disabled": "false"},
        }, SOK_LOCAL),
    ], form)
    variables = environ.merge_dict(
        {"splunk": {"home": "/opt/splunk", "conf": conf}},
        {"splunk": {"conf": {"server": {"content": {
            "general": {"site": "site1"},
            "replication_port-ssl://9887": {"disabled": "false"},
        }}}}},
    )
    # Detection content contains all targets, but restoration must keep their locations.
    variables[fact_name] = {"general": {"serverName": "app", "site": "site1"},
                            "replication_port-ssl://9999": {"disabled": "false"},
                            "replication_port-ssl://9887": {"disabled": "false"}}
    variables["has_ssl_replication_port_in_conf"] = True
    variables["has_ssl_replication_port_in_conf_multisite"] = True
    with open(os.path.join(REPO_DIR, "roles", "splunk_indexer", "tasks", filename)) as stream:
        task = next(task for task in yaml.safe_load(stream)
                    if task.get("name", "").startswith("Re-apply SSL replication port configuration"))
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters.update(CoreFilters().filters())
    env.filters.update(splunk_conf.FilterModule().filters())
    env.tests.update(CoreTests().tests())
    candidates = ast.literal_eval(env.from_string(task["with_dict"]).render(**variables))
    restored = {}
    for name, settings in candidates.items():
        context = dict(variables, stanza={"key": name, "value": settings})
        if all(env.compile_expression(condition)(**context) for condition in task["when"]):
            restored[name] = settings

    assert restored == {"replication_port-ssl://9887": {"disabled": "false"}}


@pytest.mark.parametrize("filename", ["indexer_clustering.yml", "setup_multisite.yml"])
@pytest.mark.parametrize("conf", [{}, {"conf": None}, {"conf": []}])
def test_indexer_restoration_loop_tolerates_missing_or_empty_conf(filename, conf):
    with open(os.path.join(REPO_DIR, "roles", "splunk_indexer", "tasks", filename)) as stream:
        task = next(task for task in yaml.safe_load(stream)
                    if task.get("name", "").startswith("Re-apply SSL replication port configuration"))
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters.update(splunk_conf.FilterModule().filters())
    variables = {"splunk": dict(conf, home="/opt/splunk")}

    assert ast.literal_eval(env.from_string(task["with_dict"]).render(**variables)) == {}


def test_entries_for_the_same_file_are_merged_into_one():
    entries = [
        entry("outputs", {"cloud_processing_queue": {"remote_queue.type": "sqs_smartbus"}}, SOK_LOCAL),
        entry("outputs", {"remote_queue:sok_queue": {"remote_queue.type": "sqs_smartbus"}}, SOK_LOCAL),
    ]

    combined = combine(entries, SYSTEM_LOCAL)

    assert combined == [entry("outputs", {
        "cloud_processing_queue": {"remote_queue.type": "sqs_smartbus"},
        "remote_queue:sok_queue": {"remote_queue.type": "sqs_smartbus"},
    }, SOK_LOCAL)]


def test_later_entry_wins_conflicting_options():
    entries = [
        entry("outputs", {"tcpout": {"indexAndForward": "false", "maxQueueSize": "10MB"}}, SOK_LOCAL),
        entry("outputs", {"tcpout": {"indexAndForward": "true"}}, SOK_LOCAL),
        entry("outputs", {"tcpout": {"maxQueueSize": "auto"}}, SOK_LOCAL),
    ]

    combined = combine(entries, SYSTEM_LOCAL)

    assert combined[0]["value"]["content"] == {
        "tcpout": {"indexAndForward": "true", "maxQueueSize": "auto"},
    }
    # Deterministic: same input, same result.
    assert combine(entries, SYSTEM_LOCAL) == combined


def test_combined_entry_keeps_the_first_entry_position():
    entries = [
        entry("outputs", {"a": {"x": "1"}}, SOK_LOCAL),
        entry("inputs", {"b": {"y": "1"}}, SOK_LOCAL),
        entry("outputs", {"c": {"z": "1"}}, SOK_LOCAL),
    ]

    combined = combine(entries, SYSTEM_LOCAL)

    assert [e["key"] for e in combined] == ["outputs", "inputs"]
    assert combined[0]["value"]["content"] == {"a": {"x": "1"}, "c": {"z": "1"}}


def test_different_directories_and_files_are_kept_separate():
    entries = [
        entry("server", {"general": {"serverName": "idx"}}),
        entry("server", {"general": {"parallelIngestionPipelines": "2"}}, "/opt/splunk/etc/apps/app1/local"),
        entry("web", {"settings": {"enableSplunkWebSSL": "true"}}),
        entry("outputs", {"tcpout": {"defaultGroup": "a"}}, "/opt/splunk/etc/apps/app1/local"),
        entry("outputs", {"tcpout": {"defaultGroup": "b"}}, "/opt/splunk/etc/apps/app2/local"),
    ]

    assert combine(entries, SYSTEM_LOCAL) == entries


def test_default_and_explicit_spellings_of_one_directory_are_merged():
    entries = [
        entry("server", {"general": {"serverName": "idx"}}),
        entry("server", {"sslConfig": {"sslVersions": "tls1.2"}}, SYSTEM_LOCAL + "/"),
        entry("server", {"kvstore": {"disabled": "true"}}, "/opt/splunk/etc/./system//local"),
    ]

    combined = combine(entries, SYSTEM_LOCAL)

    assert len(combined) == 1
    assert combined[0]["value"]["content"] == {
        "general": {"serverName": "idx"},
        "sslConfig": {"sslVersions": "tls1.2"},
        "kvstore": {"disabled": "true"},
    }


def test_combining_does_not_mutate_the_input():
    entries = [
        entry("outputs", {"tcpout": {"defaultGroup": "a"}}, SOK_LOCAL),
        entry("outputs", {"tcpout": {"defaultGroup": "b"}}, SOK_LOCAL),
    ]
    original = copy.deepcopy(entries)

    combine(entries, SYSTEM_LOCAL)

    assert entries == original


def test_dict_form_conf_is_returned_untouched():
    dict_conf = {
        "server": {"content": {"general": {"serverName": "idx"}}},
        "web": {"directory": "/opt/splunk/etc/apps/app1/local", "content": {"settings": {}}},
    }
    original = copy.deepcopy(dict_conf)

    assert combine(dict_conf, SYSTEM_LOCAL) is dict_conf
    assert dict_conf == original


def test_malformed_entries_pass_through_unchanged():
    entries = [
        "not-a-mapping",
        {"key": "server"},
        {"value": {"content": {"general": {"a": "1"}}}},
        entry("server", {"general": {"a": "1"}}),
    ]

    assert combine(entries, SYSTEM_LOCAL) == entries


def noah_entries():
    return [
        entry("server", {"noahService": {"uri": "https://noah.example"}}),
        entry("outputs", {"tcpout": {"defaultGroup": "a"}}, SOK_LOCAL),
        entry("server", {"noahService": {"pass4SymmKey": "noah-secret"}}),
        entry("outputs", {"tcpout": {"useACK": "true"}}, SOK_LOCAL),
        entry("server", {"general": {"site": "site1"}}, "/opt/splunk/etc/apps/app1/local"),
    ]


def server_entries(entries):
    return [e for e in entries if e["key"] == "server"]


def test_noah_normalization_still_merges_only_server_conf():
    vars_scope = {
        "splunk_noah_enabled": True,
        "splunk": {"home": "/opt/splunk", "conf": noah_entries()},
    }

    environ.normalizeNoahConf(vars_scope)

    assert [e["key"] for e in vars_scope["splunk"]["conf"]] == ["server", "outputs", "outputs", "server"]


def test_combining_noah_effective_conf_leaves_its_server_entries_unchanged():
    vars_scope = {
        "splunk_noah_enabled": True,
        "splunk": {"home": "/opt/splunk", "conf": noah_entries()},
    }
    environ.normalizeNoahConf(vars_scope)
    splunk_conf_effective = vars_scope["splunk"]["conf"]

    combined = combine(splunk_conf_effective, SYSTEM_LOCAL)

    assert server_entries(combined) == server_entries(splunk_conf_effective)
    assert server_entries(combined)[0]["value"]["content"]["noahService"] == {
        "uri": "https://noah.example",
        "pass4SymmKey": "noah-secret",
    }
    assert combined == combine(noah_entries(), SYSTEM_LOCAL)


# ---------------------------------------------------------------------------
# Wiring in roles/splunk_common/tasks/main.yml
# ---------------------------------------------------------------------------

def main_tasks():
    with open(os.path.join(REPO_DIR, "roles", "splunk_common", "tasks", "main.yml")) as stream:
        return yaml.safe_load(stream)


def writer_loop_items(splunk, splunk_conf_by_file=None):
    """Render the conf_entries passed to set_config_files.yml from main.yml."""
    task = next(t for t in main_tasks() if t.get("include_tasks") == "set_config_files.yml")
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters["dict2items"] = lambda d: [{"key": k, "value": v} for k, v in d.items()]
    env.tests["mapping"] = lambda value: isinstance(value, dict)
    context = {"splunk": splunk}
    if splunk_conf_by_file is not None:
        context["splunk_conf_by_file"] = splunk_conf_by_file
    return ast.literal_eval(env.from_string(task["vars"]["conf_entries"]).render(**context))


def test_combine_task_runs_before_the_writer_loop_for_list_form_only():
    tasks = main_tasks()
    names = [t.get("name") for t in tasks]
    combine_index = names.index("Combine list-form splunk.conf entries by effective file")
    writer_index = next(i for i, t in enumerate(tasks) if t.get("include_tasks") == "set_config_files.yml")
    noah_index = next(i for i, t in enumerate(tasks)
                      if t.get("include_role", {}).get("tasks_from") == "pre_auth")
    combine_task = tasks[combine_index]

    assert noah_index < combine_index < writer_index
    assert "splunk_conf_effective | default(splunk.conf)" in combine_task["set_fact"]["splunk_conf_by_file"]
    assert "normalize_splunk_conf_entries(splunk.home + '/etc/system/local')" in (
        combine_task["set_fact"]["splunk_conf_by_file"])
    assert "splunk.conf is not mapping" in combine_task["when"]
    assert combine_task["no_log"] == "{{ hide_password }}"


def test_writer_loop_uses_combined_entries_for_list_form():
    combined = combine(noah_entries(), SYSTEM_LOCAL)

    assert writer_loop_items({"conf": noah_entries()}, combined) == combined


@pytest.mark.parametrize("conf", [[], None])
def test_writer_loop_tolerates_empty_conf_without_combined_fact(conf):
    assert writer_loop_items({"conf": conf}) == conf


def test_writer_loop_keeps_dict_form_conf():
    dict_conf = {"server": {"content": {"general": {"serverName": "idx"}}}}

    assert writer_loop_items({"conf": dict_conf}, ["ignored"]) == [
        {"key": "server", "value": dict_conf["server"]},
    ]
