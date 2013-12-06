# -*- coding: utf-8 -*-
##
## This file is part of Invenio.
## Copyright (C) 2013 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""
Set of utilities for the SCOAP3 project.
"""

from __future__ import division

import sys
import logging
import urllib
import itertools
import datetime
from xml.dom.minidom import parse

from invenio.search_engine import get_collection_reclist
from invenio.config import CFG_LOGDIR, CFG_CROSSREF_USERNAME, CFG_CROSSREF_PASSWORD, CFG_SITE_NAME
from os.path import join

CFG_CROSSREF_DOIS_PER_REQUEST = 10
CFG_CROSSREF_API_URL = "http://doi.crossref.org/search/doi?"

def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]

def init_db():
    run_sql("""
CREATE TABLE IF NOT EXISTS bibrec_scoap3check (
  id_bibrec mediumint(8) unsigned NOT NULL,
  doi varchar(255) NOT NULL,
  arxiv varchar(255) NULL default NULL,
  doi_timestamp datetime NULL default NULL,
  last_verification datetime NOT NULL,
  valid_record boolean NOT NULL default 'false',
  PRIMARY KEY doi (doi),
  UNIQUE KEY id_bibrec(id_bibrec),
  KEY arxiv(arxiv),
  KEY doi_timestamp(doi_timestamp),
  KEY last_verification(last_verification),
  KEY valid_record(valid_record)
) ENGINE=MyISAM;""")

def get_all_recids_to_check():
    all_recids = get_collection_reclist(CFG_SITE_NAME)
    last_verification = run_sql("SELECT MAX(last_verification) FROM bibrec_scoap3check")[0][0] or datetime.datetime(1970, 1, 1, 0, 0)
    verified_recids = intbitset(run_sql("SELECT id_bibrec FROM bibrec_scoap3check WHERE doi_timestamp IS NOT NULL AND arxiv IS NOT NULL AND valid_record"))
    unverified_recids = all_recids - verified_recids
    modified_recids = all_recids & run_sql("SELECT bibrec.id FROM bibrec, bibrec_scoap3check WHERE bibrec.id=id_bibrec AND modification_date>last_verification")
    return new_recids | modified_recids

def get_all_info_from_recid(recid):
    


def crossref_checker(dois, username=CFG_CROSSREF_USERNAME, password=CFG_CROSSREF_PASSWORD):
    """
    Given a list of DOIs send a batch request of up to CFG_CROSSREF_DOIS_PER_REQUEST
    and return all information
    """
    ret = dict([(doi, None) for doi in dois])
    for chunk in chunks(dois, CFG_CROSSREF_DOIS_PER_REQUEST):
        query = [("pid", "%s:%s" % (username, password)), ("format", "info"), ("doi", chunk)]
        results = parse(urllib.urlopen(CFG_CROSSREF_API_URL + urllib.urlencode(query, doseq=True)))
        for result in results.getElementsByTagName("crossref-metadata"):
            doi = get_value_in_tag(result, 'doi')
            if doi not in dois:
                raise StandardError("CrossRef returned information for a DOI that was not asked for!? %s" % doi)
            for crm_item in result.getElementsByTagName("crm-item"):
                if crm_item.getAttribute('name') == u'deposit-timestamp':
                    ret[doi] = datetime.datetime.strptime(xml_to_text(crm_item), "%Y%m%d%H%M%S%f")
                    break
    return ret

def lock_issue():
    """
    Locks the issu in case of error.
    """
    # TODO
    print >> sys.stderr, "locking issue"


# Creates a logger object
def create_logger(publisher, filename=join(CFG_LOGDIR, 'scoap3_harvesting.log')):
    logger = logging.getLogger(publisher)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(filename=filename)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)
    return logger


def progress_bar(n):
    num = 0
    while num <= n:
        yield "\r%d%% [%s%s]" % (num/n*100, "="*num, '.'*(n-num))
        num += 1


class MD5Error(Exception):
    def __init__(self, value):
        self.value = value


class NoNewFiles(Exception):
    def __init__(self, value=None):
        self.value = value
