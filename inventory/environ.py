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
import requests
import sys
import urllib2, urllib3
import yaml
from time import sleep
import ssl

urllib3.disable_warnings()

HERE = os.path.dirname(os.path.normpath(__file__))
PLATFORM = platform.platform().lower()
DEFAULTS = {}
if "windows" in PLATFORM or "cygwin" in PLATFORM:
    PLATFORM = "windows"
else:
    PLATFORM = "linux"

roleNames = [
    'splunk_cluster_master', # (if it exists, set up indexer clustering)
    'splunk_deployer',
    'splunk_heavy_forwarder',
    'splunk_standalone',
    'splunk_search_head',
    'splunk_indexer',
    'splunk_license_master', # (if it exists, run adding license with a license master)
    'splunk_search_head_captain', # TODO: remove this as we deprecate this role
    'splunk_universal_forwarder',
    'splunk_deployment_server'
]

varPrefix = "SPLUNK_VAR_"
reVarPrefix = r"${varPrefix}(.*)"
envPrefix = "SPLUNK_ROLE_"
reNamePattern = r"${envPrefix}(.*)"

inventory = {
    "_meta": {
        "hostvars": {}
    },
    "all": {
        "hosts": [],
        "children": ["ungrouped"]
    },
    "ungrouped": {
        "hosts": []
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
    inventory["all"]["vars"] = getDefaultVars()

    if(os.path.isfile("/.dockerenv")):
        if("localhost" not in inventory["all"]["children"]):
            inventory["all"]["hosts"].append("localhost")
        inventory["_meta"]["hostvars"]["localhost"] = loadHostVars(inventory["all"]["vars"], os.uname()[1], PLATFORM)
        inventory["_meta"]["hostvars"]["localhost"]["ansible_connection"] = "local"

def getDefaultVars():
    defaultVars = loadDefaultSplunkVariables()
    overrideEnvironmentVars(defaultVars)

    defaultVars["splunk"]["license_master_included"] = True if os.environ.get('SPLUNK_LICENSE_MASTER_URL', False) else False
    defaultVars["splunk"]["deployer_included"] = True if os.environ.get('SPLUNK_DEPLOYER_URL', False) else False
    defaultVars["splunk"]["indexer_cluster"] = True if os.environ.get('SPLUNK_CLUSTER_MASTER_URL', False) else False
    defaultVars["splunk"]["search_head_cluster"] = True if os.environ.get('SPLUNK_SEARCH_HEAD_CAPTAIN_URL', False) else False
    defaultVars["splunk"]["search_head_cluster_url"] = os.environ.get('SPLUNK_SEARCH_HEAD_CAPTAIN_URL', None)
    # Need to provide some file value (does not have to exist). The task will automatically skip over if the file is not found. Otherwise, will throw an error if no file is specified.
    defaultVars["splunk"]["license_uri"] = os.environ.get('SPLUNK_LICENSE_URI', 'splunk.lic')
    if defaultVars["splunk"]["license_uri"] and '*' in defaultVars["splunk"]["license_uri"]:
        defaultVars["splunk"]["wildcard_license"] = True
    else:
        defaultVars["splunk"]["wildcard_license"] = False
    defaultVars["splunk"]["nfr_license"] = os.environ.get('SPLUNK_NFR_LICENSE', '/tmp/nfr_enterprise.lic')
    defaultVars["splunk"]["ignore_license"] = os.environ.get('SPLUNK_IGNORE_LICENSE', False)
    defaultVars["splunk"]["license_download_dest"] = os.environ.get('SPLUNK_LICENSE_INSTALL_PATH', '/tmp/splunk.lic')
    defaultVars["splunk"]["role"] = os.environ.get('SPLUNK_ROLE', 'splunk_standalone')
    defaultVars["splunk_home_ownership_enforcement"] = False if os.environ.get('SPLUNK_HOME_OWNERSHIP_ENFORCEMENT', "").lower() == "false" else True
    defaultVars["hide_password"] = True if os.environ.get('HIDE_PASSWORD', "").lower() == "true" else False

    # Check required Java installation
    java_version = os.environ.get("JAVA_VERSION", "").lower()
    if java_version in ['oracle:8', 'openjdk:8', 'openjdk:11']:
        defaultVars["java_version"] = os.environ.get("JAVA_VERSION", "")
        if java_version == "oracle:8":
            defaultVars["java_download_url"] = os.environ.get("JAVA_DOWNLOAD_URL", "https://download.oracle.com/otn-pub/java/jdk/8u201-b09/42970487e3af4f5aa5bca3f542482c60/jdk-8u201-linux-x64.tar.gz")
            try:
                defaultVars["java_update_version"] = re.search("jdk-8u(\d+)-linux-x64.tar.gz", defaultVars["java_download_url"]).group(1)
            except:
                raise Exception("Invalid Java download URL format")
        elif java_version == "openjdk:11":
            defaultVars["java_download_url"] = os.environ.get(
                "JAVA_DOWNLOAD_URL", "https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz")
            try:
                defaultVars["java_update_version"] = re.search(
                    "openjdk-(\d+\.\d+\.\d+)_linux-x64_bin.tar.gz", defaultVars["java_download_url"]).group(1)
            except:
                raise Exception("Invalid Java download URL format")


    # Lower indexer search/replication factor when indexer hosts less than 3
    if inventory.has_key("splunk_indexer") and inventory["splunk_indexer"].has_key("hosts") and len(inventory["splunk_indexer"]["hosts"]) < 3:
        defaultVars["splunk"]["idxc"]["search_factor"] = 1
        defaultVars["splunk"]["idxc"]["replication_factor"] = 1

    #When sites are specified, assume multisite
    if inventory.has_key("splunk.site"):
        defaultVars["splunk"]["multisite_replication_factor_origin"] = 1
        defaultVars["splunk"]["multisite_replication_factor_total"] = 1
        defaultVars["splunk"]["multisite_search_factor_origin"] = 1
        defaultVars["splunk"]["multisite_search_factor_total"] = 1

    getSplunkBuild(defaultVars)
    getSplunkApps(defaultVars)
    getUFSplunkVariables(defaultVars)
    return defaultVars

def getSplunkBuild(vars_scope):
    vars_scope["splunk"]["build_location"] = os.environ.get("SPLUNK_BUILD_URL", vars_scope["splunk"]["build_location"])
    if vars_scope["splunk"]["build_location"] and vars_scope["splunk"]["build_location"].startswith("http"):
        vars_scope["splunk"]["build_remote_src"] = True
    else:
        vars_scope["splunk"]["build_remote_src"] = False

def getSplunkApps(vars_scope):
    splunkbase_username = (vars_scope["splunkbase_username"] if "splunkbase_username" in vars_scope else None) or os.environ.get("SPLUNKBASE_USERNAME") or None
    splunkbase_password = (vars_scope["splunkbase_password"] if "splunkbase_password" in vars_scope else None) or os.environ.get("SPLUNKBASE_PASSWORD") or None
    if splunkbase_username and splunkbase_password:
        splunkbase_username = urllib2.quote(splunkbase_username)
        splunkbase_password = urllib2.quote(splunkbase_password)
        response = urllib2.urlopen("https://splunkbase.splunk.com/api/account:login/", "username={}&password={}".format(splunkbase_username, splunkbase_password))
        if response.getcode() != 200:
            raise Exception("Invalid Splunkbase credentials - will not download apps from Splunkbase")
        output = response.read()
        splunkbase_token = re.search("<id>(.*)</id>", output, re.IGNORECASE)
        vars_scope["splunkbase_token"] = splunkbase_token.group(1) if splunkbase_token else None
    apps = os.environ.get("SPLUNK_APPS_URL", None)
    if apps:
        vars_scope["splunk"]["apps_location"] = apps.split(",")
    else:
        vars_scope["splunk"]["apps_location"] = []

def overrideEnvironmentVars(vars_scope):
    vars_scope["ansible_pre_tasks"] = os.environ.get("SPLUNK_ANSIBLE_PRE_TASKS", vars_scope["ansible_pre_tasks"])
    vars_scope["ansible_post_tasks"] = os.environ.get("SPLUNK_ANSIBLE_POST_TASKS", vars_scope["ansible_post_tasks"])
    vars_scope["cert_prefix"] = os.environ.get("SPLUNK_CERT_PREFIX", vars_scope.get("cert_prefix", "https"))
    vars_scope["splunk"]["opt"] = os.environ.get('SPLUNK_OPT', vars_scope["splunk"]["opt"])
    vars_scope["splunk"]["home"] = os.environ.get('SPLUNK_HOME', vars_scope["splunk"]["home"])
    splunk_home = vars_scope["splunk"]["home"]
    vars_scope["splunk"]["exec"] = os.environ.get('SPLUNK_EXEC', vars_scope["splunk"]["exec"])
    vars_scope["splunk"]["pid"] = os.environ.get('SPLUNK_PID', vars_scope["splunk"]["pid"])
    vars_scope["splunk"]["password"] = os.environ.get('SPLUNK_PASSWORD', vars_scope["splunk"]["password"])
    vars_scope["splunk"]["svc_port"] = os.environ.get('SPLUNK_SVC_PORT', vars_scope["splunk"]["svc_port"])
    vars_scope["splunk"]["s2s_port"] = os.environ.get('SPLUNK_S2S_PORT', vars_scope["splunk"]["s2s_port"])
    vars_scope["splunk"]["hec_token"] = os.environ.get('SPLUNK_HEC_TOKEN', vars_scope["splunk"]["hec_token"])
    if "shc" not in vars_scope["splunk"]:
        vars_scope["splunk"]["shc"] = {}
    vars_scope["splunk"]["shc"]["secret"] = os.environ.get('SPLUNK_SHC_SECRET', vars_scope["splunk"]["shc"]["secret"])
    if "idxc" not in vars_scope["splunk"]:
        vars_scope["splunk"]["idxc"] = {}
    vars_scope["splunk"]["idxc"]["secret"] = os.environ.get('SPLUNK_IDXC_SECRET', vars_scope["splunk"]["idxc"]["secret"])
    vars_scope["splunk"]["enable_service"] = os.environ.get('SPLUNK_ENABLE_SERVICE', vars_scope["splunk"]["enable_service"])
    vars_scope["splunk"]["allow_upgrade"] = os.environ.get('SPLUNK_ALLOW_UPGRADE', vars_scope["splunk"]["allow_upgrade"])
    vars_scope["splunk"]["build_location"] = os.environ.get('SPLUNK_INSTALLER', vars_scope["splunk"]["build_location"])
    # add ssl variables
    vars_scope["splunk"]["http_enableSSL"] = os.environ.get('SPLUNK_HTTP_ENABLESSL', vars_scope["splunk"]["http_enableSSL"])
    vars_scope["splunk"]["http_enableSSL_cert"] = os.environ.get('SPLUNK_HTTP_ENABLESSL_CERT', vars_scope["splunk"]["http_enableSSL_cert"])
    vars_scope["splunk"]["http_enableSSL_privKey"] = os.environ.get('SPLUNK_HTTP_ENABLESSL_PRIVKEY', vars_scope["splunk"]["http_enableSSL_privKey"])
    vars_scope["splunk"]["http_enableSSL_privKey_password"] = os.environ.get('SPLUNK_HTTP_ENABLESSL_PRIVKEY_PASSWORD', vars_scope["splunk"]["http_enableSSL_privKey_password"])
    #Used for multisite
    if 'SPLUNK_SITE' in os.environ or 'site' in vars_scope["splunk"]:
        vars_scope["splunk"]["site"] = os.environ.get('SPLUNK_SITE', vars_scope["splunk"].get("site"))

        all_sites = os.environ.get('SPLUNK_ALL_SITES', vars_scope["splunk"].get("all_sites"))
        if all_sites:
            vars_scope["splunk"]["all_sites"] = all_sites

        multisite_master = os.environ.get('SPLUNK_MULTISITE_MASTER', vars_scope["splunk"].get("multisite_master"))
        if multisite_master:
            vars_scope["splunk"]["multisite_master"] = multisite_master

        vars_scope["splunk"]["multisite_master_port"] = os.environ.get('SPLUNK_MULTISITE_MASTER_PORT', vars_scope["splunk"].get("multisite_master_port", 8089))
        vars_scope["splunk"]["multisite_replication_factor_origin"] = os.environ.get('SPLUNK_MULTISITE_REPLICATION_FACTOR_ORIGIN', vars_scope["splunk"].get("multisite_replication_factor_origin", 1))
        vars_scope["splunk"]["multisite_replication_factor_total"] = os.environ.get('SPLUNK_MULTISITE_REPLICATION_FACTOR_TOTAL', vars_scope["splunk"].get("multisite_replication_factor_total", 1))
        vars_scope["splunk"]["multisite_search_factor_origin"] = os.environ.get('SPLUNK_MULTISITE_SEARCH_FACTOR_ORIGIN', vars_scope["splunk"].get("multisite_search_factor_origin", 1))
        vars_scope["splunk"]["multisite_search_factor_total"] = os.environ.get('SPLUNK_MULTISITE_SEARCH_FACTOR_TOTAL', vars_scope["splunk"].get("multisite_search_factor_total", 1))

def convert_path_windows_to_nix(filepath):
    if filepath.startswith("C:"):
        filepath = re.sub(r"\\+", "/", filepath.lstrip("C:"))
        return filepath

def getUFSplunkVariables(vars_scope):
    if os.environ.get('SPLUNK_DEPLOYMENT_SERVER', False):
        vars_scope["splunk"]["deployment_server"] = os.environ.get('SPLUNK_DEPLOYMENT_SERVER')
    if os.environ.get('SPLUNK_ADD', False):
        vars_scope["splunk"]["add"] = os.environ.get('SPLUNK_ADD').split(',')
    if os.environ.get('SPLUNK_BEFORE_START_CMD', False):
        vars_scope["splunk"]["before_start_cmd"] = os.environ.get('SPLUNK_BEFORE_START_CMD').split(',')
    if os.environ.get('SPLUNK_CMD', False):
        vars_scope["splunk"]["cmd"] = os.environ.get('SPLUNK_CMD').split(',')
    vars_scope["docker_version"] = '18.06.0'

def getRandomString():
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.sample(char_set * 6, 6))

def merge_dict(dict1, dict2, path=None):
    if path is None: path = []
    for key in dict2:
        if key in dict1:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                merge_dict(dict1[key], dict2[key], path + [str(key)])
            else:
                dict1[key] = dict2[key]
        else:
            dict1[key] = dict2[key]
    return dict1

def loadDefaultSplunkVariables():
    '''
    This method accepts a url argument, but that argument can be None. If it is None, then we load from a file
    In this way, we manage two different methods of loading the default file (which contains potentially sentive
    information
    '''
    loaded_yaml = {}
    ### Load the splunk defaults shipped with splunk-ansible
    if os.environ.get("SPLUNK_ROLE", None) == "splunk_universal_forwarder":
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "splunkforwarder_defaults_{platform}.yml".format(platform=PLATFORM)), 'r') as yaml_file:
            loaded_yaml = yaml.load(yaml_file, Loader=yaml.Loader)
    else:
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "splunk_defaults_{platform}.yml".format(platform=PLATFORM)), 'r') as yaml_file:
            loaded_yaml = yaml.load(yaml_file, Loader=yaml.Loader)

    ### Load the defaults for the environment
    if "config" in loaded_yaml and loaded_yaml["config"] is not None and "baked" in loaded_yaml["config"] and \
            os.path.exists(os.path.join(loaded_yaml["config"]["defaults_dir"], loaded_yaml["config"]["baked"])):
        try:
            with open(os.path.join(loaded_yaml["config"]["defaults_dir"], loaded_yaml["config"]["baked"]), 'r') as yaml_file:
                loaded_yaml = merge_dict(loaded_yaml, yaml.load(yaml_file, Loader=yaml.Loader))
        except:
            raise

    url = None
    if "config" in loaded_yaml and loaded_yaml["config"] is not None and "env" in loaded_yaml["config"] and loaded_yaml["config"]["env"] is not None and "var" in loaded_yaml["config"]["env"] and loaded_yaml["config"]["env"]["var"] is not None and len(loaded_yaml["config"]["env"]["var"]) > 0:
        url = os.environ.get(loaded_yaml["config"]["env"]["var"], None)

    if url:
        headers = None
        if "headers" in loaded_yaml['config']['env'] and loaded_yaml['config']['env']['headers'] != None and len(loaded_yaml['config']['env']['headers']) > 0:
            headers = loaded_yaml['config']['env']['headers']

        max_retries = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_RETRIES', loaded_yaml["config"]["max_retries"]))
        max_delay = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_DELAY', loaded_yaml["config"]["max_delay"]))
        max_timeout = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_TIMEOUT', loaded_yaml["config"]["max_timeout"]))
        verify = bool(os.environ.get('SPLUNK_DEFAULTS_HTTPS_VERIFY', loaded_yaml["config"]["env"]["verify"]))
        unlimited_retries = (max_retries == -1)
        current_retry = 0
        while True:
            try:
                response = requests.get(url.format(platform=PLATFORM), headers=headers, timeout=max_timeout, verify=verify)
                response.raise_for_status()
                loaded_yaml = merge_dict(loaded_yaml, yaml.load(response.content, Loader=yaml.Loader))
                break
            except Exception as e:
                if unlimited_retries or current_retry < max_retries:
                    current_retry += 1
                    print('URL request #{0} failed, sleeping {1} seconds and retrying'.format(current_retry, max_delay))
                    sleep(max_delay)
                else:
                    raise e
    return loaded_yaml

