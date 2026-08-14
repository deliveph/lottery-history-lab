# Implementation Plan: Lottery History Lab

## Overview

Implement a standard-library Python CLI in thin, testable slices: normalize API
responses, paginate and cache complete history, then generate transparent weighted
random candidates from the cached draw records.

## Architecture Decisions

- Use one `Draw` record for both lotteries, with game-specific rules kept in a
  small configuration mapping.
- Isolate HTTP/JSONP handling from pure parsers so all logic is unit-testable.
- Treat simulation as weighted sampling without replacement, not prediction.
- Prefer fresh online data; allow explicit offline cache use and clear failures.

## Task List

### Phase 1: Contracts and parsing

- [x] Define draw/rule records and response parser tests.
- [x] Implement parsers and validation for both response formats.

### Checkpoint: Parsing

- [x] Parser tests pass for valid and malformed fixtures.

### Phase 2: Fetch and storage

- [x] Add pagination tests and HTTP client with required headers/timeouts.
- [x] Add JSON/CSV storage and round-trip tests.

### Checkpoint: Data pipeline

- [x] Unit tests pass and live first-page probes parse correctly.

### Phase 3: Simulation and CLI

- [x] Add seeded ticket-generation tests and implementation.
- [x] Add CLI orchestration, disclaimer, README, and offline mode.

### Checkpoint: Complete

- [x] Full tests and compile check pass.
- [x] Online end-to-end run writes both histories and prints five tickets each.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Upstream WAF rejects script requests | High | Browser-like fixed headers, timeout, actionable error, explicit cache mode |
| API schema changes | High | Strict parsing errors and response-shaped regression fixtures |
| “Simulation” interpreted as prediction | Medium | CLI and docs disclaimer plus model explanation |
| Very old draws use different rules | Medium | Validate current configured ranges and report the bad issue |

## Open Questions

None for the requested CLI scope.
