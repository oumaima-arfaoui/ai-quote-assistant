from conditions import answer_question

for question in [
    "Puis-je annuler ou reporter les travaux ?",
    "Faut-il verser un acompte ?",
    "Quelle est la durée de la garantie ?",
    "Quel est le prix d'un chauffe-eau ?",
]:
    print("\nQ :", question)
    print("R :", answer_question(question))