from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from extract import chain, compute_missing, build_questions, llm

reply_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You write draft email replies, in French, for a building trades company answering a prospect "
     "who asked for a quote.\n"
     "Rules:\n"
     "- Polite, warm and concise (about 120 words maximum).\n"
     "- Start with 'Bonjour' followed by the prospect's name if it is known, otherwise just 'Bonjour,'.\n"
     "- Thank the person and briefly restate what you understood of the request, using only the information given.\n"
     "- If a list of questions is provided, ask exactly those questions as a bullet list. Do not add other questions.\n"
     "- If there are no questions, say that you will prepare a quote and come back to them.\n"
     "- If the urgency is 'urgent', acknowledge the urgency but do not promise any intervention time.\n"
     "- Never mention prices, costs, dates of intervention or any commitment.\n"
     "- End with 'Cordialement,' and the signature '[Nom de l'entreprise]'.\n"
     "- Write only the body of the email, with no subject line and no comments."),
    ("human",
     "Information extracted from the request:\n{record}\n\n"
     "Questions to ask:\n{questions}"),
])

reply_chain = reply_prompt | llm | StrOutputParser()


def draft_reply(request) -> str:
    questions = build_questions(request)
    questions_text = "\n".join(f"- {q}" for q in questions) if questions else "(none)"
    return reply_chain.invoke({
        "record": request.model_dump_json(indent=2),
        "questions": questions_text,
    })


if __name__ == "__main__":
    for path in sorted(Path("data/requests").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        result = chain.invoke({"request_text": text})
        result.missing_fields = compute_missing(result)

        print(f"\n===== {path.name} =====")
        if not result.is_quote_request:
            print("Pas une demande de devis : aucune réponse générée.")
            continue

        print("BROUILLON - à valider avant envoi\n")
        print(draft_reply(result))