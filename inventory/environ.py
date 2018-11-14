#!/usr/bin/env python
# Copyright 2018 Splunk
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import platform
import json
import argparse
import re
import random
import string
import shutil
import sys
import urllib2
import yaml

HERE = os.path.dirname(os.path.normpath(__file__))
PLATFORM = platform.platform().lower()
DEFAULTS = {}
if "windows" in PLATFORM or "cygwin" in PLATFORM:
    PLATFORM = "windows"
else:
    PLATFORM = "linux"

ansibleDefaultsMapping = {
                            "windows": {
                                "SPLUNK_BUILD_URL": "C:\\\\splunk.msi"
                            },
                            "linux": {
                                "SPLUNK_BUILD_URL": "/tmp/splunk.tgz"
                            }
                        }

roleNames = [
    'splunk_cluster_master', # (if it exists, set up indexer clustering)
    'splunk_deployer',
    'splunk_heavy_forwarder',
    'splunk_standalone',
    'splunk_search_head',
    'splunk_indexer',
    'splunk_license_master', # (if it exists, run adding license with a license master)
    'splunk_search_head_captain', # (if it exists, set up search head clustering)
    'splunk_universal_forwarder'
]

varPrefix = "SPLUNK_VAR_"
reVarPrefix = r"${varPrefix}(.*)"
envPrefix = "SPLUNK_ROLE_"
reNamePattern = r"${envPrefix}(.*)"

inventory = {
    "_meta": {
        "hostvars": {}
    }
}

def getVars(rePattern):
    return { re.match(rePattern, k).group(1).lower():os.environ[k] for k in os.environ if re.match(rePattern, k) }

def getSplunkInventory(inventory, reName=r"(.*)_URL"):
    group_information = getVars(reName)
    for group_name in group_information:
        if group_name.lower() in roleNames:
            inventory[group_name] = {}
            hosts = [ host.strip() for host in group_information[group_name].split(',') ]
            inventory[group_name] = {
                'hosts': list([ host.split(':')[0] for host in hosts ])
            }
    getHostVars(inventory)

def getSplunkPassword():
    password = os.environ.get('SPLUNK_PASSWORD')
    if not password:
        if getValueFromDEFAULTS("splunk.password"):
            password = getValueFromDEFAULTS("splunk.password")
        else:
            print "Default password doesn't exist as environment variable or in a default.yml"
            sys.exit(1)
    return password

def getHostVars(inv):
    inv["all"] = {"vars": {"splunk": {}}}

    getDefaultSplunkVariables(inv)

    inv["all"]["vars"]["splunk"]["license_master_included"] = True if os.environ.get('SPLUNK_LICENSE_MASTER_URL', False) else False
    inv["all"]["vars"]["splunk"]["deployer_included"] = True if os.environ.get('SPLUNK_DEPLOYER_URL', False) else False
    inv["all"]["vars"]["splunk"]["indexer_cluster"] = True if os.environ.get('SPLUNK_CLUSTER_MASTER_URL', False) else False
    inv["all"]["vars"]["splunk"]["search_head_cluster"] = True if os.environ.get('SPLUNK_SEARCH_HEAD_CAPTAIN_URL', False) else False
    inv["all"]["vars"]["splunk"]["license_uri"] = os.environ.get('SPLUNK_LICENSE_URI', '')
    inv["all"]["vars"]["splunk"]["role"] = os.environ.get('SPLUNK_ROLE', 'splunk_standalone')

    getSplunkBuild(inv)
    getSplunkApps(inv)
    getUFSplunkVariables(inv)
    checkUpgrade(inv)

def getSplunkBuild(inv):
    location = os.environ.get("SPLUNK_BUILD_URL", ansibleDefaultsMapping[PLATFORM]["SPLUNK_BUILD_URL"])
    inv["all"]["vars"]["splunk"]["build_location"] = location
    if location and location.startswith("http"):
        inv["all"]["vars"]["splunk"]["build_remote_src"] = True
    else:
        inv["all"]["vars"]["splunk"]["build_remote_src"] = False

