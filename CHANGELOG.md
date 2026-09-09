# Changelog

## Unreleased

### Added

- Add validated context-aware inputs to `iching`: official draw time, casting
  timestamp, lunar birth date/time, location, coordinates, direction, and an
  optional wealth direction.
- Print every normalized context value so contextual runs are auditable and
  reproducible.

### Changed

- Use `21:25` for Super Lotto and `21:15` for Double Color Ball as the default
  draw times in contextual I Ching generation.

## 0.2.0 - 2026-08-14

### Added

- Add reproducible low-overlap portfolio generation through `--mode coverage`.
- Balance ball usage across tickets and penalize repeated pairs and obvious patterns.

## 0.1.0 - 2026-08-14

### Added

- Fetch, validate, and cache complete Super Lotto and Double Color Ball history.
- Generate seeded history-weighted entertainment-only candidate tickets.
