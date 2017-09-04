# python-packagecloud
Python Package for Packagecloud

Implements functions for working with:
* master and read-tokens
* packages
* stats

Packagecloud API reference docs:
https://packagecloud.io/docs/api

## Usage

Example of how to purge all packages in a given repo:

```
#!/usr/bin/env python
"""Destroy All Packages"""
from __future__ import print_function

from PackageCloud import destroy_packages
from PackageCloud import get_all_packages


def configure():
    """Configure"""
    pkgcloud_token = "INSERT TOKEN FROM PACKAGECLOUD API SETTINGS"
    pkgcloud_http_scheme = "https"
    pkgcloud_api_domain = "packagecloud.io"
    pkgcloud_api_version = "v1"

    conf = {
        'domain_base': '{}://{}:@{}'.format(
            pkgcloud_http_scheme, pkgcloud_token, pkgcloud_api_domain),
        'url_base': '{}://{}:@{}/api/{}'.format(
            pkgcloud_http_scheme, pkgcloud_token, pkgcloud_api_domain,
            pkgcloud_api_version),
        'token': pkgcloud_token,
        'debug': True
    }

    return conf


def main():
    """Main"""
    conf = configure()

    packages = get_all_packages("myrepouser", "myreponame", conf)
    for package in packages:
        print(package['destroy_url'])
        destroy_package(package, conf)

main()
```
