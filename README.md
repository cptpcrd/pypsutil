# pypsutil

[![PyPI](https://img.shields.io/pypi/v/pypsutil)](https://pypi.org/project/pypsutil)
[![Python Versions](https://img.shields.io/pypi/pyversions/pypsutil)](https://pypi.org/project/pypsutil)
[![Documentation Status](https://readthedocs.org/projects/pypsutil/badge/?version=latest)](https://pypsutil.readthedocs.io/en/latest/?badge=latest)
[![GitHub Actions](https://github.com/cptpcrd/pypsutil/workflows/CI/badge.svg?branch=master&event=push)](https://github.com/cptpcrd/pypsutil/actions?query=workflow%3ACI+branch%3Amaster+event%3Apush)
[![Cirrus CI](https://api.cirrus-ci.com/github/cptpcrd/pypsutil.svg?branch=master)](https://cirrus-ci.com/github/cptpcrd/pypsutil)
[![codecov](https://codecov.io/gh/cptpcrd/pypsutil/branch/master/graph/badge.svg)](https://codecov.io/gh/cptpcrd/pypsutil)

A partial reimplementation of psutil in pure Python using ctypes. Currently, only Linux, macOS, and the BSDs are supported, but Windows support is planned.

[Documentation](https://pypsutil.readthedocs.io/en/latest/)

## Example usage

`pypsutil`'s API is very similar to `psutil`'s:

```
>>> import pypsutil
>>> p = pypsutil.Process()
>>> p.pid
477967
>>> p
Process(pid=477967, name='python3', status='running', started='12:00:40')
>>> p.name()
'python3'
>>> p.exe()
'/usr/bin/python3.9'
>>> p.cwd()
'/tmp'
>>> p.cmdline()
['python3']
>>> p.terminal()
'/dev/pts/6'
>>> p.status()
<ProcessStatus.RUNNING: 'running'>
>>> p.ppid()
477771
>>> p.parent()
Process(pid=477771, name='bash', status='sleeping', started='12:00:33')
```

More information is available in the [documentation](https://pypsutil.readthedocs.io/en/latest/).
