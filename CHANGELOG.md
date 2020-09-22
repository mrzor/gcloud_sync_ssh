#### 1.0.0b4

User-facing:

- Support for removing vanishing instances
- Added `--debug-template` to help users troubleshoot / refine settings
  (It turned out to be quite convenient for testing as well)
- Support for multiple `-kw` assignments on the same keyword, in the cases where SSH
  allows multiple kwarg pairs for the same keyword, like `LocalForward`.

Internals:

- 95%+ test coverage
- Replaced icdiff dep by icdiff inspired code

#### 1.0.0b3

First (test.)PyPI release