def getSplunkApps(inv):
    splunkbase_username = getValueFromDEFAULTS("splunkbase_username") or os.environ.get("SPLUNKBASE_USERNAME") or None
    splunkbase_password = getValueFromDEFAULTS("splunkbase_password") or os.environ.get("SPLUNKBASE_PASSWORD") or None
    if splunkbase_username and splunkbase_password:
        splunkbase_username = urllib2.quote(splunkbase_username)
        splunkbase_password = urllib2.quote(splunkbase_password)
        response = urllib2.urlopen("https://splunkbase.splunk.com/api/account:login/", "username={}&password={}".format(splunkbase_username, splunkbase_password))
        if response.getcode() != 200:
            raise Exception("Invalid Splunkbase credentials - will not download apps from Splunkbase")
        output = response.read()
        splunkbase_token = re.search("<id>(.*)</id>", output, re.IGNORECASE)
        inv["all"]["vars"]["splunkbase_token"] = splunkbase_token.group(1) if splunkbase_token else None
    apps = os.environ.get("SPLUNK_APPS_URL", None)
    if apps:
        inv["all"]["vars"]["splunk"]["apps_location"] = apps.split(",")
    else:
        inv["all"]["vars"]["splunk"]["apps_location"] = []

def getDefaultSplunkVariables(inv):
    # All variables have default value except for splunk.password, splunk.hec_token, splunk.shc.secret, and splunk.idxc.secret
    vars_scope = inv["all"]["vars"]
    vars_scope["ansible_ssh_user"] = getValueFromDEFAULTS("ansible_ssh_user") or "splunk"
    vars_scope["delay_num"] = getValueFromDEFAULTS("delay_num", casting=int) or 3
    vars_scope["retry_num"] = getValueFromDEFAULTS("retry_num", casting=int) or 50
    vars_scope["splunk"]["opt"] = os.environ.get('SPLUNK_OPT') or getValueFromDEFAULTS("splunk.opt") or "/opt"
    vars_scope["splunk"]["home"] = os.environ.get('SPLUNK_HOME') or getValueFromDEFAULTS(
        "splunk.home") or "{splunk_opt_path}/splunk".format(splunk_opt_path=vars_scope["splunk"]["opt"])
    splunk_home = vars_scope["splunk"]["home"]
    vars_scope["splunk"]["user"] = getValueFromDEFAULTS("splunk.user") or "splunk"
    vars_scope["splunk"]["exec"] = os.environ.get('SPLUNK_EXEC') or getValueFromDEFAULTS(
        "splunk.exec") or "{splunk_home_path}/bin/splunk".format(splunk_home_path=splunk_home)
    vars_scope["splunk"]["pid"] = os.environ.get('SPLUNK_PID') or getValueFromDEFAULTS(
        "splunk.pid") or "{splunk_home_path}/var/run/splunk/splunkd.pid".format(splunk_home_path=splunk_home)
    vars_scope["splunk"]["password"] = getSplunkPassword()
    vars_scope["splunk"]["svc_port"] = os.environ.get('SPLUNK_SVC_PORT') or getValueFromDEFAULTS("splunk.svc_port", casting=int) or 8089
    vars_scope["splunk"]["s2s_port"] = os.environ.get('SPLUNK_S2S_PORT') or getValueFromDEFAULTS("splunk.s2s_port", casting=int) or 9997
    vars_scope["splunk"]["http_port"] = getValueFromDEFAULTS("splunk.http_port", casting=int) or 8000
    vars_scope["splunk"]["hec_port"] = getValueFromDEFAULTS("splunk.hec_port", casting=int) or 8088
    vars_scope["splunk"]["hec_disabled"] = getValueFromDEFAULTS("splunk.hec_disabled", casting=int) or 0
    vars_scope["splunk"]["hec_enableSSL"] = getValueFromDEFAULTS("splunk.hec_enableSSL", casting=int) or 1
    vars_scope["splunk"]["hec_token"] = os.environ.get('SPLUNK_HEC_TOKEN') or getValueFromDEFAULTS("splunk.hec_token")
    vars_scope["splunk"]["shc"] = {}
    vars_scope["splunk"]["shc"]["enable"] = getValueFromDEFAULTS("splunk.shc.enable") or False
    vars_scope["splunk"]["shc"]["secret"] = os.environ.get('SPLUNK_SHC_SECRET') or getValueFromDEFAULTS("splunk.shc.secret")
    vars_scope["splunk"]["shc"]["label"] = getValueFromDEFAULTS("splunk.shc.label") or "shc_label"
    vars_scope["splunk"]["shc"]["replication_factor"] = getValueFromDEFAULTS("splunk.shc.replication_factor", casting=int) or 3
    vars_scope["splunk"]["shc"]["replication_port"] = getValueFromDEFAULTS("splunk.shc.replication_port", casting=int) or 4001
    vars_scope["splunk"]["idxc"] = {}
    vars_scope["splunk"]["idxc"]["enable"] = getValueFromDEFAULTS("splunk.idxc.enable") or False
    vars_scope["splunk"]["idxc"]["secret"] = os.environ.get('SPLUNK_IDXC_SECRET') or getValueFromDEFAULTS("splunk.idxc.secret")
    vars_scope["splunk"]["idxc"]["label"] = getValueFromDEFAULTS("splunk.idxc.label") or "idxc_label"
    vars_scope["splunk"]["idxc"]["search_factor"] = getValueFromDEFAULTS("splunk.idxc.search_factor", casting=int) or 3
    vars_scope["splunk"]["idxc"]["replication_factor"] = getValueFromDEFAULTS("splunk.idxc.replication_factor", casting=int) or 3
    vars_scope["splunk"]["idxc"]["replication_port"] = getValueFromDEFAULTS("splunk.idxc.replication_port", casting=int) or 4001
    vars_scope["splunk"]["enable_service"] = os.environ.get('SPLUNK_ENABLE_SERVICE') or False

    vars_scope["splunk"]["app_paths"] = {}
    if PLATFORM == "linux":
        vars_scope["splunk"]["group"] = getValueFromDEFAULTS("splunk.group") or "splunk"
        vars_scope["splunk"]["exec"] = getValueFromDEFAULTS(
            "splunk.exec") or "{splunk_home_path}/bin/splunk".format(splunk_home_path=splunk_home)
        vars_scope["splunk"]["app_paths"]["default"] = getValueFromDEFAULTS(
            "splunk.app_paths.default") or "{splunk_home_path}/etc/apps".format(splunk_home_path=splunk_home)
        vars_scope["splunk"]["app_paths"]["shc"] = getValueFromDEFAULTS(
            "splunk.app_paths.shc") or "{splunk_home_path}/etc/shcluster/apps".format(splunk_home_path=splunk_home)
        vars_scope["splunk"]["app_paths"]["idxc"] = getValueFromDEFAULTS(
            "splunk.app_paths.idxc") or "{splunk_home_path}/etc/master-apps".format(splunk_home_path=splunk_home)
        vars_scope["splunk"]["app_paths"]["httpinput"] = getValueFromDEFAULTS(
            "splunk.app_paths.httpinput") or "{splunk_home_path}/etc/apps/splunk_httpinput".format(splunk_home_path=splunk_home)
    elif PLATFORM == "windows":
        vars_scope["splunk"]["home"] = convert_path_windows_to_nix(vars_scope["splunk"]["home"])
        vars_scope["splunk"]["pid"] = convert_path_windows_to_nix(vars_scope["splunk"]["pid"])
        vars_scope["splunk"]["group"] = getValueFromDEFAULTS("splunk.group") or "Administrators"
        vars_scope["splunk"]["exec"] = convert_path_windows_to_nix(getValueFromDEFAULTS(
            "splunk.exec") or "{splunk_home_path}/bin/splunk.exe".format(splunk_home_path=splunk_home))
        vars_scope["splunk"]["app_paths"]["default"] = convert_path_windows_to_nix(getValueFromDEFAULTS(
            "splunk.app_paths.default") or "{splunk_home_path}/etc/apps".format(splunk_home_path=splunk_home))
        vars_scope["splunk"]["app_paths"]["shc"] =convert_path_windows_to_nix(getValueFromDEFAULTS(
            "splunk.app_paths.shc") or "{splunk_home_path}/etc/shcluster/apps".format(splunk_home_path=splunk_home))
        vars_scope["splunk"]["app_paths"]["idxc"] = convert_path_windows_to_nix(getValueFromDEFAULTS(
            "splunk.app_paths.idxc") or "{splunk_home_path}/etc/master-apps".format(splunk_home_path=splunk_home))
        vars_scope["splunk"]["app_paths"]["httpinput"] = convert_path_windows_to_nix(getValueFromDEFAULTS(
            "splunk.app_paths.httpinput") or "{splunk_home_path}/etc/apps/splunk_httpinput".format(splunk_home_path=splunk_home))

