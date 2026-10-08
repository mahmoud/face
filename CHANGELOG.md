# face Changelog

## Unreleased

- Report malformed flagfile quoting as a command-line error with the file
  and line number, including nested flagfiles.
- Accept `multi='overwrite'` as an undocumented alias for `multi='override'`,
  matching a longstanding typo in the `Flag` docstring
- Fix the `Flag` docstring to spell the shortcut `'override'`, and drop the
  bool shortcuts from the invalid-`multi` error message in favor of the three
  canonical names
- Build and lint packages in CI with
  `hynek/build-and-inspect-python-package`, adding a `Package` job to the test
  workflow and sourcing the publish workflow's version check from built
  package metadata

## 26.0.1

_(June 17, 2026)_

- Add subcommand grouping via `CommandGroup` class and `group` parameter
- Fix short command display in help output
- Fix `get_minimal_executable` cross-drive crash on Windows
- Fix `test_minimal_exe` for Windows environments
- Migrate build system from setuptools to flit
- Modernize CI: switch to uv and tox-uv, add Codecov integration
- Add GitHub Actions publish workflow with OIDC trusted publishing
- Drop Python 3.8 and 3.9 support (now requires >=3.10)
- Add Python 3.14 support
- Modernize codebase: f-strings, keyword-only arguments, type hints
- Flesh out documentation with comprehensive usage guides
