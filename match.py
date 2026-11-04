from pathlib import Path
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from catalog import load_catalog
from extract import chain, compute_missing, llm
from ingest import get_vectorstore


class SelectedLine(BaseModel):
    item_id: str = Field(description="Catalog item id, copied exactly from the candidates")
    quantity: Optional[float] = Field(
        None,
        description="Quantity in the unit of the service, only if the request gives it directly. Otherwise null.",
    )
    reason: str = Field(description="Short reason, in French, why this service matches")


class Selection(BaseModel):
    lines: list[SelectedLine] = Field(default_factory=list)
    unmatched_work: list[str] = Field(
        default_factory=list,
        description="Requested work, in French, that has no matching candidate",
    )



selector_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You select services from a building company's catalog to prepare a draft quote.\n"
     "You receive a work request and a list of candidate services (id, name, unit, conditions).\n"
     "Rules:\n"
     "- Select only services for work the person explicitly asks to have done. "
     "Damage, problems or consequences they describe (for example a stain on a ceiling) are not requests: "
     "do not select a service for them and do not list them in unmatched_work either.\n"
     "- Do not add preparation, removal or extra services unless the person asks for them.\n"
     "- If the request does not name any specific work (for example it only says that some work is needed, "
     "or only asks for a quote), do not select a service just because it seems related to a place or trade "
     "they mention. Select nothing and write one entry in unmatched_work that restates the vague request.\n"
     "- If the request mentions several kinds of work, check each one separately against the candidates "
     "and select every matching service (for example both walls and ceilings if both are requested).\n"
     "- item_id must be copied exactly from the candidates. Never invent a service.\n"
     "- If a requested work has no matching candidate, describe it in unmatched_work instead of forcing a match. "
     "Write one short entry per distinct work, with no duplicates.\n"
     "- quantity: only if the request gives a measure that directly matches the service's unit. "
     "The size of a room (for example 'salon de 30 m2') is a floor area, not a surface to paint: set quantity to null. "
     "Never guess."),
    ("human", "Work request:\n{description}\n\nCandidate services:\n{candidates}"),

])

selector = selector_prompt | llm.with_structured_output(Selection)


WORK_LABELS = {
    "plomberie": "Plomberie",
    "electricite": "Électricité",
    "peinture": "Peinture",
    "menuiserie": "Menuiserie",
    "renovation": "Rénovation",
}


def find_candidates(record, k: int = 6):
    catalog = load_catalog()
    store = get_vectorstore()
    queries = [record.description or ""]
    queries += [WORK_LABELS[wt.value] for wt in record.work_types if wt.value in WORK_LABELS]

    found = {}
    for query in queries:
        for doc in store.similarity_search(query, k=k, filter={"doc_type": "catalog"}):
            found[doc.metadata["item_id"]] = catalog[doc.metadata["item_id"]]
    return list(found.values())

def select_lines(record) -> Selection:
    candidates = find_candidates(record)
    candidates_text = "\n".join(
        f"- {c.item_id} | {c.service_name} | unité : {c.unit} | conditions : {c.conditions or 'aucune'}"
        for c in candidates
    )
    selection = selector.invoke({"description": record.description, "candidates": candidates_text})

    valid_ids = {c.item_id for c in candidates}
    selection.lines = [line for line in selection.lines if line.item_id in valid_ids]
    return selection


if __name__ == "__main__":
    catalog = load_catalog()
    for path in sorted(Path("data/requests").glob("*.txt")):
        record = chain.invoke({"request_text": path.read_text(encoding="utf-8")})
        record.missing_fields = compute_missing(record)
        if not record.is_quote_request:
            continue

        print(f"\n===== {path.name} =====")
        print("Demande :", record.description)
        selection = select_lines(record)
        for line in selection.lines:
            item = catalog[line.item_id]
            print(f"  {line.item_id} | {item.service_name} | qté : {line.quantity} {item.unit} | {line.reason}")
        for work in selection.unmatched_work:
            print(f"  À CHIFFRER MANUELLEMENT : {work}")