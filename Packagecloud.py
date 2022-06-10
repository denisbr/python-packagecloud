#!/usr/bin/env python
"""Packagecloud API module

   Implements functions for working with:
   * master and read-tokens
   * packages
   * stats
   * stream based download
   * rpm/deb/dsc package push

   Packagecloud API reference docs:
   https://packagecloud.io/docs/api
"""


import shutil
import sys
import time

from os.path import dirname
from os.path import splitext
from requests import ConnectionError
from requests.exceptions import RequestException
from requests import HTTPError
from requests import post
from requests import Request
from requests import Session
from requests import Timeout
from requests_toolbelt import MultipartEncoder


def eprint(*args, **kwargs):
    """Print to stderr"""
    print(*args, file=sys.stderr, **kwargs)


def abort(errstr, errcode=1):
    """Print error and exit with errcode"""
    eprint(errstr)
    sys.exit(errcode)


def api_call(url, method, debug, **kwargs):
    """Generic method to make HTTP requests to the packagecloud API

       Will retry on connection error or timeout, until max retries
    """
    resp = None
    attempt = 0
    maxattempts = 3
    req = Request(method.upper(), url, **kwargs)

    if debug:
        print("DEBUG: Request ({}) {}".format(method.upper(), url))

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
    postdata = ("master_token[name]={}".format(name))

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
            print("Found token with name: {}".format(name))
            try:
                url = "{}{}".format(config['domain_base'],
                                    token['paths']['self'])
                resp = (api_call(url, 'delete', config['debug']))
            except ValueError as ex:
                abort("Unexpected response from packagecloud API: "
                      "{}".format(ex.message))
            if resp.status_code == 204:
                print("Token destroyed, name: {}".format(name))
                print("Result: {}" % resp)
            else:
                eprint("ERROR: Destroying token {} failed".format(name))
                eprint("Result: {}".format(resp))

    return True


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
    postdata = ("read_token[name]={}".format(name))

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
            print("Found token with name: {}".format(name))
            try:
                url = "{}{}/read_tokens/{}".format(config['domain_base'],
                                                   mt_path, token['id'])
                resp = (api_call(url, 'delete', config['debug']))
            except ValueError as ex:
                abort("Unexpected response from packagecloud API: "
                      "{}".format(ex.message))
            if resp.status_code == 204:
                print("Token destroyed, name: {}".format(name))
                print("Result: {}".format(resp))
                return token['value']
            else:
                eprint("ERROR: Destroying token {} failed".format(name))
                eprint("Result: {}".format(resp))


###########################################################
# Packagecloud Packages                                   #
# https://packagecloud.io/docs/api#resource_stats         #
###########################################################
def get_all_packages(user, repo, config):
    """List All Packages (not grouped by package version)

       https://packagecloud.io/docs/api#resource_packages_method_all

       GET /api/v1/repos/:user/:repo/packages.json
    """
    packages = []
    total = 1
    fetched = 0
    offset = 1

    while fetched < total:
        url = "{}/repos/{}/{}/packages.json?page={}".format(config['url_base'],
                                                            user, repo, offset)
        try:
            resp = (api_call(url, 'get', config['debug']))
            packages = packages + resp.json()
            total = int(resp.headers['Total'])
            perpage = int(resp.headers['Per-Page'])
            fetched += perpage
            offset += 1

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


def promote_package(package, repouser, destination, config):
    """Promote named package to destination repo

       https://packagecloud.io/docs/api#resource_packages_method_promote

       POST /api/v1/repos/:user/:repo/:distro/:version/:package/promote.json
    """
    url = "{}{}".format(config['domain_base'], package['promote_url'])
    postdata = ("destination={}/{}".format(repouser, destination))

    try:
        resp = (api_call(url, 'post', config['debug'], data=postdata))
        result = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return result


def download_package(package, filepath, config):
    """Detect package type and call the correct function"""
    pkgtype = package['type']

    if pkgtype in ['dsc']:
        result = download_srcpackage(package, filepath, config)
    else:
        result = download_binpackage(package, filepath, config)

    return result


