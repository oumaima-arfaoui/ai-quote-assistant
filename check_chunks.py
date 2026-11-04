from ingest import get_vectorstore

store = get_vectorstore()
data = store.get()
print("Total entries:", len(data["ids"]))

pdf_entries = [
    (doc, meta)
    for doc, meta in zip(data["documents"], data["metadatas"])
    if meta.get("doc_type") != "catalog"
]
print("Non-catalog entries:", len(pdf_entries))

for i, (doc, meta) in enumerate(pdf_entries, 1):
    print(f"\n--- chunk {i} | {meta} | {len(doc)} characters ---")
    print(doc[:250])