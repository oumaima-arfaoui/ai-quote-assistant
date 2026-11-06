import json
from datetime import datetime

from pipeline import process_text
import pandas as pd
import streamlit as st
from conditions import answer_from_articles, find_conditions
from catalog import load_catalog
from database import (
    get_final_reply,
    get_generated_quote,
    get_request,
    get_saved_quote,
    init_db,
    list_requests,
    log_correction,
    save_final_reply,
    save_generated_quote,
    save_quote,
    search_request_ids,
    update_status,
)
from match import select_lines
from quote import Quote, quote_from_selection, set_manual_price, set_quantity
from quote_html import quote_to_html
from schema import QuoteRequest

st.set_page_config(page_title="Devis - validation", layout="wide")
init_db()

st.title("Validation des demandes de devis")
st.write("Aucun envoi automatique : tout est validé par un humain.")
with st.sidebar:
    st.header("Conditions générales")
    question = st.text_input("Question sur les conditions générales", key="conditions_question")
    if st.button("Poser la question", key="conditions_ask") and question.strip():
        with st.spinner("Recherche dans les conditions..."):
            found = find_conditions(question.strip())
            st.session_state["conditions_result"] = {
                "answer": answer_from_articles(question.strip(), found),
                "articles": [(n, title, text) for n, title, text, _ in found],
            }

    result = st.session_state.get("conditions_result")
    if result:
        st.write(result["answer"])
        st.caption(
            "Réponse indicative, générée à partir des articles ci-dessous : "
            "à vérifier avant toute communication au client."
        )
        for n, title, text in result["articles"]:
            with st.expander(f"Article {n} : {title}"):
                st.write(text)
    with st.expander("Nouvelle demande"):
        new_text = st.text_area("Collez le message du client", height=150, key="new_request_text")
    if st.button("Analyser la demande", key="new_request_btn"):
        source_name = datetime.now().strftime("web_%Y%m%d_%H%M%S.txt")
        try:
            with st.spinner("Analyse en cours..."):
                result = process_text(source_name, new_text)
            st.success(f"{source_name} : {result}")
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"L'analyse a échoué : {e}")
rows = [dict(row) for row in list_requests()]

if not rows:
    st.info("Aucune demande en base. Lancez d'abord : python pipeline.py")
