# dashboard_impots_france_2026_CORRIGE2.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import zipfile
import io
import xlrd  # Nécessaire pour les vieux .xls
from pathlib import Path

st.set_page_config(page_title="Fiscalité France 2026", layout="wide")

# ============================================================
# 1. IRCOM - DONNÉES PRINCIPALES
# ============================================================
@st.cache_data(ttl=86400)
def load_ircom_data():
    """
    Charge les données IRCOM 2024 depuis le ZIP
    """
    # URL du ZIP (testée fonctionnelle)
    url_zip = "https://www.data.gouv.fr/fr/datasets/r/bbdd74b9-7821-4037-86d1-3b46c36947a1"
    
    try:
        with st.spinner("📥 Téléchargement IRCOM 2024..."):
            response = requests.get(url_zip, timeout=30)
            response.raise_for_status()
        
        with st.spinner("🔄 Extraction..."):
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                fichiers = z.namelist()
                
                # Chercher le fichier national
                fichier_csv = None
                for f in fichiers:
                    if f.endswith('.csv') and ('france' in f.lower() or 'entiere' in f.lower()):
                        fichier_csv = f
                        break
                if not fichier_csv:
                    fichier_csv = [f for f in fichiers if f.endswith('.csv')][0]
                
                with z.open(fichier_csv) as f:
                    # Détection automatique du séparateur
                    first_line = f.readline().decode('latin1')
                    sep = ';' if ';' in first_line else ','
                    f.seek(0)
                    df = pd.read_csv(f, sep=sep, encoding='latin1', dtype=str, low_memory=False)
        
        # Nettoyage
        df_clean = df.copy()
        
        # Mapping des colonnes essentielles
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
# 2. FILOSOFI - CORRECTION : C'EST UN .XLS !
# ============================================================
@st.cache_data(ttl=86400)
def load_filosofi_data():
    """
    Charge Filosofi 2021 - Format .xls (Excel 97-2003)
    """
    url_filosofi = "https://www.data.gouv.fr/fr/datasets/r/6abffbae-32ff-4e21-b8fd-1d705c35d516"
    
    try:
        with st.spinner("📥 Téléchargement Filosofi 2021 (.xls)..."):
            response = requests.get(url_filosofi, timeout=30)
            response.raise_for_status()
        
        # 🔴 CORRECTION CRITIQUE : Lecture d'un .xls, PAS .csv
        with st.spinner("🔄 Lecture du fichier Excel (format ancien)..."):
            # Méthode 1 : pandas avec engine xlrd (pour .xls)
            df = pd.read_excel(
                io.BytesIO(response.content), 
                sheet_name=0, 
                dtype=str,
                engine='xlrd'  # Spécifique pour .xls
            )
        
        st.sidebar.success(f"✅ Filosofi 2021 chargé : {len(df)} communes")
        
        # Nettoyage
        df_clean = df.copy()
        
        # Mapping des colonnes Filosofi
        col_map = {
            'CODGEO': 'code_commune',
            'LIBGEO': 'nom_commune',
            'Q212': 'revenu_median_uc',      # Médiane revenu disponible par UC
            'TP60': 'taux_pauvrete_60',       # Taux de pauvreté à 60%
            'D1D9': 'rapport_interdecile'     # Rapport interdécile D9/D1
        }
        
        rename_dict = {k: v for k, v in col_map.items() if k in df_clean.columns}
        df_clean = df_clean.rename(columns=rename_dict)
        
        # Conversion numérique
        for col in rename_dict.values():
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(
                    df_clean[col].astype(str).str.replace(',', '.'), 
                    errors='coerce'
                )
        
        return df_clean
        
    except Exception as e:
        st.warning(f"⚠️ Filosofi 2021 non disponible : {e}")
        st.info("💡 Astuce : Si l'erreur persiste, installez xlrd : `pip install xlrd`")
        return pd.DataFrame()

