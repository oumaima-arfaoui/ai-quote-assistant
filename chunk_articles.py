import re

from langchain_community.document_loaders import PyPDFLoader

PDF_PATH = "data/company/Conditions_generales.pdf"

# "4. Prix et catalogue de prestations" at the start of a line
HEADING = re.compile(r"^(\d{1,2})\.\s+(\S.*)$", re.MULTILINE)
# page header lines repeated on each page
NOISE = re.compile(
    r"^\s*(BatiPro Services — modèle de démonstration|Page \d+)\s*$", re.MULTILINE
)

pages = PyPDFLoader(PDF_PATH).load()
text = "\n".join(p.page_content for p in pages)
text = NOISE.sub("", text)

matches = list(HEADING.finditer(text))
articles = []
for i, m in enumerate(matches):
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    body = " ".join(text[m.end():end].split())  # join the wrapped lines
    articles.append({"number": int(m.group(1)), "title": m.group(2).strip(), "text": body})

print(len(articles), "articles trouvés")
for a in articles:
    print(f"\nArticle {a['number']} | {a['title']} | {len(a['text'])} caractères")
    print("  ", a["text"][:120], "...")

numbers = [a["number"] for a in articles]
print("\nNuméros :", numbers, "| séquence correcte :", numbers == list(range(1, len(numbers) + 1)))