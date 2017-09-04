# Packagecloud

Python Module for Packagecloud

Implements functions for working with:
* master and read-tokens
* packages
* stats

Packagecloud API reference docs:
https://packagecloud.io/docs/api

## Usage

Example of how to destroy all packages in a given repo:

```python
#!/usr/bin/env python
"""Destroy All Packages in myrepouser/myrepo"""
from __future__ import print_function

from PackageCloud import destroy_packages
from PackageCloud import get_all_packages


def configure():
    """Configure"""
    token = "INSERT TOKEN FROM PACKAGECLOUD API SETTINGS"
    http_scheme = "https"
    api_domain = "packagecloud.io"
    api_version = "v1"

    conf = {
        'domain_base': '{}://{}:@{}'.format(
            http_scheme, token, api_domain),
        'url_base': '{}://{}:@{}/api/{}'.format(
            http_scheme, token, api_domain, api_version),
        'token': token,
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
