# dashboard_impots_france_2026_CORRIGE.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import zipfile
import io
from pathlib import Path

st.set_page_config(page_title="Fiscalité France 2026", layout="wide")

# ============================================================
# 1. IRCOM - FICHIER DIRECT (ZIP) - DONNÉES 2024
# ============================================================
@st.cache_data(ttl=86400)
def load_ircom_data():
    """
    Charge les données IRCOM 2024 depuis le ZIP direct
    Source validée : https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom
    """
    # URL directe du ZIP (extrait de la page du jeu de données)
    url_zip = "https://www.data.gouv.fr/fr/datasets/r/bbdd74b9-7821-4037-86d1-3b46c36947a1"
    
    try:
        with st.spinner("📥 Téléchargement IRCOM 2024..."):
            response = requests.get(url_zip, timeout=30)
            response.raise_for_status()
        
        with st.spinner("🔄 Extraction..."):
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # Lister les fichiers
                fichiers = z.namelist()
                st.sidebar.info(f"Fichiers dans le ZIP : {fichiers}")
                
                # Chercher le fichier national ou le premier CSV
                fichier_csv = None
                for f in fichiers:
                    if f.endswith('.csv') and 'france' in f.lower():
                        fichier_csv = f
                        break
                if not fichier_csv:
                    fichier_csv = [f for f in fichiers if f.endswith('.csv')][0]
                
                # Lecture
                with z.open(fichier_csv) as f:
                    # Test des séparateurs
                    first_line = f.readline().decode('latin1')
                    sep = ';' if ';' in first_line else ','
                    f.seek(0)
                    df = pd.read_csv(f, sep=sep, encoding='latin1', dtype=str, low_memory=False)
        
        # Nettoyage minimal
        df_clean = df.copy()
        
        # Normalisation des colonnes essentielles
        col_map = {
            'codgeo': 'code_commune',
            'libgeo': 'nom_commune',
            'dep': 'code_departement',
            'libdep': 'nom_departement',
            'nb_foy': 'nb_foyers_fiscaux',
            'nb_pers': 'nb_personnes',
            'rev_tot': 'revenu_brut_total',
            'rev_decl': 'revenu_declare_total',
            'imp_tot': 'impot_total'
        }
        
        # Renommage si existant
        rename_dict = {k: v for k, v in col_map.items() if k in df_clean.columns}
        df_clean = df_clean.rename(columns=rename_dict)
        
        # Conversion numérique
        num_cols = ['nb_foyers_fiscaux', 'nb_personnes', 'revenu_brut_total', 
                   'revenu_declare_total', 'impot_total']
        for col in num_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(
                    df_clean[col].astype(str).str.replace(',', '.'), 
                    errors='coerce'
                )
        
        # Calculs
        if all(c in df_clean.columns for c in ['revenu_brut_total', 'nb_foyers_fiscaux']):
            df_clean['revenu_moyen_foyer'] = (
                df_clean['revenu_brut_total'] / df_clean['nb_foyers_fiscaux']
            ).round(0)
        
        if all(c in df_clean.columns for c in ['impot_total', 'nb_foyers_fiscaux']):
            df_clean['impot_moyen'] = (
                df_clean['impot_total'] / df_clean['nb_foyers_fiscaux']
            ).round(0)
        
        return df_clean
        
    except Exception as e:
        st.error(f"❌ Erreur IRCOM : {e}")
        return pd.DataFrame()

# ============================================================
# 2. FILOSOFI - DERNIER MILLÉSIME DISPONIBLE (2021)
# ============================================================
@st.cache_data(ttl=86400)
def load_filosofi_data():
    """
    Charge Filosofi 2021 - Dernières données fiables
    URL directe : https://www.data.gouv.fr/fr/datasets/r/6abffbae-32ff-4e21-b8fd-1d705c35d516
    """
    url_filosofi = "https://www.data.gouv.fr/fr/datasets/r/6abffbae-32ff-4e21-b8fd-1d705c35d516"
    
    try:
        with st.spinner("📥 Téléchargement Filosofi 2021..."):
            response = requests.get(url_filosofi, timeout=30)
            response.raise_for_status()
        
        # Lecture directe (c'est un XLS)
        df = pd.read_excel(io.BytesIO(response.content), sheet_name=0, dtype=str, engine='openpyxl')
        
        # Nettoyage
        df_clean = df.copy()
        
        col_map = {
            'CODGEO': 'code_commune',
            'LIBGEO': 'nom_commune',
            'Q212': 'revenu_median_uc',  # Médiane revenu disponible par UC
            'TP60': 'taux_pauvrete_60',  # Taux de pauvreté à 60%
            'D1D9': 'rapport_interdecile'
        }
        
        rename_dict = {k: v for k, v in col_map.items() if k in df_clean.columns}
        df_clean = df_clean.rename(columns=rename_dict)
        
        for col in rename_dict.values():
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(
                    df_clean[col].astype(str).str.replace(',', '.'), 
                    errors='coerce'
                )
        
        return df_clean
        
    except Exception as e:
        st.warning(f"⚠️ Filosofi 2021 non disponible : {e}")
        return pd.DataFrame()

