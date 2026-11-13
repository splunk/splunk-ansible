#!/usr/bin/env python
"""Ansible filters that apply splunk_conf_pending results to splunk.conf entries."""

from __future__ import absolute_import

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

from ansible import constants as C
from ansible.module_utils.six import string_types


def conf_targets(entries, default_directory):
    """Return [{file, directory, path, stanzas}] for splunk.conf entries ({key, value})."""
    targets = []
    for entry in entries or []:
        value = entry.get("value")
        if not isinstance(value, Mapping):
            # Merging list-form splunk.conf into map-form leaves plain-string values; read them as empty.
            value = {}
        directory = value.get("directory") or default_directory
        conf_file = "{}.conf".format(entry["key"])
        targets.append({
            "file": conf_file,
            "directory": directory,
            "path": "{}/{}".format(directory, conf_file),
            "stanzas": value.get("content", {}),
        })
    return targets


def has_only_string_keys(stanzas):
    # Module arguments travel as JSON, which turns non-string keys into strings that
    # differ from what ini_file receives (True becomes "true"), so the probe can't vouch for them.
    for stanza, settings in stanzas.items():
        if not isinstance(stanza, string_types):
            return False
        if isinstance(settings, Mapping) and not all(isinstance(k, string_types) for k in settings):
            return False
    return True


def probed_pending(probe, path):
    """Return the probe's [[stanza, options]] for path, or None when it can't vouch for it."""
    # A killed module or invalid output leaves no files: failed_when: false masks the failure.
    result = (probe.get("files") or {}).get(path)
    if not result or not result["supported"]:
        return None
    return result["pending"]


def probe_supported(probe, path, stanzas):
    # Under jinja2_native the writer's "{{ value }}" coerces strings ('1.00' to 1.0) in ways
    # the probe does not model, so every option is written.
    return (
        not getattr(C, "DEFAULT_JINJA2_NATIVE", False)
        and isinstance(stanzas, Mapping)
        and has_only_string_keys(stanzas)
        and probed_pending(probe, path) is not None
    )


def pending_stanzas(stanzas, probe, path):
    """Return the part of stanzas the probe says ini_file would change; all of it if unsure."""
    if not probe_supported(probe, path, stanzas):
        return stanzas
    names = dict((item[0], item[1]) for item in probed_pending(probe, path))
    pending = {}
    for stanza, settings in stanzas.items():
        if not settings or not isinstance(settings, Mapping):
            pending[stanza] = settings
            continue
        if stanza in names:
            pending[stanza] = dict((k, v) for k, v in settings.items() if k in names[stanza])
    return pending


def probe_report(probe):
    """Summarise a probe result without any configuration values."""
    if "files" not in probe:
        return {"failed": True, "msg": probe.get("msg")}
    return {
        "summary": probe["summary"],
        "unsupported": dict(
            (path, result["reason"]) for path, result in probe["files"].items() if not result["supported"]
        ),
    }


class FilterModule(object):
    def filters(self):
        return {
            "splunk_conf_targets": conf_targets,
            "splunk_conf_pending_stanzas": pending_stanzas,
            "splunk_conf_probe_supported": probe_supported,
            "splunk_conf_probe_report": probe_report,
        }
