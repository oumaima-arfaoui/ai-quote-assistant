# Testing

This document explains how the automated tests of the project are organised, how to run them, and what they do and do not cover.

The guiding rule of the project is that **prices and totals are computed in code, never by the LLM, and nothing is ever sent**. The tests are built around protecting that rule, and around the places where a bug would silently produce a wrong quote.

## Running the tests

From the project root, with the virtual environment active:

```powershell
pytest                              # everything
pytest -v                           # one line per test
pytest tests/unit                   # unit tests only
pytest tests/integration            # integration tests only
pytest tests/unit/test_qualify.py   # one file
pytest -k "rerun"                   # tests whose name contains "rerun"
```

The suite needs **no network, no API key and no model call**. It runs in a few seconds and gives the same result every time. Run `pytest` to see the current number of tests.

## Layout

```
conftest.py                  shared fixtures (temporary database)
pytest.ini                   pytest configuration
tests/
  unit/                      one module at a time, no external services
    test_quote.py
    test_schema.py
    test_extract_logic.py
    test_qualify.py
    test_quote_html.py
    test_database.py
    test_fixture.py
  integration/               several modules working together
    test_pipeline.py
    test_selection_to_quote.py
```

### Configuration (`pytest.ini`)

- `testpaths = tests` makes a bare `pytest` look only in `tests/`.
- `pythonpath = .` adds the project root to the import path, so tests can write `import quote` or `import database` directly.
- A `DeprecationWarning` filter hides harmless third-party warnings.

If you ever see `ModuleNotFoundError` when running pytest, check that you launched it from the project root.

### Shared fixture (`conftest.py`)

`temp_db` gives each test its own empty SQLite database:

1. pytest creates a temporary folder for the test (`tmp_path`);
2. `database.DB_PATH` is pointed at a new file in that folder (`monkeypatch`, restored automatically afterwards);
3. `init_db()` creates the tables.

Because of this, **no test ever touches the real `data/agent.db`**. Any test that reads or writes the database must use `temp_db` (directly, or through another fixture that depends on it).

## Unit tests

| File | What it protects |
|---|---|
| `test_quote.py` | Price logic: every price comes from the catalog item, unknown quantity leaves the total empty, totals with two VAT rates, incomplete quotes are flagged, `set_quantity` and `set_manual_price` (including refusals and the guarantee that the original quote is not modified). |
| `test_schema.py` | `QuoteRequest` defaults, the validator that turns junk strings (`"."`, `"null"`, `"N/A"`, `"inconnu"`, whitespace...) into `None` on every text field, strict enums for work type and urgency, numeric surface. |
| `test_extract_logic.py` | `compute_missing` (base fields, `work_types`, surface required for painting and renovation and listed only once, non-quote messages have nothing missing) and `build_questions` (order, unknown fields ignored). Also checks that every field that can be missing has a question. |
| `test_qualify.py` | Completeness score for 0 to 6 missing fields, and the priority rules: non-quote is `aucune`, urgent is `haute`, score of 70 or more is `moyenne`, otherwise `basse`. |
| `test_quote_html.py` | The downloadable draft quote: euro and number formatting, the draft banner, dashes for missing values, the "incomplete quote" warning, the client block, and **HTML escaping** of every text. Uses small stand-in objects so it does not depend on `quote.py`. |
| `test_database.py` | Upsert keeps one row per source file, **a re-run keeps `validé` and `rejeté` decisions**, ordering of the request list, search, save and reload of quote / final reply / generated quote, and the correction rule (a correction equal to the original is removed). |
| `test_fixture.py` | A single check that `temp_db` really isolates the database and creates the tables. |

## Integration tests

### `test_pipeline.py`: from message to saved request

Runs the real `process_text` and `process` with the LLM replaced by fakes:

- `FakeExtractor` stands in for the extraction chain. It returns a prepared `QuoteRequest` or raises an error.
- `FakeDrafter` stands in for `draft_reply`. It can fail a chosen number of times before answering.
- `time.sleep` is disabled, so the retry tests finish instantly.
- The database is the temporary one.

Covered behaviours: a complete request, an incomplete request with its missing fields, urgent priority, a message that is not a quote request (no reply drafted), extraction failure (saved as `à vérifier` for manual review), the draft reply failing three times (left empty for the professional), succeeding on the third try, empty messages refused, a re-run keeping a validated decision, and reading a file by path.

### `test_selection_to_quote.py`: from LLM selection to priced quote

Uses the **real `catalog.csv`** and builds a `Selection` by hand, the way the LLM would return it. No LLM and no vector search are involved.

Covered behaviours: every price, label, unit and VAT rate comes from the catalog; hand-computed totals; unknown ids dropped; duplicate ids keep only the first line; unknown quantity leaves the line unpriced and the quote incomplete; out-of-catalog work becomes an unpriced line; an empty selection; the professional entering a quantity; the professional pricing an out-of-catalog line by hand (flagged as manual).

The test finds the catalog through an absolute path built from the test file's location, so it works from any working directory.

## Design choices

- **Fakes instead of real models.** Real LLM calls are slow, cost money and vary between runs, which makes tests flaky. Tests use fakes so that a failure always means a code change broke something.
- **Public functions only.** Tests call the public functions of each module and never read private details, so internal refactoring does not break them.
- **One behaviour per test**, with the name describing the behaviour (`test_rerun_keeps_a_final_decision`).
- **Parametrized tests** (`@pytest.mark.parametrize`) cover several inputs with one test body, for example every junk string or every work type.
- **Hand-computed expected values.** Expected totals are written out as numbers, not recomputed with the same formula as the code.

## What is not covered by pytest

- **LLM quality.** Whether the model extracts the right fields or picks the right catalog items varies between runs, so it is measured separately by the evaluation scripts (extraction score, matching evaluation set, retrieval questions for the general conditions). Those are quality measurements, not pass/fail tests.
- **Real model calls and the vector store.** The semantic search over the catalog, the embeddings and the general-conditions retrieval are not exercised by the suite.
- **`select_lines`.** Its second filter (dropping ids that are not among the retrieved candidates) is not covered, because it needs a fake selector and a fake candidate search.
- **The Streamlit interface.** Not tested automatically. It is checked by hand.
- **PDF reading.** Known limitation: the reader drops some spaces; there is no test for it.

## Things that will change on purpose

- `test_default_company_is_still_the_placeholder` documents that the company name is still a placeholder. When the name moves to a config file, this test must be updated.
- Three tests in `test_selection_to_quote.py` use hand-computed amounts based on the current prices of `PEINT-001`, `PEINT-002` and `PLOMB-001`. If those prices change in `catalog.csv`, the tests fail on purpose, and the expected numbers must be recomputed.
- If more required fields are added, `TOTAL_CHECKS` in `qualify.py` and the score table in `test_qualify.py` need to follow.

## Adding a test

1. Put it in `tests/unit/` if it checks one module, or `tests/integration/` if several modules work together.
2. Name the file `test_<topic>.py` and each function `test_<behaviour>`.
3. If it touches the database, take `temp_db` as an argument.
4. If it would call an LLM, replace the call with a fake using `monkeypatch.setattr` on the module that uses it, as in `test_pipeline.py`.
5. Run the new file alone first, then the whole suite.