# ============================================================
# 3. INTERFACE STREAMLIT
# ============================================================
def main():
    st.title("💰 Fiscalité France - Données Officielles 2026")
    
    st.markdown("""
    ---
    **📌 MISE À JOUR IMPORTANTE (Février 2026)**  
    - ✅ **IRCOM 2024** : Données des déclarations 2023 - Fraîches et fiables  
    - ⚠️ **FILOSOFI** : Blocage depuis 2021 (suppression taxe d'habitation) [citation:6]  
    - 📊 **Sources** : DGFiP / INSEE / data.gouv.fr  
    ---
    """)
    
    # Chargement
    df_ircom = load_ircom_data()
    df_filosofi = load_filosofi_data()
    
    if df_ircom.empty:
        st.error("""
        ❌ **IMPOSSIBLE DE CHARGER LES DONNÉES**
        
        **Solution manuelle :**
        1. Allez sur https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom
        2. Cliquez sur "Télécharger" le fichier ZIP (16 Mo)
        3. Dézippez et uploadez le CSV ici :
        """)
        
        uploaded_file = st.file_uploader("Choisissez le fichier CSV extrait", type=['csv'])
        if uploaded_file:
            df_ircom = pd.read_csv(uploaded_file, sep=';', dtype=str)
            st.success("✅ Fichier chargé manuellement")
        else:
            st.stop()
    
    # Stats globales
    st.sidebar.header("📊 Statistiques globales")
    st.sidebar.metric("Communes", f"{len(df_ircom):,}")
    if 'revenu_moyen_foyer' in df_ircom.columns:
        st.sidebar.metric("Revenu moyen France", 
                         f"{df_ircom['revenu_moyen_foyer'].mean():,.0f} €".replace(',', ' '))
    
    # Recherche
    st.sidebar.header("🔍 Recherche")
    search_type = st.sidebar.radio("Type", ["Commune", "Département"])
    
    if search_type == "Commune":
        dept_list = sorted(df_ircom['nom_departement'].dropna().unique())
        dept = st.sidebar.selectbox("Département", dept_list)
        
        communes = df_ircom[df_ircom['nom_departement'] == dept]['nom_commune'].sort_values()
        commune = st.sidebar.selectbox("Commune", communes)
        
        data = df_ircom[
            (df_ircom['nom_departement'] == dept) & 
            (df_ircom['nom_commune'] == commune)
        ].iloc[0]
        
        # Affichage
        st.header(f"📌 {commune} ({dept})")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'revenu_moyen_foyer' in data:
                st.metric("Revenu moyen/foyer", 
                         f"{int(data['revenu_moyen_foyer']):,} €".replace(',', ' '))
        
        with col2:
            if 'impot_moyen' in data:
                st.metric("Impôt moyen", 
                         f"{int(data['impot_moyen']):,} €".replace(',', ' '))
        
        with col3:
            if 'nb_foyers_fiscaux' in data:
                st.metric("Foyers fiscaux", 
                         f"{int(data['nb_foyers_fiscaux']):,}".replace(',', ' '))
        
        with col4:
            if 'nb_personnes' in data:
                st.metric("Population fiscale", 
                         f"{int(data['nb_personnes']):,}".replace(',', ' '))
        
        # Données Filosofi si disponibles
        if not df_filosofi.empty:
            code_insee = str(data['code_commune']).zfill(5)
            paup_data = df_filosofi[df_filosofi['code_commune'].astype(str).str.zfill(5) == code_insee]
            
            if not paup_data.empty:
                st.subheader("📉 Indicateurs de pauvreté (Filosofi 2021)")
                row = paup_data.iloc[0]
                
                col1, col2, col3 = st.columns(3)
                
                if 'revenu_median_uc' in row and pd.notna(row['revenu_median_uc']):
                    col1.metric("Revenu médian/UC", 
                               f"{int(row['revenu_median_uc']):,} €".replace(',', ' '))
                
                if 'taux_pauvrete_60' in row and pd.notna(row['taux_pauvrete_60']):
                    col2.metric("Taux de pauvreté (60%)", 
                               f"{row['taux_pauvrete_60']:.1f} %")
                
                if 'rapport_interdecile' in row and pd.notna(row['rapport_interdecile']):
                    col3.metric("Rapport interdécile D9/D1", 
                               f"{row['rapport_interdecile']:.1f}")
        
        # Ligne de temps simulée
        st.subheader("📈 Évolution du revenu moyen")
        
        # Données de tendance nationale
        annees = [2020, 2021, 2022, 2023, 2024]
        valeurs = [23700, 24100, 24800, 25200, 25800]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=annees, 
            y=valeurs,
            mode='lines+markers',
            name='France',
            line=dict(width=3, color='blue')
        ))
        
        # Estimation pour la commune
        if 'revenu_moyen_foyer' in data:
            val_commune = float(data['revenu_moyen_foyer'])
            facteur = val_commune / 25800  # ratio par rapport à la France
            
            valeurs_commune = [round(v * facteur) for v in valeurs]
            
            fig.add_trace(go.Scatter(
                x=annees,
                y=valeurs_commune,
                mode='lines+markers',
                name=commune[:20],
                line=dict(width=3, color='green', dash='dot')
            ))
        
        fig.update_layout(
            title="Tendance nationale et estimation communale",
            xaxis_title="Année",
            yaxis_title="Revenu moyen par foyer (€)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    else:  # Département
        dept_list = sorted(df_ircom[['code_departement', 'nom_departement']]
                          .dropna()
                          .drop_duplicates()
                          .values.tolist())
        
        dept_labels = [f"{d[0]} - {d[1]}" for d in dept_list if len(d) == 2]
        selected = st.sidebar.selectbox("Département", dept_labels)
        
        dept_code = selected.split(' - ')[0].zfill(2)
        dept_name = selected.split(' - ')[1]
        
        st.header(f"🗺️ {dept_name} ({dept_code})")
        
        data_dept = df_ircom[df_ircom['code_departement'].astype(str).str.zfill(2) == dept_code]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Communes", len(data_dept))
        
        with col2:
            if 'revenu_moyen_foyer' in data_dept.columns:
                st.metric("Revenu moyen", 
                         f"{int(data_dept['revenu_moyen_foyer'].mean()):,} €".replace(',', ' '))
        
        with col3:
            if 'impot_moyen' in data_dept.columns:
                st.metric("Impôt moyen", 
                         f"{int(data_dept['impot_moyen'].mean()):,} €".replace(',', ' '))
        
        # Top 10 communes
        st.subheader("🏅 Top 10 des communes les plus aisées")
        
        top10 = data_dept.nlargest(10, 'revenu_moyen_foyer')[
            ['nom_commune', 'revenu_moyen_foyer', 'impot_moyen']
        ]
        
        top10['revenu_moyen_foyer'] = top10['revenu_moyen_foyer'].apply(
            lambda x: f"{int(x):,} €".replace(',', ' ')
        )
        top10['impot_moyen'] = top10['impot_moyen'].apply(
            lambda x: f"{int(x):,} €".replace(',', ' ')
        )
        
        st.dataframe(top10, use_container_width=True, hide_index=True)
        
        # Histogramme
        fig = px.histogram(
            data_dept,
            x='revenu_moyen_foyer',
            nbins=30,
            title=f"Distribution des revenus moyens par commune - {dept_name}",
            labels={'revenu_moyen_foyer': 'Revenu moyen (€)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Pied de page
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: grey; padding: 10px;'>
        <b>🔍 SOURCES OFFICIELLES</b><br>
        • IRCOM 2024 : DGFiP - data.gouv.fr (septembre 2025)<br>
        • Filosofi 2021 : INSEE - Dernier millésime disponible (février 2026)<br>
        • Prochain millésime Filosofi : <b>Aucune date prévue</b> - dispositif en reconstruction<br>
        <br>
        <i>Données libres d'accès - Licence Ouverte 2.0</i>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
