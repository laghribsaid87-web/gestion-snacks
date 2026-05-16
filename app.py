import streamlit as st
import pandas as pd
import speech_recognition as sr
import re
import io
from audio_recorder_streamlit import audio_recorder
from datetime import datetime

def analyser_texte_facture(texte):
    # On sépare le texte dicté à chaque fois qu'on rencontre "DH"
    articles_bruts = re.split(r'\s*DH\s*', texte, flags=re.IGNORECASE)
    donnees = []
    
    date_jour = datetime.today().strftime('%Y-%m-%d')
    mois_actuel = datetime.today().strftime('%Y-%m')
    
    for article in articles_bruts:
        article = article.strip()
        if not article:
            continue
        
        # Cette expression régulière va extraire : [Nom de l'article] [Quantité] [Unité] [Prix]
        # Le segment `(?:b\s*)?` permet d'ignorer le "B" optionnel que vous dites en darija (ex: "B 200")
        modele = r'(.*?)\s+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]*)\s*(?:b\s*)?(\d+(?:[.,]\d+)?)$'
        match = re.search(modele, article, re.IGNORECASE)
        
        if match:
            nom = match.group(1).strip().upper()
            quantite = float(match.group(2).replace(',', '.'))
            unite = match.group(3).strip().upper()
            
            # Si l'unité est vide ou qu'il a pris le "B" de darija pour l'unité (ex: BOUTA 2 B 100)
            if unite == 'B' or unite == '':
                unite = "PIÈCE"
                
            prix = float(match.group(4).replace(',', '.'))
            
            donnees.append({
                "Date": date_jour,
                "Mois": mois_actuel,
                "Article": nom,
                "Quantité": quantite,
                "Unité": unite,
                "Prix Total (DH)": prix
            })
        else:
            # Si l'IA vocale s'est trompée sur le format, on l'ajoute quand même pour que vous puissiez corriger
            donnees.append({
                "Date": date_jour,
                "Mois": mois_actuel,
                "Article": article,
                "Quantité": 0.0,
                "Unité": "?",
                "Prix Total (DH)": 0.0
            })
            
    return pd.DataFrame(donnees)

def main():
    st.set_page_config(page_title="Facture Vocale", layout="centered")
    st.title("🎙️ Saisie de Facture par la Voix")
    st.write("Exemple à dicter : *viande hachée 5 kg 500 DH saucisse 2 kg 200 DH poulet 3 kg 80 DH bouta gaz 2 B 100 DH zite 5 l b 200 DH*")

    # Initialisation de la mémoire pour le texte dicté
    if 'texte_dicte' not in st.session_state:
        st.session_state.texte_dicte = ""

    st.write("🎤 Cliquez sur le micro ci-dessous pour dicter votre facture :")
    audio_bytes = audio_recorder(text="Parler", neutral_color="#6aa36f", recording_color="#e81416")

    if audio_bytes:
        with st.spinner("Analyse de la voix en cours..."):
            try:
                r = sr.Recognizer()
                # Utilisation d'un fichier audio en mémoire au lieu de PyAudio
                audio_file = io.BytesIO(audio_bytes)
                with sr.AudioFile(audio_file) as source:
                    audio = r.record(source)
                
                st.session_state.texte_dicte = r.recognize_google(audio, language="fr-FR")
                st.success("Texte capturé avec succès !")
            except sr.UnknownValueError:
                st.error("Désolé, je n'ai pas pu comprendre l'audio. Rapprochez-vous du micro.")
            except sr.RequestError as e:
                st.error(f"Erreur de connexion au service vocal : {e}")

    texte = st.text_area("Texte brut (vous pouvez le modifier manuellement) :", value=st.session_state.texte_dicte, height=100)
    
    if texte:
        df_facture = analyser_texte_facture(texte)
        st.subheader("📋 Détail de votre facture")
        df_modifie = st.data_editor(df_facture, num_rows="dynamic", use_container_width=True)
        st.markdown(f"### 💰 Total à payer : **{df_modifie['Prix Total (DH)'].sum():.2f} DH**")
        
        # Bouton pour télécharger la facture et faire le suivi mensuel
        csv = df_modifie.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger pour suivi mensuel (CSV)",
            data=csv,
            file_name=f"facture_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()