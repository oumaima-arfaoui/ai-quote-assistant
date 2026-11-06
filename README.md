# Quote Request AI Agent (practice exercise)

An AI assistant for a building trades company. It reads incoming quote requests, extracts the key information, detects what is missing, and prepares a draft reply and a draft quote. **A human validates everything: nothing is ever sent.**

This is a learning project. The company (BatiPro Services), the requests and the catalog are fictional. The interface and the generated texts are in French.

## What it does

1. **Extraction**: an LLM turns a free-text message into a structured record (name, contact, site address, type of work, description, surface, urgency, availability).
2. **Qualification**: the code lists the missing fields (some work types require extra fields, for example a surface for painting), computes a completeness score and a priority (haute / moyenne / basse).
3. **Draft reply**: the LLM writes a French reply that asks for the missing information (no prices, no commitments).
4. **Catalog matching**: a semantic search finds candidate services, then the LLM selects among them. The code drops any id that is not in the candidates.
5. **Draft quote**: prices come only from `catalog.csv`, and the totals (HT, TVA, TTC) are computed in code. The professional types the quantities, and can price lines outside the catalog by hand (these lines are marked as manual).
6. **Validation interface (Streamlit)**: original message next to the extracted data, editable reply and quote, approve / reject, HTML export of the draft quote, search and status filter, a box to paste a new request, and a sidebar to ask questions about the general conditions.

## Rules enforced by the code

- **No invented prices.** The LLM never sees a price. It only returns catalog ids and quantities. Totals are computed in code.
- **Work outside the catalog is never priced automatically.** It becomes a line to price manually, and a hand-typed price is clearly flagged.
- **Nothing is sent.** There is no sending code. "Approuver" only changes a status.
- **Everything can be corrected.** Extracted data, reply and quote are reviewed by the professional, and each correction (original vs final) is logged.
- **Failures go to manual review.** If the extraction fails after 3 attempts, the request is kept with the status "à vérifier". If the reply cannot be generated, the professional writes it by hand.

## Technology

Python, LangChain, Amazon Bedrock (Nova Pro for the LLM, Titan for embeddings), Chroma (vector store), SQLite, Pydantic, Streamlit, pandas, pytest.

## Project structure

| File | Role |
|---|---|
| `schema.py` | `QuoteRequest` model (extracted record) with cleaning of empty values |
| `extract.py` | extraction prompt and chain, required fields, missing-field detection, questions |
| `qualify.py` | completeness score and priority |
| `reply.py` | French draft reply |
| `catalog.py` | loads `data/company/catalog.csv` |
| `ingest.py` | builds the vector store: one chunk per article of the general conditions, plus the catalog entries |
| `match.py` | candidate search and LLM selection of catalog services |
| `quote.py` | quote lines and totals, quantities, manual prices (price logic, tested) |
| `quote_html.py` | HTML draft quote (with a "BROUILLON" banner) |
| `conditions.py` | retrieval and grounded answers about the general conditions |
| `database.py` | SQLite storage (requests, quotes, replies, corrections) |
| `pipeline.py` | processes a message or a file: extraction, reply, status, score, storage |
| `app.py` | Streamlit validation interface |
| `evaluate.py`, `evaluate_match.py` | evaluation scripts, with `data/expected.json` and `data/expected_match.json` |
| `test_quote.py` | unit tests of the price logic |
| `data/requests/` | 10 fictional requests |
| `data/company/` | `catalog.csv` and `Conditions_generales.pdf` |

Request statuses: en cours de traitement, à compléter, hors demande, à vérifier, validé, rejeté.

## Setup (Windows, PowerShell)

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file:

```
AWS_REGION=ap-south-1
EMBED_REGION=<region of the embedding model>
LLM_MODEL_ID=apac.amazon.nova-pro-v1:0
EMBED_MODEL_ID=amazon.titan-embed-text-v2:0
```

AWS credentials with access to the Bedrock models must be configured (environment variables or an AWS profile).

## Running

```
python ingest.py        # builds the vector store (stop Streamlit first)
python pipeline.py      # processes data/requests/*.txt into SQLite
streamlit run app.py    # opens the validation interface
```

Re-running `pipeline.py` refreshes the requests and keeps the decisions already taken (validé, rejeté). Saved quotes, replies and corrections are stored separately and are not affected.

## Tests and evaluation

```
pytest -v                    # unit tests on the price logic, no LLM call
python evaluate.py           # extraction check against data/expected.json
python evaluate_match.py 5   # matching check, repeated 5 times
python conditions.py         # retrieval check on the general conditions
```

Last measured results: extraction 32/32; matching 251/260 checks over 5 runs; conditions retrieval 8/8. LLM results vary slightly between runs, so repeat the checks before drawing conclusions. The test sets are small (10 requests).

## Known limitations

- The service selector sometimes adds a line that was not requested, or a duplicate "to price manually" line. The professional reviews every quote.
- Quantities are usually empty, because a room's floor area is not the surface to paint. The professional types them.
- The PDF reader sometimes drops spaces in the text of the general conditions.
- Search in the interface only ignores case for plain letters (SQLite `LIKE`).
- After a quantity is saved, clearing the cell does not remove it.
- Requests are entered as text. There is no mailbox or web-form connection.

## Data protection notes (exercise)

All data in this project is fictional. In a real deployment, these points would need to be settled:

- Messages are sent to Amazon Bedrock for processing. Here the region is `ap-south-1`, outside the EU, so a real European client would need an EU region and a review of the provider's data processing terms.
- Requests, replies and quotes are stored unencrypted in a local SQLite file, with no retention period, no deletion mechanism and no access control.
- The corrections log keeps the original and the edited text of replies and quotes.

