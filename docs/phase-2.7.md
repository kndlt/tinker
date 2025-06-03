# Tinker - Phase 2.7

Tinker currently does not have any way to react the the stdout/stderr.

We should look into how it can course correct when problems are found. It should have ability read std outputs and replan accordingly.

## Tasks

- [x] Add `analyze_command_result()` function to analyze stdout/stderr from failed commands
- [x] When commands fail, ask AI to suggest fixes based on the error output
- [x] Give user options: retry with suggested fix, skip command, or abort task
- [x] Test with common failure scenarios (missing packages, permissions, network issues)