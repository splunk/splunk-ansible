"""Edit Splunk configuration without translating Windows ACLs to POSIX modes.

The installed ini_file implementation remains the INI parser.  Its check-mode
planner runs against an in-memory view; only the native Windows backend writes
the resulting bytes.  Other platforms retain the original module behavior.
"""
from __future__ import absolute_import, division, print_function

import base64
import importlib.util
import inspect
import io
import os
import types

from ansible.errors import AnsibleError
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.plugins.action import ActionBase
from ansible.plugins.loader import module_loader


_INI_MODULES = {}
_ATTRIBUTES = frozenset(("owner", "group", "mode"))


def _reject_unknown(arguments, supported):
    unknown = sorted(set(arguments) - set(supported) - _ATTRIBUTES)
    if unknown:
        raise ValueError("Unsupported Windows configuration arguments: %s" % ", ".join(unknown))


def _as_bool(value):
    return boolean(value, strict=True)


def _target_path(arguments):
    path = arguments.get("path", arguments.get("dest"))
    if not isinstance(path, str) or not path:
        raise ValueError("A nonempty configuration path is required")
    if arguments.get("path") and arguments.get("dest") and arguments["path"] != arguments["dest"]:
        raise ValueError("path and dest must identify the same configuration file")
    return path


def _load_ini_planner(collection_list=None):
    """Resolve the installed module instead of depending on a collection version."""
    context = module_loader.find_plugin_with_context("ini_file", collection_list=collection_list)
    if not context.resolved:
        context = module_loader.find_plugin_with_context("community.general.ini_file", collection_list=collection_list)
    path = context.plugin_resolved_path
    if not context.resolved or not path:
        raise ValueError("The installed ini_file module could not be resolved")
    if path not in _INI_MODULES:
        spec = importlib.util.spec_from_file_location("_splunk_config_ini_file", path)
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        if not hasattr(loaded, "do_ini"):
            raise ValueError("The installed ini_file module has no compatible planner")
        _INI_MODULES[path] = loaded.do_ini
    return _INI_MODULES[path]


class _MemoryPath(object):
    def __init__(self, path, exists):
        self._path = path
        self._exists = exists

    def exists(self, path):
        return self._exists if path == self._path else True

    def islink(self, path):
        return False

    def __getattr__(self, name):
        if name in ("dirname", "basename", "abspath", "join", "normpath", "normcase", "split", "splitext", "isabs", "expanduser"):
            return getattr(os.path, name)
        raise ValueError("INI planning attempted a filesystem operation: path.%s" % name)


class _MemoryOS(object):
    def __init__(self, path, exists):
        self.path = _MemoryPath(path, exists)

    def __getattr__(self, name):
        raise ValueError("INI planning attempted a filesystem operation: %s" % name)


class _MemoryIO(object):
    def __init__(self, path, content):
        self._path = path
        self._content = content

    def open(self, path, mode="r", **kwargs):
        if path != self._path or mode != "r":
            raise ValueError("INI planning attempted an unexpected file access")
        # Match io.open(..., encoding='utf-8-sig') and universal newlines.
        return io.StringIO(self._content.decode("utf-8-sig"), newline=None)


class _PlannerModule(object):
    check_mode = True
    _diff = True

    def __init__(self, parameters):
        self.params = parameters

    def fail_json(self, **kwargs):
        raise ValueError(kwargs.get("msg", "INI planning failed"))