def loadHostVars(defaults, hostname=None, platform="linux"):
    loaded_yaml = {}
    if hostname == None:
        return loaded_yaml

    url = None
    if "config" in defaults and defaults["config"] is not None and "host" in defaults["config"] and defaults["config"]["host"] is not None and "url" in defaults['config']['host'] and defaults['config']['host']['url'] is not None and len(defaults['config']['host']['url'].strip()) > 0:
        url = defaults['config']['host']['url'].strip()
        headers = None
        if "headers" in defaults['config']['host'] and defaults['config']['host']['headers'] != None and len(defaults['config']['host']['headers']) > 0:
            headers = defaults['config']['host']['headers']

        max_retries = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_RETRIES', defaults["config"]["max_retries"]))
        max_delay = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_DELAY', defaults["config"]["max_delay"]))
        max_timeout = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_TIMEOUT', defaults["config"]["max_timeout"]))
        verify = bool(os.environ.get('SPLUNK_DEFAULTS_HTTPS_VERIFY', defaults["config"]["host"]["verify"]))
        unlimited_retries = (max_retries == -1)
        current_retry = 0
        while True:
            try:
                response = requests.get(url.format(hostname=hostname, platform=platform), headers=headers, timeout=max_timeout, verify=verify)
                response.raise_for_status()
                loaded_yaml = merge_dict(loaded_yaml, yaml.load(response.content, Loader=yaml.Loader))
                break
            except Exception as e:
                if unlimited_retries or current_retry < max_retries:
                    current_retry += 1
                    print('URL request #{0} failed, sleeping {1} seconds and retrying'.format(current_retry, max_delay) + str(e))
                    sleep(max_delay)
                else:
                    raise e
    return loaded_yaml

