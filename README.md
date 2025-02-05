# GNSS and Navigation modules

## Installation

To make sure that the extensions are installed along with the package, run

`pip install pygnss`

## Modules

### Logger

Example of how to use the logger module:

```python
>>> from pygnss import logger
>>> logger.set_level("DEBUG")
>>> logger.debug("Debug message")
2020-05-05 18:23:55,688 - DEBUG    - Debug message
>>> logger.warning("Warning message")
2020-05-05 18:24:11,327 - WARNING  - Warning message
>>> logger.info("Info message")
2020-05-05 18:24:26,021 - INFO     - Info message
>>> logger.error("Error message")
2020-05-05 18:24:36,090 - ERROR    - Error message
>>> logger.critical("Critical message")
2020-05-05 18:24:43,562 - CRITICAL - Critical message
>>> logger.exception("Exception message", ValueError("Exception message")
2020-05-05 18:25:11,360 - CRITICAL - Exception message
ValueError: Exception message
Traceback (most recent call last):
  ...
ValueError: Exception message
```
