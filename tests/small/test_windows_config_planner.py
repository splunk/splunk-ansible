"""Configuration planning stays in memory and uses the installed INI semantics."""
import base64
import builtins
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from ansible.plugins.action import ActionBase
from ansible_collections.community.general.plugins.modules import ini_file


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("splunk_config_action", ROOT / "action_plugins" / "splunk_config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
PATH = "/opt/splunk/etc/system/local/server.conf"


def ini_arguments(**kwargs):
    arguments = {"path": PATH, "section": "general", "option": "name", "value": "new"}
    arguments.update(kwargs)
    return arguments


def plan(content, exists=True, **kwargs):
    return config.plan_ini(content, exists, ini_arguments(**kwargs), planner=ini_file.do_ini)


def test_ini_preserves_comments_other_sections_and_unicode():
    before = "; keep this\n[general]\nname=old\n# untouched\n[other]\ncity=東京\n".encode()
    result = plan(before, value="München")
    assert result["changed"]
    assert result["content"] == "; keep this\n[general]\nname = München\n# untouched\n[other]\ncity=東京\n".encode()
    assert not plan(result["content"], value="München")["changed"]


def test_ini_duplicate_options_follow_installed_exclusive_semantics():
    result = plan(b"[general]\nname=first\nname=second\n[other]\nname=keep\n")
    assert result["content"].count(b"name = new") == 1
    assert b"name=first" not in result["content"]
    assert b"name=second" not in result["content"]
    assert b"[other]\nname=keep\n" in result["content"]


def test_ini_duplicate_sections_follow_installed_parser():
    result = plan(b"[general]\nname=first\n[other]\nx=1\n[general]\nname=second\n")
    assert b"name=first" not in result["content"]
    assert b"[general]\nname=second\n" in result["content"]
    assert b"[other]\nx=1\n" in result["content"]
    assert not plan(result["content"])["changed"]


def test_ini_absent_removes_only_requested_option():
    result = plan(b"[general]\nname=old\nkeep=yes\n[other]\nname=other\n", state="absent", value=None)
    assert result["content"] == b"[general]\nkeep=yes\n[other]\nname=other\n"
    assert not plan(result["content"], state="absent", value=None)["changed"]


@pytest.mark.parametrize("before", [b"", b"[other]\nx=1", b"[general]\nname=old\n"])
def test_ini_creates_and_repeats_without_extra_changes(before):
    result = plan(before, exists=bool(before))
    assert b"[general]\n" in result["content"]
    assert b"name = new\n" in result["content"]
    assert not plan(result["content"])["changed"]


def test_ini_normalizes_bom_and_crlf_only_when_it_changes_content():
    before = b"\xef\xbb\xbf[general]\r\nname=old\r\n"
    result = plan(before)
    assert result["content"] == b"[general]\nname = new\n"
    assert not plan(b"[general]\r\nname = new\r\n")["changed"]


def test_ini_planner_cannot_read_or_write_real_files(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("The planner accessed the filesystem")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(ini_file.io, "open", forbidden)
    monkeypatch.setattr(ini_file.tempfile, "mkstemp", forbidden)
    result = plan(b"[general]\nname=old\n")
    assert result["content"] == b"[general]\nname = new\n"


def test_legacy_value_signature_is_supported_without_io():
    # Ansible 2.10 images include this older signature instead of values=[...].
    def legacy(module, filename, section=None, option=None, value=None, state="present",
               backup=False, no_extra_spaces=False, create=True, allow_no_value=False):
        with io.open(filename, "r", encoding="utf-8-sig") as stream:
            before = stream.read()
        after = before + "[%s]\n%s = %s\n" % (section, option, value)
        assert module.check_mode and module._diff
        return True, None, {"before": before, "after": after}, "option added"

    # This name is deliberately bound in the function globals and replaced by
    # plan_ini's memory facade, rather than opening a real fixture file.
    legacy.__globals__["io"] = __import__("io")
    result = config.plan_ini(b"; comment\n", True, ini_arguments(value="雪"), planner=legacy)
    assert result["content"] == "; comment\n[general]\nname = 雪\n".encode()


@pytest.mark.parametrize("extra", [
    {"backup": True}, {"follow": True}, {"unsafe_writes": True},
    {"regexp": "name=.*"}, {"value": None}, {"create": False},
])
def test_ini_rejects_unsupported_or_invalid_requests(extra):
    with pytest.raises(ValueError):
        config.plan_ini(b"", False, ini_arguments(**extra), planner=ini_file.do_ini)


def test_line_adds_empty_stanza_once_and_preserves_other_bytes():
    arguments = {"path": PATH, "line": "[empty]", "create": True, "mode": "0660"}
    result = config.plan_line(b"; keep\r\n[general]\r\nx=1", True, arguments)
    assert result["content"] == b"; keep\r\n[general]\r\nx=1\n[empty]\n"
    assert not config.plan_line(result["content"], True, arguments)["changed"]


def test_line_creates_header_only_file():
    result = config.plan_line(b"", False, {"path": PATH, "line": "[empty]", "create": True})
    assert result["content"] == b"[empty]\n"


@pytest.mark.parametrize("extra", [{"regexp": ".*"}, {"state": "absent"}, {"line": "a\nb"}])
def test_line_rejects_semantics_it_does_not_implement(extra):
    arguments = {"path": PATH, "line": "[empty]", "create": True}
    arguments.update(extra)
    with pytest.raises(ValueError):
        config.plan_line(b"", False, arguments)


def test_receipt_copy_compares_exact_utf8_content():
    arguments = {"dest": PATH, "content": "general:\n  name: 雪\n", "mode": "0660"}
    result = config.plan_copy(b"", False, arguments)
    assert result["content"] == arguments["content"].encode()
    assert not config.plan_copy(result["content"], True, arguments)["changed"]
    assert config.plan_copy(b"", False, {"path": PATH, "content": ""})["changed"]


def action(monkeypatch, module="ini_file", arguments=None, diff=False, no_log=False, exists=True, before=b"[general]\nname=old\n"):
    monkeypatch.setattr(ActionBase, "run", lambda *args, **kwargs: {})
    monkeypatch.setattr(config, "_load_ini_planner", lambda *args: ini_file.do_ini)
    instance = object.__new__(config.ActionModule)
    task_arguments = {"module": module, "home": "/opt/splunk"}
    task_arguments.update(arguments or ini_arguments())
    instance._task = SimpleNamespace(args=task_arguments, collections=[], diff=diff, no_log=no_log)
    read = {"exists": exists, "content_b64": base64.b64encode(before).decode(), "sha256": "original-hash", "_ansible_no_log": True}
    instance._execute_module = Mock(side_effect=[read, {"changed": True, "exists": True, "sha256": "new-hash"}])
    return instance


def test_windows_action_uses_native_read_then_guarded_write(monkeypatch):
    instance = action(monkeypatch)
    result = instance.run(task_vars={"ansible_system": "CYGWIN_NT-10.0-20348"})
    calls = instance._execute_module.call_args_list
    assert calls[0].kwargs["module_args"]["operation"] == "read"
    write = calls[1].kwargs["module_args"]
    assert write["operation"] == "write"
    assert write["expected_sha256"] == "original-hash"
    assert write["expected_absent"] is False
    assert base64.b64decode(write["content_b64"]) == b"[general]\nname = new\n"
    assert result["changed"] and "diff" not in result
    assert "content_b64" not in result and "_ansible_no_log" not in result


def test_windows_action_preserves_raw_bytes_on_noop(monkeypatch):
    before = b"[general]\r\nname = new\r\n"
    instance = action(monkeypatch, before=before)
    result = instance.run(task_vars={"ansible_system": "Win32NT"})
    assert not result["changed"]
    assert instance._execute_module.call_count == 1


def test_windows_action_checks_absence_on_creation(monkeypatch):
    instance = action(monkeypatch, before=b"", exists=False)
    assert instance.run(task_vars={"ansible_system": "Win32NT"})["changed"]
    write = instance._execute_module.call_args_list[1].kwargs["module_args"]
    assert write["expected_absent"] is True and write["expected_sha256"] is None


@pytest.mark.parametrize("diff,no_log,has_diff", [(False, False, False), (True, False, True), (True, True, False)])
def test_action_exposes_diff_only_when_requested_and_not_secret(monkeypatch, diff, no_log, has_diff):
    instance = action(monkeypatch, arguments=ini_arguments(value="supersecret"), diff=diff, no_log=no_log)
    result = instance.run(task_vars={"ansible_system": "Win32NT"})
    assert ("diff" in result) is has_diff
    if not has_diff:
        assert "supersecret" not in repr(result)


def test_action_keeps_native_write_failure_and_strips_private_fields(monkeypatch):
    instance = action(monkeypatch)
    instance._execute_module.side_effect = [
        {"exists": True, "content_b64": base64.b64encode(b"[general]\nname=old\n").decode(), "sha256": "old"},
        {"failed": True, "changed": False, "msg": "Configuration changed concurrently", "content_b64": "private", "invocation": {"private": "data"}},
    ]
    result = instance.run(task_vars={"ansible_system": "Win32NT"})
    assert result["failed"]
    assert result["msg"] == "Configuration changed concurrently"
    assert "private" not in repr(result)


def test_action_rejects_a_read_without_a_stale_write_guard(monkeypatch):
    instance = action(monkeypatch)
    instance._execute_module.side_effect = [{"exists": True, "content_b64": ""}]
    result = instance.run(task_vars={"ansible_system": "Win32NT"})
    assert result["failed"] and not result["changed"]
    assert instance._execute_module.call_count == 1


def test_read_failures_and_invalid_utf8_do_not_expose_content(monkeypatch):
    instance = action(monkeypatch)
    instance._execute_module.side_effect = [{
        "failed": True, "msg": "Cannot read configuration", "content_b64": "supersecret",
        "stdout": "supersecret", "_ansible_no_log": True,
    }]
    result = instance.run(task_vars={"ansible_system": "Win32NT"})
    assert result["failed"] and "supersecret" not in repr(result)
    instance = action(monkeypatch, before=b"[general]\nname=supersecret\xff\n")
    result = instance.run(task_vars={"ansible_system": "Win32NT"})
    assert result["failed"] and "supersecret" not in repr(result)


@pytest.mark.parametrize("state,operation", [("file", "attributes"), ("directory", "directory"), ("absent", "absent")])
def test_windows_file_operations_never_send_posix_attributes(monkeypatch, state, operation):
    instance = action(monkeypatch, module="file", arguments={"path": PATH, "state": state, "owner": "SYSTEM", "group": "SYSTEM", "mode": "0660"})
    instance._execute_module.side_effect = None
    instance._execute_module.return_value = {"changed": False, "exists": state != "absent"}
    result = instance.run(task_vars={"ansible_system": "Win32NT"})
    assert not result["changed"]
    assert instance._execute_module.call_args.kwargs["module_args"] == {"operation": operation, "path": PATH, "home": "/opt/splunk"}


@pytest.mark.parametrize("system", ["Linux", "Darwin", ""])
def test_other_platforms_delegate_original_arguments(monkeypatch, system):
    arguments = ini_arguments(owner="splunk", group="splunk", mode="0660")
    instance = action(monkeypatch, arguments=arguments)
    instance._execute_module.side_effect = None
    instance._execute_module.return_value = {"changed": True}
    assert instance.run(task_vars={"ansible_system": system})["changed"]
    call = instance._execute_module.call_args.kwargs
    assert call["module_name"] == "ini_file" and call["module_args"] == arguments


def test_other_platform_copy_uses_original_action_for_content(monkeypatch):
    arguments = {"dest": PATH, "content": "receipt", "mode": "0660"}
    instance = action(monkeypatch, module="copy", arguments=arguments)
    instance._original_copy = Mock(return_value={"changed": True})
    assert instance.run(task_vars={"ansible_system": "Linux"})["changed"]
    instance._original_copy.assert_called_once_with(arguments, None, {"ansible_system": "Linux"})
    instance._execute_module.assert_not_called()
