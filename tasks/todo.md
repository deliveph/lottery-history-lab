# Tasks

- [x] Task 1: Parse and validate both API response formats
  - Acceptance: normalized valid records; malformed counts/ranges rejected
  - Verify: `python -m unittest tests.test_parsers -v`
  - Files: `lottery_lab/models.py`, `lottery_lab/parsers.py`, `tests/test_parsers.py`
- [x] Task 2: Paginate, deduplicate, and persist complete history
  - Acceptance: final advertised page fetched; JSON/CSV created; round trip works
  - Verify: `python -m unittest tests.test_fetchers tests.test_storage -v`
  - Files: `lottery_lab/fetchers.py`, `lottery_lab/storage.py`, related tests
- [x] Task 3: Generate deterministic valid candidate tickets
  - Acceptance: five distinct tickets per game; ranges/counts valid; seed repeats
  - Verify: `python -m unittest tests.test_simulation -v`
  - Files: `lottery_lab/simulation.py`, `tests/test_simulation.py`
- [ ] Task 4: Provide documented online/offline CLI
  - Acceptance: one command fetches and prints; offline reuses cache; disclaimer shown
  - Verify: unit suite, compile check, and real endpoint run
  - Files: `lottery_lab/cli.py`, `lottery_lab/__main__.py`, `README.md`
