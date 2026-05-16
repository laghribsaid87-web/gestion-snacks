import streamlit as st
import pandas as pd
import re
import io
import google.generativeai as genai
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
            if "GEMINI_API_KEY" in st.secrets:
                try:
                    # Configuration de l'IA Gemini
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    # Ordre strict pour Gemini
                    prompt = "Écoute cet enregistrement audio (mélange de darija marocaine et de français). Transcris exactement ce que la personne dit sans corriger les mots en darija et sans faire de phrases, donne uniquement le texte brut (ex: viande 5 kg 500 DH...)"
                    
                    # Envoi de l'audio directement à l'IA
                    reponse = model.generate_content([
                        prompt,
                        {"mime_type": "audio/wav", "data": audio_bytes}
                    ])
                    
                    st.session_state.texte_dicte = reponse.text.strip()
                    st.success("Texte capturé avec succès grâce à Gemini ! ✨")
                except Exception as e:
                    st.error(f"Erreur lors de l'analyse avec Gemini : {e}")
            else:
                st.error("⚠️ La clé API Gemini n'est pas configurée dans les paramètres.")

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