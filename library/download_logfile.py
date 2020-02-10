#!/usr/bin/python
# vim: set fileencoding=utf-8 :

"""
Meta
====
    $Id$
    $DateTime$
    $Author$
    $Change$
"""

import sys
import mule
from mule.connector.s3connector import S3Connector


def download_source():
    """
    Download test files into test data dir by Mule
    e.g.
      access.log            -> <data dir>/access.log
      data_input/access.log -> <data dir>/data_input/access.log

    :type source: string
    :param source: the remote file or folder to copy.

    :rtype: string
    :return: local path to the downloaded file or folder.
    """
    if len(sys.argv) != 2:
        raise Exception("Only accept 1 log file name.")
    target = '/tmp/'
    normalized_source = sys.argv[1].replace('\\', '/')

    mule.get(
        source=normalized_source, target=target,
        connector=S3Connector(bucket_name='splk-newtest-data'))


if __name__ == "__main__":
    download_source()