def obfuscate_vars(inventory):
    stars = '**************'
    if inventory["all"]["vars"]["splunk"].get("password"):
        inventory["all"]["vars"]["splunk"]["password"] = stars
    if inventory["all"]["vars"]["splunk"].get("shc") and inventory["all"]["vars"]["splunk"]["shc"].get("secret"):
        inventory["all"]["vars"]["splunk"]["shc"]["secret"] = stars
    if inventory["all"]["vars"]["splunk"].get("idxc") and inventory["all"]["vars"]["splunk"]["idxc"].get("secret"):
        inventory["all"]["vars"]["splunk"]["idxc"]["secret"] = stars
    if inventory["all"]["vars"]["splunk"].get("smartstore", False):
        for index in range(0, len(inventory["all"]["vars"]["splunk"]["smartstore"])):
            if inventory["all"]["vars"]["splunk"]["smartstore"][index].get("s3", False):
                if inventory["all"]["vars"]["splunk"]["smartstore"][index]["s3"].get("access_key", False):
                    inventory["all"]["vars"]["splunk"]["smartstore"][index]["s3"]["access_key"] = stars
                if inventory["all"]["vars"]["splunk"]["smartstore"][index]["s3"].get("secret_key", False):
                    inventory["all"]["vars"]["splunk"]["smartstore"][index]["s3"]["secret_key"] = stars
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

    keys_to_del = [ "docker_version", "ansible_ssh_user", "delay_num", "apps_location", "build_location", "build_remote_src", "deployer_included", "upgrade", "role", "search_head_cluster", "indexer_cluster", "license_master_included", "license_uri"]
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

    getSplunkInventory(inventory)
    if args.write_to_file:
        with open(os.path.join("/opt/container_artifact", "ansible_inventory.json"), "w") as outfile:
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