def plan_ini(content, exists, arguments, planner=None, collection_list=None):
    """Return the installed ini_file module's planned content without file I/O."""
    _reject_unknown(arguments, (
        "path", "dest", "section", "option", "value", "values", "state",
        "allow_no_value", "no_extra_spaces", "create", "backup", "exclusive",
        "ignore_spaces", "follow",
    ))
    path = _target_path(arguments)
    defaults = {
        "section": None, "option": None, "value": None, "values": None,
        "state": "present", "allow_no_value": False, "no_extra_spaces": False,
        "create": True, "backup": False, "exclusive": True,
        "ignore_spaces": False, "follow": False,
        "section_has_values": None, "modify_inactive_option": True,
    }
    parameters = dict(defaults)
    parameters.update({key: value for key, value in arguments.items() if key in defaults})
    for key in ("allow_no_value", "no_extra_spaces", "create", "backup", "exclusive", "ignore_spaces", "follow"):
        parameters[key] = _as_bool(parameters[key])
    if parameters["state"] not in ("present", "absent"):
        raise ValueError("INI state must be present or absent")
    if parameters["backup"] or parameters["follow"]:
        raise ValueError("Windows configuration does not support backup or follow")
    if parameters["value"] is not None and parameters["values"] is not None:
        raise ValueError("value and values are mutually exclusive")
    values = parameters["values"]
    if values is not None and not isinstance(values, (list, tuple)):
        raise ValueError("values must be a list")
    if parameters["value"] is not None:
        parameters["value"] = to_text(parameters["value"])
        values = [parameters["value"]]
    elif values is None:
        values = []
    else:
        values = [to_text(value) for value in values]
    if parameters["state"] == "present" and not parameters["allow_no_value"] and not values:
        raise ValueError("value(s) must be defined for an INI option")
    parameters["values"] = values

    planner = planner or _load_ini_planner(collection_list)
    globals_copy = dict(planner.__globals__)
    memory_io = _MemoryIO(path, content)
    globals_copy.update(os=_MemoryOS(path, exists), io=memory_io, open=memory_io.open,
                        tempfile=_MemoryOS(path, exists))
    memory_planner = types.FunctionType(
        planner.__code__, globals_copy, planner.__name__, planner.__defaults__, planner.__closure__)
    memory_planner.__kwdefaults__ = planner.__kwdefaults__
    signature = inspect.signature(planner)
    kwargs = {}
    for name in signature.parameters:
        if name in ("module", "filename"):
            continue
        if name == "value":
            if len(values) > 1:
                raise ValueError("The installed INI planner does not support multiple values")
            kwargs[name] = values[0] if values else None
        elif name == "values":
            kwargs[name] = values
        elif name in parameters:
            kwargs[name] = parameters[name]
        elif signature.parameters[name].default is inspect.Parameter.empty:
            raise ValueError("The installed INI planner requires an unsupported argument: %s" % name)
    changed, unused_backup, diff, message = memory_planner(_PlannerModule(parameters), path, **kwargs)
    if "after" not in diff:
        raise ValueError("The installed INI planner did not return the planned content")
    return {"changed": changed, "content": diff["after"].encode("utf-8"), "diff": diff, "msg": message}


def plan_line(content, exists, arguments):
    """Implement the exact-line append used for header-only configuration stanzas."""
    _reject_unknown(arguments, ("path", "dest", "line", "state", "create"))
    path = _target_path(arguments)
    if arguments.get("state", "present") != "present":
        raise ValueError("Windows configuration line edits support state=present only")
    if not exists and not _as_bool(arguments.get("create", False)):
        raise ValueError("The configuration file does not exist and create is false")
    line = arguments.get("line")
    if not isinstance(line, str) or "\n" in line or "\r" in line:
        raise ValueError("A single configuration line is required")
    encoded = line.encode("utf-8")
    changed = not any(existing.rstrip(b"\r\n") == encoded for existing in io.BytesIO(content).readlines())
    after = content
    if changed:
        if after and not after.endswith(b"\n"):
            after += b"\n"
        after += encoded + b"\n"
    return {
        "changed": changed, "content": after,
        "diff": {"before": content.decode("utf-8"), "after": after.decode("utf-8"),
                 "before_header": path, "after_header": path},
        "msg": "line added" if changed else "",
    }


def plan_copy(content, exists, arguments):
    _reject_unknown(arguments, ("path", "dest", "content"))
    path = _target_path(arguments)
    desired = arguments.get("content")
    if not isinstance(desired, str):
        raise ValueError("Windows configuration copy requires text content")
    after = desired.encode("utf-8")
    return {
        "changed": not exists or content != after, "content": after,
        "diff": {"before": content.decode("utf-8"), "after": desired,
                 "before_header": path, "after_header": path},
        "msg": "",
    }