def convert_path_windows_to_nix(filepath):
    if filepath.startswith("C:"):
        filepath = re.sub(r"\\+", "/", filepath.lstrip("C:"))
        return filepath

def getValueFromDEFAULTS(path, casting=str):
    split_path = path.split(".")
    current_scope = DEFAULTS
    try:
        for path in split_path:
            current_scope = current_scope.get(path)
        if casting == int:
            return int(current_scope)
        return current_scope
    except:
        return None

def checkUpgrade(inv):
    upgrade_var = os.environ.get('SPLUNK_UPGRADE', False)
    if upgrade_var and upgrade_var.lower() == 'true':
        inv["all"]["vars"]["splunk"]["upgrade"] = True
    else:
        inv["all"]["vars"]["splunk"]["upgrade"] = False

def getUFSplunkVariables(inv):
    if os.environ.get('SPLUNK_DEPLOYMENT_SERVER', False):
        inv["all"]["vars"]["splunk"]["deployment_server"] = os.environ.get('SPLUNK_DEPLOYMENT_SERVER')
    if os.environ.get('SPLUNK_ADD', False):
        inv["all"]["vars"]["splunk"]["add"] = os.environ.get('SPLUNK_ADD').split(',')
    if os.environ.get('SPLUNK_BEFORE_START_CMD', False):
        inv["all"]["vars"]["splunk"]["before_start_cmd"] = os.environ.get('SPLUNK_BEFORE_START_CMD').split(',')
    if os.environ.get('SPLUNK_CMD', False):
        inv["all"]["vars"]["splunk"]["cmd"] = os.environ.get('SPLUNK_CMD').split(',')
    docker_monitoring_var = os.environ.get('DOCKER_MONITORING', False)
    if docker_monitoring_var and docker_monitoring_var.lower() == "true":
        inv["all"]["vars"]["docker_monitoring"] = True
    else:
        inv["all"]["vars"]["docker_monitoring"] = False
    inv["all"]["vars"]["docker_version"] = '18.06.0'