def download_binpackage(package, filepath, config):
    """Download named package to filepath"""
    resp = None
    req = Request('GET', package['download_url'])
    local_filename = "{}/{}".format(filepath, package['filename'])

    if config['debug']:
        print("DEBUG: Request ({}) {}".format('GET', package['download_url']))

    try:
        resp = Session().send(
            Session().prepare_request(req), verify=True, stream=True)
        with open(local_filename, 'wb') as lfile:
            shutil.copyfileobj(resp.raw, lfile)
        resp.raise_for_status()
    except (HTTPError, ConnectionError, Timeout, IOError) as ex:
        abort(ex.message)

    return local_filename


def download_srcpackage(package, filepath, config):
    """Download named debian source package (dsc) and files to filepath

       Post the .dsc file to the contents endpoint, then post the set of
       files to the packages endpoint.

       https://packagecloud.io/docs/api#resource_packages_method_contents
       https://packagecloud.io/docs/api#resource_packages_method_create

       POST /api/v1/repos/:user/:repo/packages/contents.json
    """
    filename = download_binpackage(package, filepath, config)

    conttype = "application/x-dsc"
    distid = str(get_distid('dsc', package['distro_version'], config))

    url = "{}/repos/{}/{}/packages/contents.json".format(config['url_base'],
                                                         config['repouser'],
                                                         config['srcrepo'])

    menc = MultipartEncoder(fields={'package[distro_version_id]': distid,
                                    'package[package_file]':
                                    (filename, open(filename, 'rb'),
                                     conttype)})

    if config['debug']:
        print("DEBUG: Request ({}) {}".format('POST', url))
        print("DEBUG: {}".format(menc))

    try:
        resp = post(url, data=menc,
                    headers={'Content-Type': menc.content_type})
        resp.raise_for_status()
        result = resp.json()
    except (HTTPError, ConnectionError, Timeout, IOError) as ex:
        abort(ex.message)

    for srcfile in result['files']:
        resp = None
        dl_url = package['download_url'].replace('/download',
                                                 '/files/{}/download'.
                                                 format(srcfile['filename']))
        req = Request('GET', dl_url)
        local_filename = "{}/{}".format(filepath, srcfile['filename'])

        if config['debug']:
            print("DEBUG: Request ({}) {}".
                  format('GET', dl_url))

        try:
            resp = Session().send(
                Session().prepare_request(req), verify=True, stream=True)
            with open(local_filename, 'wb') as lfile:
                shutil.copyfileobj(resp.raw, lfile)
            resp.raise_for_status()
        except (HTTPError, ConnectionError, Timeout, IOError) as ex:
            abort(ex.message)
    return filename


def create_package(user, repo, filename, distro, config):
    """Detect package type and call the correct function"""
    pkgtype = get_pkgtype(filename)

    if pkgtype in ['rpm', 'deb']:
        result = create_binpackage(user, repo, filename, distro, config)
    elif pkgtype in ['dsc']:
        result = create_srcpackage(user, repo, filename, distro, config)
    else:
        abort('Unsupported packagetype {}'.format(pkgtype))

    return result


def create_binpackage(user, repo, filename, distro, config):
    """Upload filename as new package to destination repo

       https://packagecloud.io/docs/api#resource_packages_method_create

       POST /api/v1/repos/:user/:repo/packages.json
    """
    pkgtype = get_pkgtype(filename)
    conttype = "application/x-{}".format(pkgtype)
    distid = str(get_distid(pkgtype, distro, config))

    url = "{}/repos/{}/{}/packages.json".format(config['url_base'],
                                                user, repo)

    menc = MultipartEncoder(fields={'package[distro_version_id]': distid,
                                    'package[package_file]':
                                    (filename, open(filename, 'rb'),
                                     conttype)})

    if config['debug']:
        print("DEBUG: Request ({}) {}".format('POST', url))
        print("DEBUG: {}".format(menc))

    try:
        resp = post(url, data=menc,
                    headers={'Content-Type': menc.content_type})
        resp.raise_for_status()
        result = resp.json()
    except (HTTPError, ConnectionError, Timeout, IOError) as ex:
        abort(ex.message)

    return result


