import os
import re
import shutil

from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from catalog import load_catalog

load_dotenv()

CHROMA_DIR = "data/chroma"
PDF_PATH = "data/company/Conditions_generales.pdf"

# "4. Prix et catalogue de prestations" at the start of a line
HEADING = re.compile(r"^(\d{1,2})\.\s+(\S.*)$", re.MULTILINE)
# page header lines repeated on each page
NOISE = re.compile(
    r"^\s*(BatiPro Services — modèle de démonstration|Page \d+)\s*$", re.MULTILINE
)


def get_embeddings():
    return BedrockEmbeddings(
        model_id=os.getenv("EMBED_MODEL_ID"),
        region_name=os.getenv("EMBED_REGION"),
    )


def get_vectorstore():
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=get_embeddings())


def load_articles():
    """One Document per article of the general conditions."""
    pages = PyPDFLoader(PDF_PATH).load()
    text = "\n".join(p.page_content for p in pages)
    text = NOISE.sub("", text)

    matches = list(HEADING.finditer(text))
    articles = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = " ".join(text[m.end():end].split())  # join the wrapped lines
        number = int(m.group(1))
        title = m.group(2).strip()
        articles.append(
            Document(
                page_content=f"Article {number}. {title}\n{body}",
                metadata={
                    "doc_type": "conditions",
                    "source": "Conditions_generales.pdf",
                    "article_number": number,
                    "article_title": title,
                },
            )
        )

    numbers = [a.metadata["article_number"] for a in articles]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError(f"Article numbers look wrong: {numbers}")
    return articles


def build_documents():
    articles = load_articles()

    catalog_docs = []
    for item in load_catalog().values():
        text = (
            f"{item.service_name} ({item.category}). "
            f"Unité : {item.unit}. Conditions : {item.conditions or 'aucune'}"
        )
        catalog_docs.append(
            Document(
                page_content=text,
                metadata={"doc_type": "catalog", "item_id": item.item_id, "source": "catalog.csv"},
            )
        )
    return articles + catalog_docs


if __name__ == "__main__":
    shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    docs = build_documents()
    n_cond = sum(d.metadata["doc_type"] == "conditions" for d in docs)
    n_cat = len(docs) - n_cond
    print(f"{n_cond} articles de conditions + {n_cat} prestations du catalogue")

    Chroma.from_documents(docs, embedding=get_embeddings(), persist_directory=CHROMA_DIR)
    print("Base vectorielle créée dans", CHROMA_DIR)

    vs = get_vectorstore()
    for question in [
        "fuite sous l'évier",
        "peinture des murs et plafonds",
        "remplacement d'un chauffe-eau",
        "annulation du devis",
        "protection des données personnelles",
    ]:
        print(f"\nRecherche : {question}")
        for doc, score in vs.similarity_search_with_score(question, k=3):
            label = doc.metadata.get("item_id") or f"conditions art.{doc.metadata.get('article_number')}"
            print(f"  {score:.3f} | {label:<18} | {doc.page_content[:70]!r}")