def _public_result(result):
    # Read responses and module invocation arguments can contain complete configs.
    allowed = ("changed", "failed", "msg", "exists", "sha256", "security_hash",
               "warnings", "skipped", "skip_reason", "error_line", "error_code")
    return {key: value for key, value in result.items() if key in allowed}


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def _backend(self, operation, arguments, task_vars, **kwargs):
        backend_args = {"operation": operation, "path": _target_path(arguments), "home": self._task.args["home"]}
        backend_args.update(kwargs)
        return self._execute_module(module_name="splunk_windows_config", module_args=backend_args, task_vars=task_vars)

    def _original_copy(self, arguments, tmp, task_vars):
        task = self._task.copy()
        task.action = "copy"
        task.args = arguments
        action = self._shared_loader_obj.action_loader.get(
            "copy", task=task, connection=self._connection,
            play_context=self._play_context, loader=self._loader, templar=self._templar,
            shared_loader_obj=self._shared_loader_obj)
        return action.run(tmp=tmp, task_vars=task_vars)

    def run(self, tmp=None, task_vars=None):
        task_vars = task_vars or {}
        result = super(ActionModule, self).run(tmp, task_vars)
        arguments = dict(self._task.args)
        module = arguments.pop("module", None)
        home = arguments.pop("home", None)
        if module not in ("ini_file", "lineinfile", "file", "copy"):
            raise AnsibleError("splunk_config requires module=ini_file, lineinfile, file or copy")
        system = task_vars.get("ansible_system", task_vars.get("ansible_facts", {}).get("system", "")) or ""
        if system != "Win32NT" and not system.startswith("CYGWIN"):
            if module == "copy":
                result.update(self._original_copy(arguments, tmp, task_vars))
            else:
                result.update(self._execute_module(module_name=module, module_args=arguments, task_vars=task_vars, tmp=tmp))
            return result

        try:
            if not isinstance(home, str) or not home:
                raise ValueError("Windows configuration requires the Splunk home directory")
            if module == "file":
                _reject_unknown(arguments, ("path", "dest", "state"))
                state = arguments.get("state", "file")
                operations = {"file": "attributes", "directory": "directory", "absent": "absent"}
                if state not in operations:
                    raise ValueError("Unsupported Windows configuration file state: %s" % state)
                result.update(_public_result(self._backend(operations[state], arguments, task_vars)))
                return result

            read = self._backend("read", arguments, task_vars)
            if read.get("failed"):
                result.update(_public_result(read))
                return result
            exists = read.get("exists", False)
            content = base64.b64decode(read.get("content_b64", ""), validate=True)
            if exists and not read.get("sha256"):
                raise ValueError("The native configuration read did not provide a content hash")
            if module == "ini_file":
                plan = plan_ini(content, exists, arguments, collection_list=self._task.collections)
            elif module == "lineinfile":
                plan = plan_line(content, exists, arguments)
            else:
                plan = plan_copy(content, exists, arguments)
            if plan["changed"]:
                write = self._backend(
                    "write", arguments, task_vars,
                    content_b64=base64.b64encode(plan["content"]).decode("ascii"),
                    expected_sha256=read.get("sha256") if exists else None,
                    expected_absent=not exists)
                result.update(_public_result(write))
                if write.get("failed"):
                    return result
            else:
                result.update(changed=False, exists=exists)
            result.update(path=_target_path(arguments), msg=plan["msg"])
            if self._task.diff and not self._task.no_log and plan["changed"]:
                result["diff"] = plan["diff"]
            return result
        except UnicodeError:
            result.update(failed=True, changed=False, msg="Windows configuration content must be valid UTF-8")
            return result
        except (ValueError, TypeError, OSError) as error:
            result.update(failed=True, changed=False, msg="Windows configuration edit failed: %s" % to_text(error))
            return result
