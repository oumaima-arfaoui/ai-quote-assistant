from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from extract import llm
from ingest import get_vectorstore


def find_conditions(question: str, k: int = 3):
    """Return the k closest articles of the general conditions: (number, title, text, score)."""
    store = get_vectorstore()
    results = store.similarity_search_with_score(
        question, k=k, filter={"doc_type": "conditions"}
    )
    return [
        (doc.metadata["article_number"], doc.metadata["article_title"], doc.page_content, score)
        for doc, score in results
    ]
answer_prompt = ChatPromptTemplate.from_messages([
    
    ("system",
     "You answer a question about a building company's general conditions.\n"
     "Rules:\n"
     "- Answer in French, as a single short paragraph of 3 sentences at most, with no line breaks.\n"
     "- Use ONLY the articles provided. Do not add facts, numbers, prices, delays or promises "
     "that are not written in them. Rephrase in your own words instead of copying sentences.\n"
     "- Cite the article number in parentheses after each fact it supports, for example (article 9).\n"
     "- If the articles only partly answer, say what they state, cite it, and say clearly "
     "what they do not specify.\n"
     "- If the articles say nothing relevant to the question, reply with exactly this sentence "
     "and nothing else: Les conditions générales ne précisent pas ce point.\n"
     "- Never give a price and never make a commitment on behalf of the company."),
    ("human", "Question : {question}\n\nArticles :\n{articles}"),
])


answer_chain = answer_prompt | llm | StrOutputParser()


def answer_from_articles(question: str, found) -> str:
    articles = "\n\n".join(text for _, _, text, _ in found)
    return answer_chain.invoke({"question": question, "articles": articles})


def answer_question(question: str, k: int = 3) -> str:
    return answer_from_articles(question, find_conditions(question, k=k))

# question -> article(s) that should answer it (any of them in the top 3 counts as a hit)
TESTS = [
    ("Puis-je annuler ou reporter les travaux ?", {9}),
    ("Combien de temps le devis est-il valable ?", {3}),
    ("Faut-il verser un acompte ?", {3, 8}),
    ("Que se passe-t-il si un problème imprévu apparaît pendant les travaux ?", {5}),
    ("Comment faire une réclamation ou utiliser la garantie ?", {10}),
    ("Mes données personnelles sont-elles protégées ?", {11}),
    ("Est-ce qu'une intelligence artificielle lit ma demande ?", {12}),
    ("Une visite technique est-elle nécessaire avant de connaître le prix ?", {2}),
]

if __name__ == "__main__":
    ok = 0
    for question, expected in TESTS:
        numbers = [n for n, _, _, _ in find_conditions(question)]
        hit = bool(expected & set(numbers))
        ok += hit
        print(f"\n{'OK   ' if hit else 'RATÉ '}| {question}")
        print(f"       attendu : {sorted(expected)} | trouvé : {numbers}")
    print(f"\nScore : {ok}/{len(TESTS)}")