# ============================================================
# 3. INTERFACE STREAMLIT
# ============================================================
def main():
    st.title("💰 Fiscalité France - Données Officielles 2026")
    
    # Vérification des dépendances
    try:
        import xlrd
    except ImportError:
        st.error("""
        ❌ **Module manquant : xlrd**
        
        Installez-le avec :
        ```bash
        pip install xlrd
        ```
        
        Ce module est nécessaire pour lire les fichiers .xls (Filosofi).
        """)
        st.stop()
    
    st.markdown("""
    ---
    **📌 SOURCES VALIDÉES**  
    - ✅ **IRCOM 2024** : Revenus 2023 - DGFiP (Sept 2025)  
    - ✅ **FILOSOFI 2021** : Pauvreté & inégalités - INSEE (Fév 2026) - **Format .xls**  
    ---
    """)
    
    # Chargement IRCOM
    df_ircom = load_ircom_data()
    
    if df_ircom.empty:
        st.error("""
        ❌ **Téléchargement automatique IRCOM échoué**
        
        **Solution manuelle :**
        1. https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom
        2. Téléchargez le ZIP (septembre 2025)
        3. Dézippez et uploadez le CSV
        """)
        
        uploaded_file = st.file_uploader("Choisissez le fichier CSV", type=['csv'])
        if uploaded_file:
            df_ircom = pd.read_csv(uploaded_file, sep=';', dtype=str)
            st.success("✅ Fichier chargé")
        else:
            st.stop()
    
    # Chargement Filosofi (.xls)
    df_filosofi = load_filosofi_data()
    
    # Stats sidebar
    st.sidebar.header("📊 Données chargées")
    st.sidebar.metric("IRCOM - Communes", f"{len(df_ircom):,}")
    if not df_filosofi.empty:
        st.sidebar.metric("FILOSOFI - Communes", f"{len(df_filosofi):,}")
        st.sidebar.info("📌 Filosofi 2021 (dernier disponible)")
    
    # Navigation
    st.sidebar.header("🔍 Recherche")
    search_type = st.sidebar.radio("Type", ["Commune", "Département", "Classement"])
    
    if search_type == "Commune":
        # Sélection département
        dept_list = sorted(df_ircom['nom_departement'].dropna().unique())
        dept = st.sidebar.selectbox("Département", dept_list)
        
        # Sélection commune
        communes = df_ircom[df_ircom['nom_departement'] == dept]['nom_commune'].sort_values().unique()
        commune = st.sidebar.selectbox("Commune", communes)
        
        # Données
        data_commune = df_ircom[
            (df_ircom['nom_departement'] == dept) & 
            (df_ircom['nom_commune'] == commune)
        ].iloc[0]
        
        # Affichage
        st.header(f"📍 {commune} ({dept})")
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'revenu_moyen_foyer' in data_commune:
                st.metric("Revenu moyen/foyer", 
                         f"{int(data_commune['revenu_moyen_foyer']):,} €".replace(',', ' '))
        
        with col2:
            if 'impot_moyen' in data_commune:
                st.metric("Impôt moyen", 
                         f"{int(data_commune['impot_moyen']):,} €".replace(',', ' '))
        
        with col3:
            if 'nb_foyers_fiscaux' in data_commune:
                st.metric("Foyers fiscaux", 
                         f"{int(data_commune['nb_foyers_fiscaux']):,}".replace(',', ' '))
        
        with col4:
            if 'revenu_brut_total' in data_commune:
                revenu_total = int(data_commune['revenu_brut_total'] / 1_000_000)
                st.metric("Revenu total", f"{revenu_total} M€")
        
        # Filosofi (si disponible)
        if not df_filosofi.empty:
            code_insee = str(data_commune['code_commune']).zfill(5)
            paup_data = df_filosofi[df_filosofi['code_commune'].astype(str).str.zfill(5) == code_insee]
            
            if not paup_data.empty:
                st.subheader("📉 Indicateurs sociaux (FILOSOFI 2021)")
                row = paup_data.iloc[0]
                
                col1, col2, col3 = st.columns(3)
                
                if 'revenu_median_uc' in row and pd.notna(row['revenu_median_uc']):
                    col1.metric(
                        "Revenu médian/UC",
                        f"{int(row['revenu_median_uc']):,} €".replace(',', ' '),
                        help="Revenu disponible médian par Unité de Consommation"
                    )
                
                if 'taux_pauvrete_60' in row and pd.notna(row['taux_pauvrete_60']):
                    col2.metric(
                        "Taux de pauvreté",
                        f"{row['taux_pauvrete_60']:.1f} %",
                        help="Seuil à 60% du revenu médian national",
                        delta=f"{row['taux_pauvrete_60'] - 14.5:.1f} pts" if 'taux_pauvrete_60' in row else None
                    )
                
                if 'rapport_interdecile' in row and pd.notna(row['rapport_interdecile']):
                    col3.metric(
                        "Rapport D9/D1",
                        f"{row['rapport_interdecile']:.1f}",
                        help="Inégalités : les 10% les plus riches gagnent X fois plus que les 10% les plus pauvres"
                    )
        
        # Graphique comparatif
        st.subheader("📊 Positionnement national")
        
        if 'revenu_moyen_foyer' in data_commune:
            revenu_commune = float(data_commune['revenu_moyen_foyer'])
            revenu_national = df_ircom['revenu_moyen_foyer'].mean()
            percentile = (df_ircom['revenu_moyen_foyer'] < revenu_commune).mean() * 100
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = revenu_commune,
                    number = {'suffix': " €", 'font': {'size': 40}},
                    title = {'text': "Revenu moyen par foyer"},
                    gauge = {
                        'axis': {'range': [None, df_ircom['revenu_moyen_foyer'].quantile(0.95)]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, revenu_national], 'color': "lightgray"},
                            {'range': [revenu_national, df_ircom['revenu_moyen_foyer'].quantile(0.95)], 'color': "gray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': revenu_national
                        }
                    }
                ))
                fig.update_layout(height=250)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.metric(
                    "Revenu national moyen",
                    f"{int(revenu_national):,} €".replace(',', ' '),
                    delta=f"{int(revenu_commune - revenu_national):,} €".replace(',', ' '),
                    delta_color="normal"
                )
                st.metric(
                    "Percentile national",
                    f"{percentile:.0f}ème",
                    help=f"Cette commune est plus riche que {percentile:.0f}% des communes françaises"
                )
    
    elif search_type == "Département":
        # Liste des départements
        dept_list = []
        for _, row in df_ircom[['code_departement', 'nom_departement']].drop_duplicates().iterrows():
            if pd.notna(row['code_departement']) and pd.notna(row['nom_departement']):
                dept_list.append(f"{str(row['code_departement']).zfill(2)} - {row['nom_departement']}")
        dept_list = sorted(dept_list)
        
        selected = st.sidebar.selectbox("Département", dept_list)
        dept_code = selected.split(' - ')[0].zfill(2)
        dept_name = selected.split(' - ')[1]
        
        # Données du département
        data_dept = df_ircom[df_ircom['code_departement'].astype(str).str.zfill(2) == dept_code]
        
        st.header(f"🗺️ {dept_name} ({dept_code})")
        
        # Stats départementales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Communes", len(data_dept))
        
        with col2:
            if 'revenu_moyen_foyer' in data_dept.columns:
                revenu_moyen = data_dept['revenu_moyen_foyer'].mean()
                st.metric("Revenu moyen", f"{int(revenu_moyen):,} €".replace(',', ' '))
        
        with col3:
            if 'impot_moyen' in data_dept.columns:
                impot_moyen = data_dept['impot_moyen'].mean()
                st.metric("Impôt moyen", f"{int(impot_moyen):,} €".replace(',', ' '))
        
        with col4:
            if 'nb_foyers_fiscaux' in data_dept.columns:
                foyers_total = int(data_dept['nb_foyers_fiscaux'].sum())
                st.metric("Foyers fiscaux", f"{foyers_total:,}".replace(',', ' '))
        
        # Top 10
        st.subheader("🏅 Communes les plus aisées")
        top10 = data_dept.nlargest(10, 'revenu_moyen_foyer')[
            ['nom_commune', 'revenu_moyen_foyer', 'impot_moyen', 'nb_foyers_fiscaux']
        ].copy()
        
        top10['revenu_moyen_foyer'] = top10['revenu_moyen_foyer'].apply(
            lambda x: f"{int(x):,} €".replace(',', ' ')
        )
        top10['impot_moyen'] = top10['impot_moyen'].apply(
            lambda x: f"{int(x):,} €".replace(',', ' ')
        )
        top10['nb_foyers_fiscaux'] = top10['nb_foyers_fiscaux'].apply(
            lambda x: f"{int(x):,}".replace(',', ' ')
        )
        
        st.dataframe(top10, use_container_width=True, hide_index=True)
        
        # Distribution
        fig = px.histogram(
            data_dept,
            x='revenu_moyen_foyer',
            nbins=30,
            title=f"Distribution des revenus moyens par commune - {dept_name}",
            labels={'revenu_moyen_foyer': 'Revenu moyen (€)'},
            color_discrete_sequence=['#3366CC']
        )
        fig.add_vline(
            x=df_ircom['revenu_moyen_foyer'].mean(),
            line_dash="dash",
            line_color="red",
            annotation_text="Moyenne nationale"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    else:  # Classement
        st.header("🏆 Classements nationaux")
        
        tab1, tab2 = st.tabs(["Départements", "Communes"])
        
        with tab1:
            # Top départements
            dept_stats = df_ircom.groupby(['code_departement', 'nom_departement']).agg({
                'revenu_moyen_foyer': 'mean',
                'impot_moyen': 'mean',
                'nb_foyers_fiscaux': 'sum'
            }).round(0).reset_index()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💰 Top 10 départements les plus riches")
                top_dept = dept_stats.nlargest(10, 'revenu_moyen_foyer')
                top_display = top_dept[['nom_departement', 'revenu_moyen_foyer', 'impot_moyen']].copy()
                top_display['revenu_moyen_foyer'] = top_display['revenu_moyen_foyer'].apply(
                    lambda x: f"{int(x):,} €".replace(',', ' ')
                )
                top_display['impot_moyen'] = top_display['impot_moyen'].apply(
                    lambda x: f"{int(x):,} €".replace(',', ' ')
                )
                st.dataframe(top_display, use_container_width=True, hide_index=True)
            
            with col2:
                st.subheader("📉 Top 10 départements les moins riches")
                bottom_dept = dept_stats.nsmallest(10, 'revenu_moyen_foyer')
                bottom_display = bottom_dept[['nom_departement', 'revenu_moyen_foyer', 'impot_moyen']].copy()
                bottom_display['revenu_moyen_foyer'] = bottom_display['revenu_moyen_foyer'].apply(
                    lambda x: f"{int(x):,} €".replace(',', ' ')
                )
                bottom_display['impot_moyen'] = bottom_display['impot_moyen'].apply(
                    lambda x: f"{int(x):,} €".replace(',', ' ')
                )
                st.dataframe(bottom_display, use_container_width=True, hide_index=True)
        
        with tab2:
            # Top communes
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💰 Top 20 communes les plus riches")
                top_communes = df_ircom.nlargest(20, 'revenu_moyen_foyer')[
                    ['nom_commune', 'nom_departement', 'revenu_moyen_foyer', 'impot_moyen']
                ].copy()
                top_communes['revenu_moyen_foyer'] = top_communes['revenu_moyen_foyer'].apply(
                    lambda x: f"{int(x):,} €".replace(',', ' ')
                )
                top_communes['impot_moyen'] = top_communes['impot_moyen'].apply(
                    lambda x: f"{int(x):,} €".replace(',', ' ')
                )
                st.dataframe(top_communes, use_container_width=True, hide_index=True)
            
            with col2:
                st.subheader("📉 Top 20 communes les moins riches")
                bottom_communes = df_ircom.nsmallest(20, 'revenu_moyen_foyer')[
                    ['nom_commune', 'nom_departement', 'revenu_moyen_foyer', 'impot_moyen']
                ].copy()
                bottom_communes['revenu_moyen_foyer'] = bottom_communes['revenu_moyen_foyer'].apply(
                    lambda x: f"{int(x):,} €".replace(',', ' ')
                )
                bottom_communes['impot_moyen'] = bottom_communes['impot_moyen'].apply(
                    lambda x: f"{int(x):,} €".replace(',', ' ')
                )
                st.dataframe(bottom_communes, use_container_width=True, hide_index=True)
    
    # Pied de page
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: grey; padding: 10px;'>
        <b>🔍 SOURCES OFFICIELLES</b><br>
        • <b>IRCOM 2024</b> : DGFiP - Données 2023 (septembre 2025)<br>
        • <b>FILOSOFI 2021</b> : INSEE - Dernier millésime disponible (février 2026) - <b>Format .xls</b><br>
        • <b>Prochain Filosofi</b> : Suspendu sine die (suppression taxe d'habitation)<br>
        <br>
        <i>Données sous Licence Ouverte 2.0 - Reproducibilité garantie</i>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
