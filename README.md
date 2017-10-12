# Packagecloud

Python Module for Packagecloud

Implements functions for working with:
* master and read-tokens
* packages
* stats

Packagecloud API reference docs:
https://packagecloud.io/docs/api

## Usage

Minimal example of how to destroy all packages in a given repo:

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

## Tools

A handful of CLI tools are bundled in this repo:

* ``listpackages`` - list packages in given repo
* ``yankpackages`` - yank packages interactively or by filters
* ``promotepackages`` - promote packages interactively or by filters
* ``downloadpackages`` - (batch) download packages interactively or by filters

### Usage

Configure your API token and username in a config file (see ``example.cfg``).
Then run the tools like so:

```
$ listpackages --config example.cfg --srcrepo myrepo --help
$ yankpackages --config example.cfg --srcrepo myrepo --help
$ promotepackages --config example.cfg --srcrepo myrepo --help
$ downloadpackages --config example.cfg --srcrepo myrepo --help
```

