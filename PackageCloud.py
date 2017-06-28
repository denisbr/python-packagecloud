#!/usr/bin/env python
"""Packagecloud API module

   Implements functions for working with:
   * master and read-tokens
   * packages
   * stats

   Packagecloud API reference docs:
   https://packagecloud.io/docs/api
"""

from __future__ import print_function
import sys
import time

from requests import ConnectionError
from requests.exceptions import RequestException
from requests import HTTPError
from requests import Request
from requests import Session
from requests import Timeout


def eprint(*args, **kwargs):
    """Print to stderr"""
    print(*args, file=sys.stderr, **kwargs)


def abort(errstr, errcode=1):
    """Print error and exit with errcode"""
    eprint(errstr)
    sys.exit(errcode)


def api_call(url, method, debug, **kwargs):
    """Generic method to make HTTP requests to packagecloud API

       Will retry on connection error or timeout, until max retries
    """
    resp = None
    attempt = 0
    maxattempts = 3
    req = Request(method.upper(), url, **kwargs)

    if debug:
        print("DEBUG: Request (%s) %s" % (method.upper(), url))

    while True:
        try:
            attempt += 1
            resp = Session().send(
                Session().prepare_request(req), verify=True)
            resp.raise_for_status()
            break
        except (HTTPError, ConnectionError, Timeout) as ex:
            if attempt >= maxattempts:
                abort(ex.message)
            else:
                time.sleep(1)
                continue
        except RequestException as ex:
            abort(ex.message)

    if resp is not None:
        return resp
    else:
        abort("Error making API call to URL: " % url)


###########################################################
# Packagecloud Master tokens                              #
# https://packagecloud.io/docs/api#resource_master_tokens #
###########################################################
def get_master_tokens(user, repo, config):
    """Lists all master tokens in repository

       https://packagecloud.io/docs/api#resource_master_tokens_method_index

       GET /api/v1/repos/:user/:repo/master_tokens
    """
    url = "{}/repos/{}/{}/master_tokens".format(config['url_base'], user, repo)

    try:
        resp = (api_call(url, 'get', config['debug']))
        tokens = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return tokens


def get_master_tokens_dict(user, repo, config):
    """Get the complete master token dict from packagecloud

       https://packagecloud.io/docs/api#resource_master_tokens_method_index

       GET /api/v1/repos/:user/:repo/master_tokens
    """
    token_list = {}
    tokens = get_master_tokens(user, repo, config)

    for token in tokens:
        # skip the default and web-download keys
        if token['name'] in ('default', 'web-downloads'):
            continue
        if token['name']:
            token_list[token['name']] = token['value']
            if config['debug']:
                print("DEBUG: Found token {} with value {}".
                      format(token['name'], token['value']))

    return token_list


def get_master_token(user, repo, name, config):
    """Get one master token based on name

       https://packagecloud.io/docs/api#resource_master_tokens_method_index

       GET /api/v1/repos/:user/:repo/master_tokens
    """
    url = "{}/repos/{}/{}/master_tokens".format(config['url_base'], user, repo)

    try:
        resp = (api_call(url, 'get', config['debug']))
        tokens = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))
    for token in tokens:
        if token['name'] == name:
            return token

    return None


def create_master_token(user, repo, config, name):
    """Create a named master token in repo

       https://packagecloud.io/docs/api#resource_master_tokens_method_create

       POST /api/v1/repos/:user/:repo/master_tokens
    """
    url = "{}/repos/{}/{}/master_tokens".format(config['url_base'], user, repo)
    postdata = ("master_token[name]=%s" % name)

    try:
        resp = (api_call(url, 'post', config['debug'], data=postdata))
        token = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    if config['debug']:
        print("DEBUG: Token {} created, with value {}".
              format(token['name'], token['value']))

    return token


def destroy_master_token(user, repo, config, name):
    """Destroy a named master token in repo

       https://packagecloud.io/docs/api#resource_master_tokens_method_destroy

       DELETE /api/v1/repos/:user/:repo/master_tokens/:id
    """
    tokens = get_master_tokens(user, repo, config)

    for token in tokens:
        if token['name'] == name:
            print("Found token with name: %s" % name)
            try:
                url = "{}{}".format(config['domain_base'],
                                    token['paths']['self'])
                resp = (api_call(url, 'delete', config['debug']))
            except ValueError as ex:
                abort("Unexpected response from packagecloud API: "
                      "{}".format(ex.message))
            if resp.status_code == 204:
                print("Token destroyed, name: %s" % name)
                print("Result: %s" % resp)
            else:
                eprint("ERROR: Destroying token %s failed" % name)
                eprint("Result: %s" % resp)


