#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Native Windows configuration I/O for Cygwin-managed Splunk installations.

The embedded program is fixed code. Configuration content travels only through
stdin, and native files receive their security descriptor before any bytes are
written. Existing files retain their owner, group and discretionary ACL.
"""
from __future__ import absolute_import, division, print_function

import base64
import json
import re
import sys

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r'''
module: splunk_windows_config
short_description: Read and securely commit Splunk configuration on Windows
description:
  - Internal backend for the Windows configuration action plugin.
  - Uses native Windows security descriptors rather than Cygwin POSIX modes.
  - Destinations must be regular files or directories inside C(home).
  - Existing files retain their owner, group and discretionary ACL.
  - New files and directories grant access only to trusted provisioning and
    installed Splunk service identities, SYSTEM, and Administrators.
options:
  operation:
    type: str
    required: true
    choices: [read, write, directory, attributes, absent]
  path:
    type: path
    required: true
  home:
    type: path
    required: true
  content_b64:
    type: str
    description: Base64-encoded replacement bytes, supplied only for write.
  expected_sha256:
    type: str
    description: Expected existing content hash, guarding against stale plans.
  expected_absent:
    type: bool
    default: false
    description: Require the destination to remain absent before creation.
'''


# .NET Framework is available in Windows PowerShell 5.1. The FileStream
# FileSecurity constructor applies its descriptor at creation. ReplaceFile
# preserves DACLs; owner/group are also cloned and checked before publication.
# https://learn.microsoft.com/dotnet/api/system.io.filestream.-ctor
# https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-replacefilew
POWERSHELL = r'''
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$script:sections = [Security.AccessControl.AccessControlSections]::Owner -bor
    [Security.AccessControl.AccessControlSections]::Group -bor
    [Security.AccessControl.AccessControlSections]::Access
$temp = $null
$stream = $null
$committed = $false
$stage = "validate request"
function Sha([byte[]]$bytes) {
    $h = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($h.ComputeHash($bytes)).Replace("-", "").ToLowerInvariant() }
    finally { $h.Dispose() }
}
function SecurityText([string]$p) {
    $acl=[IO.File]::GetAccessControl($p, $script:sections)
    $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
    if (-not $raw.DiscretionaryAcl) { throw "A configuration file must have a discretionary ACL" }
    $bytes=[byte[]]::new($raw.DiscretionaryAcl.BinaryLength)
    $raw.DiscretionaryAcl.GetBinaryForm($bytes,0)
    # ReplaceFile may update the auto-inherited bookkeeping flag. Compare the
    # actual owner/group, exact ACL bytes and inheritance protection instead.
    return $raw.Owner.Value+"|"+$raw.Group.Value+"|"+$acl.AreAccessRulesProtected+"|"+[Convert]::ToBase64String($bytes)
}
function Inspect([string]$p) {
    if ([IO.Directory]::Exists($p)) { throw "Expected a regular configuration file" }
    if (-not [IO.File]::Exists($p)) { return @{ exists=$false; content_b64=""; sha256=$null; security_hash=$null } }
    $data = [IO.File]::ReadAllBytes($p)
    $sddl = SecurityText $p
    return @{ exists=$true; content_b64=[Convert]::ToBase64String($data); sha256=(Sha $data);
        security_hash=(Sha ([Text.Encoding]::UTF8.GetBytes($sddl))) }
}
function CheckChain([string]$p) {
    $cursor = $p
    while ($cursor) {
        try {
            $a = [IO.File]::GetAttributes($cursor)
            if (($a -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse points are unsupported for Windows configuration" }
        } catch {
            $e=$_.Exception
            while ($e.InnerException) { $e=$e.InnerException }
            if (-not ($e -is [IO.FileNotFoundException] -or $e -is [IO.DirectoryNotFoundException])) { throw }
        }
        $parent = [IO.Path]::GetDirectoryName($cursor)
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}
function ServiceSids([string]$SplunkConfigHome) {
    $wanted = [IO.Path]::Combine($SplunkConfigHome, "bin\splunkd.exe")
    $found = @()
    foreach ($name in @("Splunkd", "SplunkForwarder")) {
        $key = "Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\" + $name
        if (-not (Test-Path -LiteralPath $key)) { continue }
        $v = Get-ItemProperty -LiteralPath $key
        $image = [Environment]::ExpandEnvironmentVariables([string]$v.ImagePath)
        if ($image -match '^\s*"([^"]+)"') { $exe = $matches[1] }
        elseif ($image -match '^\s*(.+?\.exe)(?:\s|$)') { $exe = $matches[1] }
        else { continue }
        if (-not [IO.Path]::GetFullPath($exe).Equals($wanted, [StringComparison]::OrdinalIgnoreCase)) { continue }
        $account = [string]$v.ObjectName
        if ($account -eq "LocalSystem") { $account = "NT AUTHORITY\SYSTEM" }
        elseif ($account -eq "NT AUTHORITY\LocalService") { $account = "NT AUTHORITY\LOCAL SERVICE" }
        elseif ($account -eq "NT AUTHORITY\NetworkService") { $account = "NT AUTHORITY\NETWORK SERVICE" }
        elseif ($account.StartsWith(".\")) { $account = $env:COMPUTERNAME + $account.Substring(1) }
        if (-not $account) { throw "Cannot resolve the installed Splunk service identity" }
        $found += ([Security.Principal.NTAccount]::new($account)).Translate([Security.Principal.SecurityIdentifier]).Value
        $found += ([Security.Principal.NTAccount]::new("NT SERVICE\" + $name)).Translate([Security.Principal.SecurityIdentifier]).Value
    }
    if (-not $found.Count) { throw "No installed Splunk service matches the configured home" }
    return @($found | Select-Object -Unique)
}
function NewSecurity([bool]$directory) {
    if ($directory) { $acl = [Security.AccessControl.DirectorySecurity]::new() }
    else { $acl = [Security.AccessControl.FileSecurity]::new() }
    $acl.SetAccessRuleProtection($true, $false)
    $current = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $trusted = @($current, "S-1-5-18", "S-1-5-32-544") | Select-Object -Unique
    $services = @(ServiceSids $script:SplunkConfigHome)
    foreach ($sidText in @($trusted + $services | Select-Object -Unique)) {
        $sid = [Security.Principal.SecurityIdentifier]::new($sidText)
        $rights = [Security.AccessControl.FileSystemRights]::Modify
        if ($trusted -contains $sidText) { $rights = [Security.AccessControl.FileSystemRights]::FullControl }
        if ($directory) {
            $rule = [Security.AccessControl.FileSystemAccessRule]::new($sid, $rights,
                ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit),
                [Security.AccessControl.PropagationFlags]::None, [Security.AccessControl.AccessControlType]::Allow)
        } else {
            $rule = [Security.AccessControl.FileSystemAccessRule]::new($sid, $rights, [Security.AccessControl.AccessControlType]::Allow)
        }
        [void]$acl.AddAccessRule($rule)
    }
    return $acl
}
function EnsureDirectory([string]$p) {
    CheckChain $p
    if ([IO.File]::Exists($p)) { throw "Expected a configuration directory" }
    if ([IO.Directory]::Exists($p)) { return }
    $missing = @()
    $cursor = $p
    while (-not [IO.Directory]::Exists($cursor)) {
        if ([IO.File]::Exists($cursor)) { throw "A configuration parent is not a directory" }
        $missing += $cursor
        $cursor = [IO.Path]::GetDirectoryName($cursor)
        if (-not $cursor) { throw "Configuration directory has no existing parent" }
    }
    $acl = NewSecurity $true
    for ($i=$missing.Count-1; $i -ge 0; $i--) {
        CheckChain $missing[$i]
        [void][IO.Directory]::CreateDirectory($missing[$i], $acl)
    }
}
function EnableRestore {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class SplunkConfigPrivilege {
 [StructLayout(LayoutKind.Sequential)] struct Luid { public uint Low; public int High; }
 [StructLayout(LayoutKind.Sequential)] struct State { public uint Count; public Luid Id; public uint Flags; }
 [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
 [DllImport("kernel32.dll")] static extern IntPtr GetCurrentThread();
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 [DllImport("advapi32.dll", SetLastError=true)] static extern bool OpenProcessToken(IntPtr p,uint a,out IntPtr t);
 [DllImport("advapi32.dll", SetLastError=true)] static extern bool OpenThreadToken(IntPtr p,uint a,bool o,out IntPtr t);
 [DllImport("advapi32.dll", SetLastError=true)] static extern bool DuplicateTokenEx(IntPtr t,uint a,IntPtr s,int l,int k,out IntPtr n);
 [DllImport("advapi32.dll", SetLastError=true)] static extern bool SetThreadToken(IntPtr t,IntPtr n);
 [DllImport("advapi32.dll", SetLastError=true)] static extern bool RevertToSelf();
 [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool LookupPrivilegeValue(string s,string n,out Luid l);
 [DllImport("advapi32.dll", SetLastError=true)] static extern bool AdjustTokenPrivileges(IntPtr t,bool d,ref State s,uint z,out State p,out uint r);
 [DllImport("advapi32.dll", EntryPoint="AdjustTokenPrivileges", SetLastError=true)] static extern bool RestoreTokenPrivileges(IntPtr t,bool d,ref State s,uint z,IntPtr p,IntPtr r);
 static IntPtr token=IntPtr.Zero, priorThread=IntPtr.Zero;
 static State previous;
 static bool installed=false;
 public static bool Enable() {
  if(installed) return true;
  IntPtr source=IntPtr.Zero;
  try {
   if(OpenThreadToken(GetCurrentThread(),0xE,true,out priorThread)) source=priorThread;
   else {
    priorThread=IntPtr.Zero;
    if(Marshal.GetLastWin32Error()!=1008 || !OpenProcessToken(GetCurrentProcess(),0xA,out source)) return false;
   }
   if(!DuplicateTokenEx(source,0x2E,IntPtr.Zero,2,2,out token)) return false;
   Luid l; if(!LookupPrivilegeValue(null,"SeRestorePrivilege",out l)) return false;
   State s=new State { Count=1, Id=l, Flags=2 }; uint length;
   bool ok=AdjustTokenPrivileges(token,false,ref s,(uint)Marshal.SizeOf(typeof(State)),out previous,out length);
   if(!ok || Marshal.GetLastWin32Error()!=0) return false;
   if(!SetThreadToken(IntPtr.Zero,token)) return false;
   installed=true;
   return true;
  } finally {
   if(source!=IntPtr.Zero && source!=priorThread) CloseHandle(source);
   if(!installed) Restore();
  }
 }
 public static bool Restore() {
  bool ok=true;
  try {
   if(token!=IntPtr.Zero && previous.Count!=0) ok=RestoreTokenPrivileges(token,false,ref previous,0,IntPtr.Zero,IntPtr.Zero);
   if(installed) ok=(priorThread!=IntPtr.Zero ? SetThreadToken(IntPtr.Zero,priorThread) : RevertToSelf()) && ok;
   return ok;
  } finally {
   installed=false;
   if(token!=IntPtr.Zero) CloseHandle(token);
   if(priorThread!=IntPtr.Zero) CloseHandle(priorThread);
   token=IntPtr.Zero; priorThread=IntPtr.Zero; previous=new State();
  }
 }
}
"@
    return [SplunkConfigPrivilege]::Enable()
}
try {
    $r = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $script:SplunkConfigHome = [IO.Path]::GetFullPath([string]$r.home).TrimEnd("\")
    $p = [IO.Path]::GetFullPath([string]$r.path)
    if ($p -notmatch '^[A-Za-z]:\\' -or $script:SplunkConfigHome -notmatch '^[A-Za-z]:\\') { throw "Only local Windows drive paths are supported" }
    if ($p.Substring(2).Contains(":")) { throw "Alternate data streams are unsupported" }
    $inside = $p.StartsWith($script:SplunkConfigHome + "\", [StringComparison]::OrdinalIgnoreCase)
    if (-not $inside -and -not ($r.operation -eq "directory" -and $p.Equals($script:SplunkConfigHome, [StringComparison]::OrdinalIgnoreCase))) {
        throw "Windows configuration paths must be inside the configured Splunk home"
    }
    if (-not [IO.Directory]::Exists($script:SplunkConfigHome)) { throw "Configured Splunk home does not exist" }
    CheckChain $p
    $result = @{ changed=$false }
    if ($r.operation -eq "directory") {
        if ([IO.File]::Exists($p)) { throw "Expected a configuration directory" }
        $result.changed = -not [IO.Directory]::Exists($p)
        if ($result.changed -and $r.check_mode) { [void](NewSecurity $true) }
        if ($result.changed -and -not $r.check_mode) { $stage="create directory"; EnsureDirectory $p }
        $result.exists = [IO.Directory]::Exists($p)
    } else {
        $old = Inspect $p
        if ($r.expected_absent -and $old.exists) { throw "Configuration changed since it was read: destination now exists" }
        if ($r.expected_sha256 -and (-not $old.exists -or $old.sha256 -ne $r.expected_sha256)) { throw "Configuration changed since it was read: content hash differs" }
        if ($r.operation -eq "read") { $result=$old; $result.changed=$false }
        elseif ($r.operation -eq "attributes") {
            if (-not $old.exists) { throw "Configuration file does not exist" }
            $result.exists=$true; $result.security_hash=$old.security_hash
        } elseif ($r.operation -eq "absent") {
            if ([IO.Path]::GetFileName($p) -notmatch '^\..+\.splunk-ansible-managed\.yml$') { throw "Only configuration ownership receipts may be removed" }
            $result.changed=$old.exists
            if ($old.exists -and -not $r.check_mode) { $stage="remove receipt"; [IO.File]::Delete($p) }
            $result.exists=[IO.File]::Exists($p)
        } elseif ($r.operation -eq "write") {
            if (-not $r.expected_absent -and -not $r.expected_sha256) { throw "A write requires an expected content hash or expected absence" }
            $data=[Convert]::FromBase64String([string]$r.content_b64)
            $newHash=Sha $data
            $result.changed=(-not $old.exists -or $old.sha256 -ne $newHash)
            if ($result.changed -and -not $old.exists -and $r.check_mode) { [void](NewSecurity $false) }
            if ($result.changed -and -not $r.check_mode) {
                $stage="prepare native replacement"
                $parent=[IO.Path]::GetDirectoryName($p)
                EnsureDirectory $parent
                $before=$null
                if ($old.exists) {
                    $before=SecurityText $p
                    $acl=[IO.File]::GetAccessControl($p,$script:sections)
                    $enabled=EnableRestore
                    if (-not $enabled) {
                        throw "Cannot establish an isolated Windows ownership-preservation privilege scope"
                    }
                } else { $acl=NewSecurity $false }
                $temp=[IO.Path]::Combine($parent,".splunk-ansible-"+[Guid]::NewGuid().ToString("N")+".tmp")
                $stream=[IO.FileStream]::new($temp,[IO.FileMode]::CreateNew,
                    [Security.AccessControl.FileSystemRights]::FullControl,[IO.FileShare]::None,4096,
                    [IO.FileOptions]::WriteThrough,$acl)
                $stream.Dispose(); $stream=$null
                if ($old.exists -and (SecurityText $temp) -ne $before) { throw "Native replacement did not preserve the original security descriptor" }
                $stream=[IO.FileStream]::new($temp,[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::None)
                $stream.Write($data,0,$data.Length); $stream.Flush($true); $stream.Dispose(); $stream=$null
                $stage="commit native replacement"
                CheckChain $p
                $now=Inspect $p
                if ($old.exists) {
                    if (-not $now.exists -or $now.sha256 -ne $old.sha256 -or (SecurityText $p) -ne $before) { throw "Configuration changed while its replacement was prepared" }
                    [IO.File]::Replace($temp,$p,[NullString]::Value,$false)
                    $committed=$true
                    $temp=$null
                    if ((SecurityText $p) -ne $before) { throw "Native replacement changed file security" }
                } else {
                    if ($now.exists) { throw "Configuration appeared while its replacement was prepared" }
                    [IO.File]::Move($temp,$p); $temp=$null
                    $committed=$true
                }
            }
            $result.exists=[IO.File]::Exists($p); $result.sha256=$newHash
            if ($result.exists) { $result.security_hash=(Inspect $p).security_hash }
        } else { throw "Unsupported configuration operation" }
    }
    if ("SplunkConfigPrivilege" -as [type]) {
        $stage="restore native privilege"
        if (-not [SplunkConfigPrivilege]::Restore()) { throw "Cannot restore the original Windows privilege state" }
    }
    $result | ConvertTo-Json -Compress -Depth 5
} catch {
    @{ failed=$true; changed=$committed; error_line=$_.InvocationInfo.ScriptLineNumber;
        error_code=$_.Exception.HResult; msg=("Native Windows configuration failed during "+$stage+
        " ("+$_.Exception.GetType().Name+", error "+$_.Exception.HResult+")") } | ConvertTo-Json -Compress
    exit 1
} finally {
    try {
        if ($stream) { $stream.Dispose() }
        if ($temp -and [IO.File]::Exists($temp)) { [IO.File]::Delete($temp) }
    } finally {
        if ("SplunkConfigPrivilege" -as [type]) { [void][SplunkConfigPrivilege]::Restore() }
    }
}
'''


def native_path(module, value):
    """Translate Cygwin paths without changing native Windows drive paths."""
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return value
    if not sys.platform.startswith("cygwin"):
        module.fail_json(msg="splunk_windows_config requires Windows or Cygwin")
    binary = module.get_bin_path("cygpath", required=True)
    rc, out, _ = module.run_command([binary, "-aw", "--", value])
    if rc or not out.strip():
        module.fail_json(msg="Cannot translate the Windows configuration path")
    return out.strip()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            operation=dict(type="str", required=True,
                           choices=["read", "write", "directory", "attributes", "absent"]),
            path=dict(type="path", required=True),
            home=dict(type="path", required=True),
            content_b64=dict(type="str", no_log=True),
            expected_sha256=dict(type="str"),
            expected_absent=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )
    request = dict(module.params)
    expected = request.get("expected_sha256")
    if expected and not re.match(r"^[a-fA-F0-9]{64}$", expected):
        module.fail_json(msg="expected_sha256 must be a SHA256 hex digest")
    if request["operation"] == "write" and request.get("content_b64") is None:
        module.fail_json(msg="content_b64 is required for writes")
    request["path"] = native_path(module, request["path"])
    request["home"] = native_path(module, request["home"])
    request["check_mode"] = module.check_mode
    powershell = module.get_bin_path("powershell.exe", required=True)
    # Keep CreateProcess's command line short. Fixed helper code is the first
    # stdin line; the second line contains the JSON request. Neither is stored.
    bootstrap = (
        "$s=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("
        "[Console]::In.ReadLine())); & ([ScriptBlock]::Create($s))"
    )
    encoded = base64.b64encode(bootstrap.encode("utf-16-le")).decode("ascii")
    program = base64.b64encode(POWERSHELL.encode("utf-8")).decode("ascii")
    rc, out, _ = module.run_command(
        [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        data=program + "\n" + json.dumps(request),
    )
    try:
        result = json.loads(out.lstrip("\ufeff").strip())
    except (TypeError, ValueError):
        module.fail_json(msg="Native Windows configuration helper returned an invalid response")
    if not isinstance(result, dict):
        module.fail_json(msg="Native Windows configuration helper returned an invalid response")
    if rc or result.get("failed"):
        module.fail_json(changed=result.get("changed", False),
                         msg=result.get("msg", "Native Windows configuration operation failed"),
                         error_line=result.get("error_line"),
                         error_code=result.get("error_code"))
    if request["operation"] == "read":
        result["_ansible_no_log"] = True
    module.exit_json(**result)


if __name__ == "__main__":
    main()