def getRandomString():
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.sample(char_set * 6, 6))

def push_defaults(url=None):
    '''
    This method accepts a url argument, but that argument can be None.  If it is None, then we load from a file
    In this way, we manage two different methods of loading the default file (which contains potentially sentive
    information
    '''
    if url:
        if not os.path.exists('/tmp/defaults'):
            os.mkdir('/tmp/defaults')

        delay = 1
        while True:
            response = urllib2.urlopen(url)
            status_code = response.getcode()
            text = response.read()
            if status_code >= 400:
                #Any 2xx or 3xx status code should be okay. 4xx and 5xx should give us an error
                print "ERROR - Download from URL {} failed CODE {} MESSAGE {}".format(url, status_code, text)
                sleep(delay)
                print "RETRYING"
                delay = delay * 2
                if delay >= 60:
                    delay = 60
            else:
                break

        if text is None or len(text) == 0:
            print "ABORTING - Required defaults empty URL {}".format(url)
            sys.exit(4)
        with open('/tmp/defaults/default.yml', 'wt') as f:
            f.write(text)

    if os.path.exists('/tmp/defaults/default.yml'):
        try:
            with open("/tmp/defaults/default.yml", 'r') as yaml_file:
                loaded_yaml = yaml.load(yaml_file)
            return loaded_yaml
        except:
            print "ABORTING: Failed to load the provided default.yml. Please verify your default.yml"
            sys.exit(1)

