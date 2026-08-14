# Spec: Lottery History Lab

## Objective

Build a local command-line application that downloads all currently available
Super Lotto (大乐透) and Double Color Ball (双色球) draw history from the
official endpoints supplied by the user, stores normalized data locally, and
generates five entertainment-only candidate tickets for each lottery.

## Tech Stack

- Python 3.12+
- Python standard library only at runtime
- `unittest` for automated tests

## Commands

- Fetch and generate: `python -m lottery_lab run`
- Generate from cache: `python -m lottery_lab generate --offline`
- Test: `python -m unittest discover -s tests -v`
- Static compile check: `python -m compileall -q lottery_lab tests`

## Project Structure

- `lottery_lab/`: fetchers, parsers, storage, simulation, and CLI
- `tests/`: unit tests with captured response-shaped fixtures
- `data/`: generated JSON and CSV history files (not committed)
- `tasks/`: implementation plan and progress
- `docs/`: specification and model explanation

## Code Style

Use typed, small functions and immutable draw records:

```python
def parse_numbers(value: str, expected: int) -> tuple[int, ...]:
    numbers = tuple(int(part) for part in value.split())
    if len(numbers) != expected:
        raise ValueError(f"expected {expected} numbers")
    return numbers
```

## Testing Strategy

- Unit-test API parsing, pagination metadata, validation, storage round trips,
  deterministic seeded generation, number ranges, uniqueness, and ticket count.
- Keep external network calls out of the unit suite.
- Finish with a real end-to-end run against both supplied endpoints.

## Boundaries

- Always: validate upstream data, use timeouts, identify requests with normal
  browser headers, keep simulations reproducible with an optional seed, and
  show a no-prediction/no-guarantee disclaimer.
- Ask first: add third-party dependencies or build a browser UI.
- Never: claim historical draws improve mathematical jackpot odds, bypass access
  controls, store secrets, or silently replace a failed download with stale data.

## Success Criteria

- Both endpoints are paginated until their advertised final page.
- Every normalized draw has issue, date, correctly ranged front/red and back/blue
  numbers, and duplicate issues are removed.
- History is written to JSON and CSV under `data/`.
- The CLI emits exactly five valid, distinct tickets per lottery by default.
- `--offline` works from the saved JSON files and `--seed` is reproducible.
- Tests, compile check, and one real online run pass.

## Open Questions

None. A web UI and scheduled refresh are intentionally out of scope.
