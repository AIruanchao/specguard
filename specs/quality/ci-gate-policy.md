# CI Gate Policy

This policy defines the unified seven-stage CI gate contract used by P0 systems. Every repository that adopts the SDD CI baseline must publish machine-readable evidence for these stages and keep failures explicit.

## Stage 1: Checkout And Environment

The CI job must check out the repository and install the declared runtime version. Python systems use Python 3.11. Next.js systems use Node.js 20.

Evidence requirements:
- repository ref
- runtime version
- dependency install command and exit code

## Stage 2: Dependency Integrity

The CI job must install dependencies from the repository manifest or lockfile without modifying project files.

Evidence requirements:
- package manager command
- dependency manifest path
- install exit code

## Stage 3: Static Quality

The CI job must run the available static quality checks for the system type.

Evidence requirements:
- lint command when configured
- type-check command when configured
- syntax compile command for Python systems when available

## Stage 4: Unit Tests

The CI job must run deterministic unit tests without requiring production secrets, external write access, or live production systems.

Evidence requirements:
- test command
- passed, failed, skipped, and error counts
- exit code

## Stage 5: Coverage Baseline

The CI job must collect coverage when the project has a supported test runner. Coverage failures must report the measured value and threshold.

Evidence requirements:
- coverage command
- coverage report path
- total line coverage percentage
- threshold when enforced

## Stage 6: Build Or Package

The CI job must verify that the application can build or package when the project exposes a build command. Python services must at least pass bytecode compilation for their entrypoint when present.

Evidence requirements:
- build or compile command
- artifact path when generated
- exit code

## Stage 7: Evidence Publication

The CI job must publish or retain the evidence needed for independent review. Coverage XML, test summaries, and CI evidence JSON are accepted artifacts.

Evidence requirements:
- artifact name
- artifact path
- schema version
- overall status

## Status Rules

A gate is `pass` only when the command was executed and returned exit code 0. A gate is `fail` when the command returned non-zero. A gate is `blocked` when the command could not run because the environment lacked an authorized prerequisite, such as missing secrets or unavailable SSH access.