else:
    statuses = sorted({r["status"] for r in rows})
    chosen = st.multiselect("Filtrer par statut", statuses, default=statuses)
    search = st.text_input("Rechercher (nom, adresse, mot-clé)")

    visible = [r for r in rows if r["status"] in chosen]
    if search.strip():
        matching = search_request_ids(search.strip())
        visible = [r for r in visible if r["id"] in matching]

    st.subheader(f"{len(visible)} demandes sur {len(rows)} (triées par priorité)")
    st.dataframe(visible, hide_index=True)

    if not visible:
        st.info("Aucune demande pour ce filtre.")
        st.stop()

    st.divider()
    labels = {r["id"]: f"{r['source_file']} | {r['priority']} | {r['status']}" for r in visible}
    selected_id = st.selectbox("Choisir une demande", list(labels), format_func=lambda i: labels[i])

    request = get_request(selected_id)
    record = QuoteRequest.model_validate_json(request["record_json"])
    left, right = st.columns(2)
    with left:
        st.subheader("Message d'origine")
        st.text(request["raw_text"])
    with right:
        st.subheader("Données extraites")
        st.json(json.loads(request["record_json"]))

    st.divider()
    st.subheader("Réponse proposée au prospect")
    if request["draft_reply"] or record.is_quote_request:
        saved_reply = get_final_reply(request["source_file"])
        if not request["draft_reply"] and not saved_reply:
            st.warning("La réponse automatique n'a pas pu être générée : rédigez-la à la main.")
        reply_text = st.text_area(
            "Brouillon (modifiable)",
            value=saved_reply or request["draft_reply"] or "",
            height=300,
            key=f"reply_{selected_id}",
        )
        if saved_reply:
            st.caption("Une version modifiée a été enregistrée.")
        if st.button("Enregistrer la réponse", key=f"save_reply_{selected_id}"):
            save_final_reply(request["source_file"], reply_text)
            log_correction(request["source_file"], "reply", request["draft_reply"] or "", reply_text)
            st.success("Réponse enregistrée.")
    else:
        st.info("Pas de réponse : ce message n'est pas une demande de devis.")

    st.divider()
    st.subheader("Devis brouillon")
    

    if not record.is_quote_request:
        st.info("Pas de devis : ce message n'est pas une demande de devis.")
    else:
        source_file = request["source_file"]
        quote_key = f"quote_{selected_id}"
        editor_key = f"editor_{selected_id}"

        if st.button("Générer le devis brouillon", key=f"btn_{selected_id}"):
            with st.spinner("Sélection des prestations..."):
                selection = select_lines(record)
            generated = quote_from_selection(selection, load_catalog())
            save_generated_quote(source_file, generated.model_dump_json(indent=2))
            st.session_state[quote_key] = generated
            st.session_state.pop(editor_key, None)  # forget old typed quantities

        # Load the saved quote from SQLite if nothing is in memory yet
        quote = st.session_state.get(quote_key)
        if quote is None:
            saved = get_saved_quote(source_file)
            if saved:
                quote = Quote.model_validate_json(saved)
                st.session_state[quote_key] = quote

        if quote:
            st.caption("Saisissez les quantités dans la colonne « Quantité ».")
            base = pd.DataFrame(
                [
                    {
                        "Désignation": line.label,
                        "Unité": line.unit,
                        "Prix unitaire HT": line.unit_price_ht_eur,
                        "Quantité": line.quantity,
                    }
                    for line in quote.lines
                ]
            ).astype({"Quantité": "float"})

            edited = st.data_editor(
                base,
                hide_index=True,
                disabled=["Désignation", "Unité", "Prix unitaire HT"],
                column_config={"Quantité": st.column_config.NumberColumn(min_value=0.0)},
                key=editor_key,
            )

            # Apply the typed quantities in code (only on lines that have a catalog price)
            priced_quote = quote
            for i, qty in enumerate(edited["Quantité"]):
                line = quote.lines[i]
                if pd.notna(qty) and qty > 0 and line.unit_price_ht_eur is not None:
                    priced_quote = set_quantity(priced_quote, i, float(qty))

            st.subheader("Devis calculé")
            st.dataframe(
                [
                    {
                        "Désignation": line.label,
                        "Quantité": line.quantity,
                        "Unité": line.unit,
                        "Prix unitaire HT": line.unit_price_ht_eur,
                        "Total HT": line.total_ht_eur,
                        "Note": line.note,
                        "Raison": line.reason,
                        "Prix manuel": "oui" if line.manual_price else "",
                    }
                    for line in priced_quote.lines
                ],
                hide_index=True,
            )
            c1, c2, c3 = st.columns(3)
            c1.metric("Total HT", f"{priced_quote.total_ht_eur:.2f} €")
            c2.metric("TVA", f"{priced_quote.total_vat_eur:.2f} €")
            c3.metric("Total TTC", f"{priced_quote.total_ttc_eur:.2f} €")
            if not priced_quote.complete:
                st.warning("Devis incomplet : des lignes sont à compléter par le professionnel.")
                manual_idx = [i for i, l in enumerate(priced_quote.lines) if l.item_id is None]
            if manual_idx:
                with st.expander("Chiffrer une ligne hors catalogue (prix saisi à la main)"):
                    idx = st.selectbox(
                        "Ligne à chiffrer",
                        manual_idx,
                        format_func=lambda i: priced_quote.lines[i].label,
                        key=f"manual_line_{selected_id}",
                    )
                    m1, m2, m3, m4 = st.columns(4)
                    m_qty = m1.number_input(
                        "Quantité", min_value=0.0, value=1.0, step=1.0, key=f"manual_qty_{selected_id}"
                    )
                    m_unit = m2.text_input("Unité", value="forfait", key=f"manual_unit_{selected_id}")
                    m_price = m3.number_input(
                        "Prix unitaire HT (€)", min_value=0.0, value=0.0, step=10.0,
                        key=f"manual_price_{selected_id}",
                    )
                    m_vat = m4.number_input(
                        "TVA (%)", min_value=0.0, value=20.0, step=1.0, key=f"manual_vat_{selected_id}"
                    )
                    if st.button("Appliquer ce prix", key=f"manual_apply_{selected_id}"):
                        if m_qty > 0 and m_price > 0:
                            st.session_state[quote_key] = set_manual_price(
                                priced_quote, idx, m_qty, m_price, m_vat, m_unit
                            )
                            st.session_state.pop(editor_key, None)
                            st.rerun()
                        else:
                            st.error("Saisissez une quantité et un prix supérieurs à 0.")

            if st.button("Enregistrer le devis", key=f"save_{selected_id}"):
                save_quote(source_file, priced_quote.model_dump_json())
                original = get_generated_quote(source_file)
                if original:  # no original for quotes generated before this step
                    log_correction(
                        source_file, "quote", original, priced_quote.model_dump_json(indent=2)
                    )
                st.session_state[quote_key] = priced_quote
                st.session_state.pop(editor_key, None)
                st.success("Devis enregistré.")
                st.download_button(
                "Télécharger le devis brouillon (HTML)",
                data=quote_to_html(priced_quote, record),
                file_name=f"devis_brouillon_{source_file.replace('.txt', '')}.html",
                mime="text/html",
                key=f"download_{selected_id}",
            )
        st.divider()
        st.subheader("Décision")
        st.write(f"Statut actuel : **{request['status']}**")
        st.caption("Approuver ne fait que changer le statut : aucun message n'est envoyé.")
        d1, d2 = st.columns(2)
        if d1.button("Approuver", key=f"approve_{selected_id}"):
            update_status(source_file, "validé")
            st.rerun()
        if d2.button("Rejeter", key=f"reject_{selected_id}"):
            update_status(source_file, "rejeté")
            st.rerun()