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

* ``copypackages`` - copy packages between repos
* ``downloadpackages`` - download packages interactively or by filters
* ``listpackages`` - list packages in given repo
* ``promotepackages`` - promote packages interactively or by filters
* ``yankpackages`` - yank packages interactively or by filters

### Usage

Configure your API token and username in a config file (see ``example.cfg``).
Use ``-h`` or ``--help`` for options:

```
$ copypackages --help
$ downloadpackages --help
$ listpackages --help
$ promotepackages --help
$ yankpackages --help
```

Then run the tools like so:

```
$ copypackages --config example.cfg --srcrepo sourcerepo --destrepo destinationrepo
$ downloadpackages --config example.cfg --srcrepo sourcerepo
$ listpackages --config example.cfg --srcrepo sourcerepo
$ promotepackages --config example.cfg --srcrepo sourcerepo --destrepo destinationrepo
$ yankpackages --config example.cfg --srcrepo clearthisrepo
```

