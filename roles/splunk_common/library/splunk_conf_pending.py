#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: splunk_conf_pending
short_description: Report which splunk.conf options ini_file would change
description:
  - Read-only. For each file, asks community.general's ini_file C(do_ini) in check mode
    whether each requested option would change, using the arguments
    set_config_stanza.yml passes to ini_file.
  - Returns stanza and option names only, never values. Empty stanzas are not reported.
  - A file is reported unsupported, so the caller writes it in full, when it is missing,
    not a regular file, a symlink, reached by more than one listed path, has a stanza or
    option that is not a plain name and single-line value, or the installed
    community.general is outside the supported range.
  - community.general must be importable by the Python this module runs with, as it is
    when Ansible and the configured host share an install, like the Splunk images.
    Otherwise every file is reported unsupported and written as before.
options:
  files:
    description: List of C(path) and C(stanzas) ({stanza: {option: value}}) to inspect.
    type: list
    elements: dict
    required: true
'''

RETURN = r'''
files:
  description: >-
    Per input path, C(supported), C(reason) and C(pending): a list of [stanza, options]
    pairs naming the options to write. Stanzas whose options all match are omitted.
  type: dict
summary:
  description: Counts of files, options and pending options, and elapsed seconds.
  type: dict
'''

import inspect
import json
import os
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.validation import check_type_str
from ansible.module_utils.six import integer_types, string_types

# do_ini is internal to ini_file, so only trust versions whose do_ini has been compared.
SUPPORTED_COMMUNITY_GENERAL = ((10, 0, 0), (12, 0, 0))

# Mirrors the ini_file arguments in set_config_stanza.yml plus ini_file's defaults.
DO_INI_ARGS = dict(
    state='present',
    exclusive=True,
    backup=False,
    no_extra_spaces=False,
    ignore_spaces=False,
    create=True,
    allow_no_value=False,
    modify_inactive_option=True,
    follow=False,
)


class Unsupported(Exception):
    pass


class ReadOnlyModule(object):
    check_mode = True
    _diff = False

    def fail_json(self, **kwargs):
        raise Unsupported('ini_file rejected the input: %s' % kwargs.get('msg'))


def parse_version(text):
    parts = []
    for part in text.split('.')[:3]:
        digits = ''
        for char in part:
            if not char.isdigit():
                break
            digits += char
        parts.append(int(digits or 0))
    return tuple(parts + [0] * (3 - len(parts)))


def load_do_ini():
    """Return (do_ini, None) or (None, reason)."""
    try:
        from ansible_collections.community.general.plugins.modules import ini_file
    except Exception as e:
        return None, 'cannot import community.general ini_file: %s' % e
    manifest = os.path.join(os.path.dirname(ini_file.__file__), '..', '..', 'MANIFEST.json')
    try:
        with open(manifest) as stream:
            version = json.load(stream)['collection_info']['version']
    except Exception as e:
        return None, 'cannot read community.general version: %s' % e
    low, high = SUPPORTED_COMMUNITY_GENERAL
    if not low <= parse_version(version) < high:
        return None, 'community.general %s is outside the supported range' % version
    getargspec = getattr(inspect, 'getfullargspec', None) or inspect.getargspec
    try:
        args = set(getargspec(ini_file.do_ini).args)
    except Exception as e:
        return None, 'cannot inspect do_ini: %s' % e
    missing = set(DO_INI_ARGS) | set(['section', 'option', 'values'])
    missing -= args
    if missing:
        return None, 'do_ini lacks arguments: %s' % ', '.join(sorted(missing))
    return ini_file.do_ini, None


def survives_templating(text):
    # The writer passes names and values through "{{ ... }}", which turns '{'/'[' strings
    # into dicts/lists and evaluates Jinja markers, so ini_file would receive a different string.
    return not text.startswith(('{', '[')) and not any(m in text for m in ('{{', '{%', '{#'))


def plain_name(name):
    if not isinstance(name, string_types):
        return False
    return (bool(name) and name == name.strip() and '\n' not in name and '\r' not in name
            and survives_templating(name))


def plain_stanza(name):
    # ini_file matches a section by header prefix, so [s] also matches a [s]x] header.
    return plain_name(name) and ']' not in name


def plain_option(name):
    # ini_file matches other options' lines on '=' and on leading comment or section characters.
    return plain_name(name) and '=' not in name and not name.startswith(('#', ';', '['))


def plain_value(value):
    if value is None or not isinstance(value, string_types + integer_types + (float, bool)):
        return False
    text = check_type_str(value)
    return '\n' not in text and '\r' not in text and survives_templating(text)


def pending_options(do_ini, path, stanzas):
    # ini_file may write an unusual name or value into another option's line or section, which
    # changes what later options need, so such files are written in full and in order.
    for stanza, settings in stanzas.items():
        if not settings:
            continue
        if not plain_stanza(stanza) or not isinstance(settings, dict):
            raise Unsupported('unsupported stanza %r' % stanza)
        for option, value in settings.items():
            if not plain_option(option) or not plain_value(value):
                raise Unsupported('unsupported option %r in stanza %r' % (option, stanza))
    pending = []
    options = 0
    for stanza, settings in stanzas.items():
        if not settings:
            continue
        changed_options = []
        for option, value in settings.items():
            options += 1
            changed = do_ini(
                ReadOnlyModule(), path,
                section=stanza, option=option, values=[check_type_str(value)], **DO_INI_ARGS
            )[0]
            if changed:
                changed_options.append(option)
        if changed_options:
            pending.append([stanza, changed_options])
    return pending, options


def inspect_file(do_ini, path, stanzas):
    if not isinstance(stanzas, dict):
        return None, 'stanzas is not a mapping', 0
    if os.path.islink(path):
        return None, 'symlink', 0
    if not os.path.exists(path):
        return None, 'missing', 0
    if not os.path.isfile(path):
        return None, 'not a regular file', 0
    try:
        pending, options = pending_options(do_ini, path, stanzas)
    except Unsupported as e:
        return None, str(e), 0
    except Exception as e:
        return None, 'inspection failed: %s: %s' % (type(e).__name__, e), 0
    return pending, None, options


def main():
    module = AnsibleModule(
        argument_spec=dict(
            files=dict(type='list', elements='dict', required=True),
        ),
        supports_check_mode=True,
    )
    start = time.time()
    requested = module.params['files']
    # ini_file's path argument is type='path', which expands these.
    paths = [os.path.expanduser(os.path.expandvars(f.get('path') or '')) for f in requested]
    # Two entries for one file, even through a symlinked directory, each need the other's writes.
    real_paths = [os.path.realpath(path) for path in paths]
    do_ini, unsupported_reason = load_do_ini()

    files = {}
    summary = dict(files=len(requested), supported_files=0, options=0, pending_options=0)
    for path, real_path, entry in zip(paths, real_paths, requested):
        if real_paths.count(real_path) > 1:
            pending, reason, options = None, 'reached by more than one listed path', 0
        elif do_ini is None:
            pending, reason, options = None, unsupported_reason, 0
        else:
            pending, reason, options = inspect_file(do_ini, path, entry.get('stanzas'))
        files[entry.get('path')] = dict(supported=pending is not None, reason=reason, pending=pending or [])
        if pending is not None:
            summary['supported_files'] += 1
            summary['options'] += options
            summary['pending_options'] += sum(len(names) for _, names in pending)
    summary['elapsed'] = round(time.time() - start, 3)
    module.exit_json(changed=False, files=files, summary=summary)


if __name__ == '__main__':
    main()
