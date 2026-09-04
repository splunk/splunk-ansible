#!/usr/bin/env python
'''
The simple script here is used for generating the Indexer TA for ESS.  It should be able to handle
all of the current supported versions
'''
from __future__ import absolute_import
from __future__ import print_function

import sys
import argparse
import json

import splunk.auth as auth
import splunk.rest as rest
try:
    # In newer versions of splunk we should be importing from
    # this location
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    # Older versions may still use this import
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


app_info = '{"app": "Splunk_TA_ForIndexers", "label": "Splunk App For Indexers", "version": "1.0.0", "build": "0"}'
include_indexes = True
include_properties = True
imported_apps_only = True
namespace = 'SplunkEnterpriseSecuritySuite'
spl_location = make_splunkhome_path(['etc', 'apps', 'SA-Utils', 'local', 'data', 'appmaker'])


def create_parser():
    '''
    Wrapper for the argument parser
    '''
    parser = argparse.ArgumentParser(description="Script to generate Enterprise Security TA bundle")
    parser.add_argument("--username", default="admin", type=str, help="Splunk username")
    parser.add_argument("--password", default=None, type=str, help="Splunk password")
    return parser

def make_ta_for_indexers(username, password):
    '''
    Splunk_TA_ForIndexers spl generation for ES 4.2.0 and up
    There are now three versions of ES we're now supporting (changes to makeIndexTimeProperties
    have been made over different versions).
    The try/except blocks below are meant to handle the differences in function signature.
    '''
    if not username or not password:
        raise Exception("Splunk username and password must be defined.")
    sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Utils', 'bin']))
    session_key = auth.getSessionKey(username, password)
    from app_maker.make_index_time_properties import makeIndexTimeProperties
    success = False
    try:
        spec = {}
        spec["include_indexes"] = include_indexes
        spec["include_properties"] = include_properties
        spec.update()
        archive = makeIndexTimeProperties(spec, session_key)
        success = True
    except TypeError:
        #Some versions have a change that consolidated app_info, namespace, and include_indexes,
        #and added include_properties.
        #Below code is written to handle older versions.
        pass
    if success:
        print(archive)
        assert archive.startswith(spl_location)
        return
    try:
        #second-newest version compatible code
        archive = makeIndexTimeProperties(app_info, session_key, include_indexes=include_indexes,
        				  imported_apps_only=imported_apps_only,
                                          namespace=namespace)
    except TypeError:
        #Some versions have a change that removed the kwarg imported_apps_only
        #For older versions, we'll still need to use the imported_apps_only arg, so that's why we
        #do this second
        archive = makeIndexTimeProperties(app_info, session_key, include_indexes=include_indexes,
        				  namespace=namespace)
    print(archive)
    assert archive.startswith(spl_location)

def make_ta_for_indexers_6xx(username, password):
    '''
    Splunk_TA_ForIndexers spl generation for ES 6.0.0 and up
    For this we'll use the rest endpoints
    '''

    uri = '/services/data/appmaker/makeapp'
    APP_INFO_DICT = {
        "app": "Splunk_TA_ForIndexers",
        "label": "Splunk App For Indexers",
        "version": "1.0.0",
        "build": "0"
    }
    INCLUDE_INDEXES = True
    INCLUDE_PROPERTIES = True

    SESSION_KEY = auth.getSessionKey(username, password)
    spec = {
        '_app': APP_INFO_DICT,
        'include_indexes': INCLUDE_INDEXES,
        'include_properties': INCLUDE_PROPERTIES
    }
    postargs = {
        'spec': json.dumps(spec),
        'routine': 'make_index_time_properties:makeIndexTimeProperties'
    }

    unused_r, c = rest.simpleRequest(
        uri,
        sessionKey=SESSION_KEY,
        postargs=postargs,
    )

    archive = make_splunkhome_path([
        'etc',
        'apps',
        json.loads(c)['namespace'],
        'local',
        'data',
        'appmaker',
        json.loads(c)['filename']
    ])
    print(archive)


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    try:
        make_ta_for_indexers_6xx(args.username, args.password)
    except:
        #If the new one fails, try the older one
        make_ta_for_indexers(args.username, args.password)