###########################################################
# Packagecloud Read tokens                                #
# https://packagecloud.io/docs/api#resource_read_tokens   #
###########################################################
def get_read_tokens(mastertoken, config):
    """Lists all read tokens in repository for given master token

       https://packagecloud.io/docs/api#resource_read_tokens_method_index

       GET /api/v1/repos/:user/:repo/master_tokens/
           :master_token/read_tokens.json
    """
    mt_path = mastertoken['paths']['self']
    url = "{}{}/read_tokens.json".\
        format(config['domain_base'], mt_path)

    try:
        resp = (api_call(url, 'get', config['debug']))
        tokens = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return tokens['read_tokens']


def get_read_tokens_dict(mastertoken, config):
    """Get the complete read token dict for given master token

    """
    token_list = {}
    tokens = get_read_tokens(mastertoken, config)

    for token in tokens:
        if token['name']:
            token_list[token['name']] = token['value']
            if config['debug']:
                print("DEBUG: Found token {} with value {}".
                      format(token['name'], token['value']))

    return token_list


def create_read_token(mastertoken, config, name):
    """Create a named master token in repo

       https://packagecloud.io/docs/api#resource_read_tokens_method_create

       POST /api/v1/repos/:user/:repo/master_tokens/
            :master_token/read_tokens.json
    """
    mt_path = mastertoken['paths']['self']
    url = "{}{}/read_tokens.json".\
        format(config['domain_base'], mt_path)
    postdata = ("read_token[name]=%s" % name)

    try:
        resp = (api_call(url, 'post', config['debug'], data=postdata))
        token = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    if config['debug']:
        print("DEBUG: Token {} created, with value {}".
              format(token['name'], token['value']))
    return token['value']


def destroy_read_token(mastertoken, config, name):
    """Destroy a named master token in repo

       https://packagecloud.io/docs/api#resource_read_tokens_method_destroy

       DELETE /api/v1/repos/:user/:repo/master_tokens/:id
    """
    mt_path = mastertoken['paths']['self']
    tokens = get_read_tokens(mastertoken, config)

    for token in tokens:
        if token['name'] == name:
            print("Found token with name: %s" % name)
            try:
                url = "{}{}/read_tokens/{}".format(config['domain_base'],
                                                   mt_path, token['id'])
                resp = (api_call(url, 'delete', config['debug']))
            except ValueError as ex:
                abort("Unexpected response from packagecloud API: "
                      "{}".format(ex.message))
            if resp.status_code == 204:
                print("Token destroyed, name: %s" % name)
                print("Result: %s" % resp)
            else:
                eprint("ERROR: Destroying token %s failed" % name)
                eprint("Result: %s" % resp)


###########################################################
# Packagecloud Packages                                   #
# https://packagecloud.io/docs/api#resource_stats         #
###########################################################
def get_all_packages(user, repo, config):
    """List All Packages (not grouped by package version)

       https://packagecloud.io/docs/api#resource_packages_method_all

       GET /api/v1/repos/:user/:repo/packages.json
    """
    packages = {}
    url = "{}/repos/{}/{}/packages.json".format(config['url_base'], user, repo)

    try:
        resp = (api_call(url, 'get', config['debug']))
        packages = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return packages


def destroy_package(package, config):
    """Destroy named (rpm,deb,jar,python) package (remove from repository)

       https://packagecloud.io/docs/api#resource_packages_method_destroy

       DELETE /api/v1/repos/:user/:repo/:distro/:version/:package.:ext
    """
    url = "{}{}".format(config['domain_base'], package['destroy_url'])

    try:
        resp = (api_call(url, 'delete', config['debug']))
        resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return True


###########################################################
# Packagecloud Statistics                                 #
# https://packagecloud.io/docs/api#resource_stats         #
###########################################################
def get_dlcount(package, startdate, config):
    """Get download count for a given package from startdate to now.

       https://packagecloud.io/docs/api#resource_stats_method_downloads_count

       GET /api/v1/repos/:user/:repo/package/:type/:distro/:version/:package/
           :arch/:package_version/:release/stats/downloads/count.json
    """
    url = "{}{}?start_date={}".format(config['domain_base'],
                                      package['downloads_count_url'],
                                      startdate)

    try:
        resp = (api_call(url, 'get', config['debug']))
        dlcount = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return dlcount['value']


def get_dldetails(package, startdate, config):
    """Get download details (log entries) for a given package.

       https://packagecloud.io/docs/api#resource_stats_method_downloads_detail

       GET /api/v1/repos/:user/:repo/package/:type/:distro/:version/:package/
           :arch/:package_version/:release/stats/downloads/detail.json
    """
    url = "{}{}?start_date={}".format(config['domain_base'],
                                      package['downloads_detail_url'],
                                      startdate)

    try:
        resp = (api_call(url, 'get', config['debug']))
        dldetails = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return dldetails
