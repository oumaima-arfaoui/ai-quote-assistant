import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate

from schema import QuoteRequest

load_dotenv()




llm = ChatBedrockConverse(
    model=os.getenv("LLM_MODEL_ID"),
    region_name=os.getenv("AWS_REGION"),
    temperature=0,
)
structured_llm = llm.with_structured_output(QuoteRequest)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You extract information from quote requests sent to a building trades company. "
     "The messages are in French.\n"
     "Rules:\n"
     "- Fill in only what is explicitly written in the message.\n"
     "- Never invent or guess a name, phone number, email or address. Leave the field empty if it is not given.\n"
     "- email, phone, site_address: if they appear anywhere in the message (including the signature), "
     "copy them exactly as written. Only leave them empty when they are really absent.\n"
     "- site_address: if only a city or a neighbourhood is given, copy it as is. "
     "Do not leave the field empty just because the street is missing.\n"
      "- name: use the signature or the way the person introduces themselves, even if it is a family name "
     "(for example 'Famille Rousseau'). If the message has no signature and the person never gives a name, "
     "leave name empty. Greetings such as 'Bonjour' or 'Salut' are not names.\n"
     "- description: always write a short French summary of the work requested, "
     "including useful details such as surface area, quantities and materials.\n"
     "- availability: include any time frame the person gives for the work or the visit, "
     "for example 'aujourd'hui ou demain' or 'en janvier'.\n"
     "- work_types: deduce the type(s) of work from the request, even if the type is not named "
     "(for example a water heater is 'plomberie', sockets and an electrical panel are 'electricite'). "
     "Use 'autre' only if nothing fits. If the request is too vague to know the trade, leave the list empty.\n"
     "- work_types: if the message only mentions a room or says 'travaux' without saying what has to be done "
     "(for example 'des travaux dans ma salle de bain'), leave work_types empty.\n"
     "- urgency: 'urgent' for an emergency or a leak happening now, 'normal' if a time frame of a few weeks is given, "
     "'flexible' if the person says there is no rush, 'inconnu' if nothing is said.\n"
     "- is_quote_request: true only if the person asks for a quote or for work to be done. "
     "False for general questions (opening hours, for example), spam or unrelated messages."),
    ("human", "{request_text}"),
])


chain = prompt | structured_llm
REQUIRED_FIELDS = ["name", "phone", "email", "site_address", "availability"]


def compute_missing(request: QuoteRequest) -> list[str]:
    if not request.is_quote_request:
        return []

    missing = [f for f in REQUIRED_FIELDS if not getattr(request, f)]
    if not request.work_types:
        missing.append("work_types")
    return missing
QUESTIONS = {
    "name": "Pouvez-vous nous indiquer vos nom et prénom ?",
    "phone": "Quel est votre numéro de téléphone pour vous joindre ?",
    "email": "Quelle est votre adresse e-mail pour vous envoyer le devis ?",
    "site_address": "Quelle est l'adresse complète du chantier ?",
    "availability": "Quand souhaitez-vous que les travaux soient réalisés, et à quels horaires êtes-vous disponible ?",
    "work_types": "Pouvez-vous préciser la nature des travaux souhaités (plomberie, électricité, peinture, menuiserie, rénovation...) ?",
}


def build_questions(request: QuoteRequest) -> list[str]:
    return [QUESTIONS[f] for f in request.missing_fields if f in QUESTIONS]
if __name__ == "__main__":
    for path in sorted(Path("data/requests").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        result = chain.invoke({"request_text": text})
        result.missing_fields = compute_missing(result)
        print(f"\n===== {path.name} =====")
        print(result.model_dump_json(indent=2))

        if not result.is_quote_request:
            print("\nCe message n'est pas une demande de devis : à traiter manuellement.")
            continue

        questions = build_questions(result)
        if questions:
            print("\nQuestions à poser au prospect :")
            for q in questions:
                print(f"  - {q}")
        else:
            print("\nAucune question : la demande est complète.")