def obfuscate_vars(inventory):
    stars = '**************'
    if inventory["all"]["vars"]["splunk"].get("password"):
        inventory["all"]["vars"]["splunk"]["password"] = stars
    if inventory["all"]["vars"]["splunk"].get("shc") and inventory["all"]["vars"]["splunk"]["shc"].get("secret"):
        inventory["all"]["vars"]["splunk"]["shc"]["secret"] = stars
    if inventory["all"]["vars"]["splunk"].get("idxc") and inventory["all"]["vars"]["splunk"]["idxc"].get("secret"):
        inventory["all"]["vars"]["splunk"]["idxc"]["secret"] = stars
    return inventory

def create_parser():
    parser = argparse.ArgumentParser(description='Return Ansible inventory defined in the environment.')
    parser.add_argument('--list', action='store_true', default=True, help='List all hosts (default: True)')
    parser.add_argument('--host', action='store', help='Only get information for a specific host.')
    parser.add_argument('--write-to-file', action='store_true', default=False, help='Write to file for debugging')
    parser.add_argument('--write-to-stdout', action='store_true', default=False, help='create a default.yml file shown on stdout from current vars')
    return parser
def prep_for_yaml_out(inventory):
    inventory_to_dump=inventory["all"]["vars"]


    keys_to_del = [ "docker_version", "ansible_ssh_user", "delay_num", "docker_monitorying", "apps_location",
                    "docker_monitoring", "build_location", "build_remote_src", "deployer_included", "upgrade",
                    "role", "search_head_cluster", "indexer_cluster", "license_master_included", "license_uri"]
    for key in keys_to_del:
        if key in inventory_to_dump:
            del inventory_to_dump[key]
        if key in inventory_to_dump["splunk"]:
            del inventory_to_dump["splunk"][key]
        if key in inventory_to_dump["splunk"]["app_paths"]:
            del inventory_to_dump["splunk"]["app_paths"][key]
        if key in inventory_to_dump["splunk"]["shc"]:
            del inventory_to_dump["splunk"]["shc"][key]
        if key in inventory_to_dump["splunk"]["idxc"]:
            del inventory_to_dump["splunk"]["idxc"][key]
    #remove extra stuff when we know it's the forwarder
    if inventory_to_dump["splunk"]["home"] == "/opt/splunkforwarder":
        del inventory_to_dump["splunk"]["idxc"]
        del inventory_to_dump["splunk"]["shc"]
    return inventory_to_dump

def main():
    global DEFAULTS
    parser = create_parser()
    args = parser.parse_args()
    sys_args = sys.argv[1:]
    # Parse command line arguments
    url = os.environ.get('SPLUNK_DEFAULTS_URL', None)
    DEFAULTS = push_defaults(url)

    getSplunkInventory(inventory)
    if args.write_to_file:
        with open(os.path.join(HERE, "ansible_inventory.json"), "w") as outfile:
            json.dump(obfuscate_vars(inventory), outfile, sort_keys=True,indent=4, ensure_ascii=False)
    elif args.write_to_stdout:
        #remove keys we don't want to print
        inventory_to_dump = prep_for_yaml_out(inventory)
        print "---"
        print yaml.dump(inventory_to_dump, default_flow_style=False)
    else:
        print json.dumps(inventory)


if __name__ == "__main__":
    main()