def create_srcpackage(user, repo, filename, distro, config):
    """Upload filename.dsc as new sourcepackage to destination repo.

       Post the .dsc file to the contents endpoint, then post the set of
       files to the packages endpoint.

       https://packagecloud.io/docs/api#resource_packages_method_contents
       https://packagecloud.io/docs/api#resource_packages_method_create

       POST /api/v1/repos/:user/:repo/packages/contents.json
       POST /api/v1/repos/:user/:repo/packages.json
    """
    conttype = "application/x-dsc"
    distid = str(get_distid('dsc', distro, config))
    fpath = dirname(filename)

    url = "{}/repos/{}/{}/packages/contents.json".format(config['url_base'],
                                                         user, repo)

    menc = MultipartEncoder(fields={'package[distro_version_id]': distid,
                                    'package[package_file]':
                                    (filename, open(filename, 'rb'),
                                     conttype)})

    if config['debug']:
        print("DEBUG: Request ({}) {}".format('POST', url))
        print("DEBUG: {}".format(menc))

    try:
        resp = post(url, data=menc,
                    headers={'Content-Type': menc.content_type})
        resp.raise_for_status()
        result = resp.json()
    except (HTTPError, ConnectionError, Timeout, IOError) as ex:
        abort(ex.message)

    filelist = [('package[distro_version_id]', distid),
                ('package[package_file]',
                 (filename, open(filename, 'rb'), conttype))]

    for srcfile in result['files']:
        srcfilename = '{}/{}'.format(fpath, srcfile['filename'])
        filelist.append(('package[source_files][]',
                         (srcfilename,
                          open(srcfilename, 'rb'),
                          'application/x-gzip')))

    url = "{}/repos/{}/{}/packages.json".format(config['url_base'],
                                                user, repo)

    menc = MultipartEncoder(fields=filelist)

    if config['debug']:
        print("DEBUG: Request ({}) {}".format('POST', url))
        print("DEBUG: {}".format(menc))

    try:
        resp = post(url, data=menc,
                    headers={'Content-Type': menc.content_type})
        resp.raise_for_status()
        result = resp.json()
    except (HTTPError, ConnectionError, Timeout, IOError) as ex:
        abort(ex.message)

    return result


###########################################################
# Packagecloud Statistics                                 #
# https://packagecloud.io/docs/api#resource_stats         #
###########################################################
def get_dlcount(package, startdate, config, enddate=False):
    """Get download count for a given package from startdate to now.

       https://packagecloud.io/docs/api#resource_stats_method_downloads_count

       GET /api/v1/repos/:user/:repo/package/:type/:distro/:version/:package/
           :arch/:package_version/:release/stats/downloads/count.json
    """
    if enddate:
        url = "{}{}?start_date={}&end_date={}".\
            format(config['domain_base'],
                   package['downloads_count_url'],
                   startdate, enddate)
    else:
        url = "{}{}?start_date={}".\
            format(config['domain_base'],
                   package['downloads_count_url'],
                   startdate)

    try:
        resp = (api_call(url, 'get', config['debug']))
        dlcount = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return dlcount['value']


def get_dldetails(package, startdate, config, enddate=False):
    """Get download details (log entries) for a given package.

       https://packagecloud.io/docs/api#resource_stats_method_downloads_detail

       GET /api/v1/repos/:user/:repo/package/:type/:distro/:version/:package/
           :arch/:package_version/:release/stats/downloads/detail.json
    """
    if enddate:
        url = "{}{}?start_date={}&end_date={}".\
            format(config['domain_base'],
                   package['downloads_detail_url'],
                   startdate, enddate)
    else:
        url = "{}{}?start_date={}".\
            format(config['domain_base'],
                   package['downloads_detail_url'],
                   startdate)

    try:
        resp = (api_call(url, 'get', config['debug']))
        dldetails = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return dldetails


def get_dlseries(package, startdate, interval, config, enddate=False):
    """Get download series for a given package and interval

       https://packagecloud.io/docs/api#resource_stats_method_downloads_series

       GET /api/v1/repos/:user/:repo/package/:type/:distro/:version/:package/
           :arch/:package_version/:release/stats/downloads/series/:interval.json
    """

    dl_series_url = package['downloads_series_url'].replace("daily", interval)
    if enddate:
        url = "{}{}?start_date={}&end_date={}".\
            format(config['domain_base'],
                   dl_series_url,
                   startdate, enddate)
    else:
        url = "{}{}?start_date={}".\
            format(config['domain_base'],
                   dl_series_url,
                   startdate)

    try:
        resp = (api_call(url, 'get', config['debug']))
        dlseries = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return dlseries['value']


########################################################################
# Packagecloud Distributions                                           #
# https://packagecloud.io/docs/api#resource_distributions_method_index #
########################################################################
def get_distributions(config):
    """Get index of known distributions from Packagecloud

       https://packagecloud.io/docs/api#resource_distributions_method_index

       GET /api/v1/distributions.json
    """
    url = "{}/{}".format(config['url_base'], "distributions.json")

    try:
        resp = (api_call(url, 'get', config['debug']))
        distributions = resp.json()
    except ValueError as ex:
        abort("Unexpected response from packagecloud API: "
              "{}".format(ex.message))

    return distributions


def get_distid(pkgtype, distslug, config):
    """Get id of given distribution slug"""

    distindex = get_distributions(config)
    distributions = distindex[pkgtype]
    distname, codename = distslug.split('/')

    if config['debug']:
        print("DEBUG: Pkgtype: {} Distribution: {} Codename: {}".
              format(pkgtype, distname, codename))

    for dist in distributions:
        if dist['index_name'] == distname:
            for ver in dist['versions']:
                if ver['index_name'] == codename:
                    return ver['id']

    abort("No distribution id found for: {}".format(distslug))


########################################################################
# Utility functions                                                    #
########################################################################
def get_pkgtype(filename):
    """Infer packagetype given a filename"""

    extension = splitext(filename)[1][1:]
    if extension in ['rpm', 'deb', 'dsc']:
        return extension
    else:
        abort("Unsupported packagetype: {} for file: {}".
              format(extension, filename))


def fmt_pkg(repouser, srcrepo, package):
    """Pretty print package line"""

    return ('{user}/{repo}/{filename:<65} {distro:<20} {timestamp:>16}'.format(
        user=repouser, repo=srcrepo, filename=package['filename'],
        distro=package['distro_version'], timestamp=package['created_at']))


def show_packagelist(user, repo, packages, distro=False, version=False,
                     name=False, match=False, pkgtype=False):
    """Display all matching packages in a pretty list"""

    print('Currently {}/{} contains these matching packages:'.format(
        user, repo))

    numpkgs = 0
    for package in packages:
        if (distro and not package['distro_version'] == distro) or \
           (version and not package['version'] == version) or \
           (name and not package['name'] == name) or \
           (pkgtype and not package['type'] == pkgtype) or \
           (match and match not in package['filename']):
            continue

        print(fmt_pkg(user, repo, package))
        numpkgs += 1

    print("Repo contains {} matching packages.".format(numpkgs))


def detect_distro(filename):
    """Simple distro detection from filename

       Only works when the distro code is part of the filename
    """
    if '.rpm' in filename:
        if 'el6' in filename:
            distro = 'el/6'
        elif 'el7' in filename:
            distro = 'el/7'
        else:
            distro = False
    elif '.deb' in filename:
        if 'precise' in filename:
            distro = 'ubuntu/precise'
        elif 'trusty' in filename:
            distro = 'ubuntu/trusty'
        elif 'xenial' in filename:
            distro = 'ubuntu/xenial'
        elif 'wheezy' in filename:
            distro = 'debian/wheezy'
        elif 'jessie' in filename:
            distro = 'debian/jessie'
        elif 'stretch' in filename:
            distro = 'debian/stretch'
        else:
            distro = False
    else:
        distro = False
    return distro
