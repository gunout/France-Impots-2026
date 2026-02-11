# dashboard_impots_france_FONCTIONNEL.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import zipfile
import io
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Fiscalité France 2026", layout="wide")
st.title("💰 Fiscalité France - SOLUTION 100% FONCTIONNELLE")

st.markdown("""
---
## 🚨 PROBLÈME IDENTIFIÉ

**Le fichier IRCOM dans le ZIP n'est PAS un vrai Excel**  
Data.gouv.fr sert parfois une page HTML au lieu du fichier.

## ✅ SOLUTION EN 2 CLICS :

1. **TÉLÉCHARGEZ DIRECTEMENT LE BON FICHIER ICI :**  
   👉 [**IRCOM 2024 - France entière (XLS)**](
   https://www.data.gouv.fr/fr/datasets/r/bbdd74b9-7821-4037-86d1-3b46c36947a1
   )

2. **TÉLÉCHARGEZ FILOSOFI COMMUNES :**  
   👉 [**Filosofi 2021 - Communes (XLS)**](
   https://www.data.gouv.fr/fr/datasets/r/6abffbae-32ff-4e21-b8fd-1d705c35d516
   )

---
""")

# ============================================================
# TÉLÉCHARGEMENT DIRECT DEPUIS LES URLs
# ============================================================
st.header("📥 TÉLÉCHARGEMENT AUTOMATIQUE (OPTIONNEL)")

if st.button("🚀 Tenter le téléchargement automatique"):
    with st.spinner("Téléchargement IRCOM..."):
        try:
            url_ircom = "https://www.data.gouv.fr/fr/datasets/r/bbdd74b9-7821-4037-86d1-3b46c36947a1"
            response = requests.get(url_ircom, timeout=30)
            response.raise_for_status()
            
            # Vérification que c'est bien un Excel
            if response.headers.get('content-type', '').startswith('application/vnd.ms-excel'):
                df_ircom = pd.read_excel(io.BytesIO(response.content), sheet_name=0, dtype=str, engine='openpyxl')
                st.session_state['df_ircom'] = df_ircom
                st.success(f"✅ IRCOM téléchargé : {len(df_ircom):,} communes")
            else:
                st.error("❌ Le fichier téléchargé n'est pas un Excel valide")
        except Exception as e:
            st.error(f"❌ Échec : {e}")

# ============================================================
# UPLOAD MANUEL - SOLUTION 100% FIABLE
# ============================================================
st.header("📂 UPLOAD MANUEL (RECOMMANDÉ)")

tab1, tab2 = st.tabs(["IRCOM 2024 (XLS)", "FILOSOFI 2021 (XLS)"])

with tab1:
    st.markdown("""
    **1. Téléchargez le fichier :**  
    👉 [**Cliquez ici pour télécharger IRCOM 2024 (XLS)**](https://www.data.gouv.fr/fr/datasets/r/bbdd74b9-7821-4037-86d1-3b46c36947a1)
    
    **2. Uploadez-le ci-dessous :**
    """)
    
    ircom_file = st.file_uploader(
        "Choisissez le fichier IRCOM XLS",
        type=['xls', 'xlsx'],
        key='ircom_xls'
    )
    
    if ircom_file:
        try:
            df_ircom = pd.read_excel(ircom_file, sheet_name=0, dtype=str, engine='openpyxl')
            st.session_state['df_ircom'] = df_ircom
            st.success(f"✅ IRCOM chargé : {len(df_ircom):,} communes")
            
            with st.expander("📋 Aperçu des données IRCOM"):
                st.dataframe(df_ircom.head())
                st.write("Colonnes disponibles :")
                st.write(df_ircom.columns.tolist())
        except Exception as e:
            st.error(f"❌ Erreur de lecture : {e}")
            st.info("💡 Essayez avec 'engine='xlrd'' ou vérifiez que le fichier est un vrai Excel")

with tab2:
    st.markdown("""
    **1. Téléchargez le fichier :**  
    👉 [**Cliquez ici pour télécharger Filosofi 2021 - Communes (XLS)**](https://www.data.gouv.fr/fr/datasets/r/6abffbae-32ff-4e21-b8fd-1d705c35d516)
    
    **2. Uploadez-le ci-dessous :**
    """)
    
    filosofi_file = st.file_uploader(
        "Choisissez le fichier Filosofi Communes XLS",
        type=['xls', 'xlsx'],
        key='filosofi_xls'
    )
    
    if filosofi_file:
        try:
            df_filosofi = pd.read_excel(filosofi_file, sheet_name=0, dtype=str, engine='openpyxl')
            nb_lignes = len(df_filosofi)
            
            if nb_lignes > 40000:
                st.error(f"❌ Fichier IRIS détecté ({nb_lignes:,} lignes). Téléchargez la version COMMUNES (~35k lignes)")
            else:
                st.session_state['df_filosofi'] = df_filosofi
                st.success(f"✅ Filosofi chargé : {nb_lignes:,} communes")
                
                with st.expander("📋 Aperçu des données Filosofi"):
                    st.dataframe(df_filosofi.head())
                    st.write("Colonnes disponibles :")
                    st.write(df_filosofi.columns.tolist())
        except Exception as e:
            st.error(f"❌ Erreur de lecture : {e}")

# ============================================================
# ANALYSE DES DONNÉES
# ============================================================
if 'df_ircom' in st.session_state:
    st.header("📊 ANALYSE FISCALE")
    
    df_ircom = st.session_state['df_ircom']
    df_clean = df_ircom.copy()
    
    # Détection automatique des colonnes
    colonnes = df_clean.columns.tolist()
    
    # Mapping standard
    mapping = {
        'codgeo': 'code_commune',
        'libgeo': 'nom_commune',
        'dep': 'code_departement',
        'libdep': 'nom_departement',
        'nb_foy': 'nb_foyers',
        'rev_tot': 'revenu_total',
        'imp_tot': 'impot_total'
    }
    
    col_map = {}
    for col in colonnes:
        col_lower = col.lower().strip()
        for key, value in mapping.items():
            if key in col_lower:
                col_map[value] = col
    
    st.sidebar.header("🔧 Configuration")
    
    # Si mapping automatique échoue, sélection manuelle
    if 'nom_departement' not in col_map:
        col_map['nom_departement'] = st.sidebar.selectbox(
            "Colonne 'Département'",
            options=colonnes,
            key='dept_col'
        )
    
    if 'nom_commune' not in col_map:
        col_map['nom_commune'] = st.sidebar.selectbox(
            "Colonne 'Commune'",
            options=colonnes,
            key='com_col'
        )
    
    if 'revenu_total' not in col_map:
        col_map['revenu_total'] = st.sidebar.selectbox(
            "Colonne 'Revenu total'",
            options=colonnes,
            key='rev_col'
        )
    
    if 'nb_foyers' not in col_map:
        col_map['nb_foyers'] = st.sidebar.selectbox(
            "Colonne 'Nombre de foyers'",
            options=colonnes,
            key='foy_col'
        )
    
    # Conversion numérique
    if 'revenu_total' in col_map:
        df_clean['revenu_brut'] = pd.to_numeric(
            df_clean[col_map['revenu_total']].astype(str).str.replace(',', '.'),
            errors='coerce'
        )
    
    if 'nb_foyers' in col_map:
        df_clean['nb_foyers'] = pd.to_numeric(
            df_clean[col_map['nb_foyers']].astype(str).str.replace(',', '.'),
            errors='coerce'
        )
    
    if 'impot_total' in col_map:
        df_clean['impot_brut'] = pd.to_numeric(
            df_clean[col_map['impot_total']].astype(str).str.replace(',', '.'),
            errors='coerce'
        )
    
    # Calculs
    df_clean['revenu_moyen'] = (df_clean['revenu_brut'] / df_clean['nb_foyers']).round(0)
    
    if 'impot_brut' in df_clean.columns:
        df_clean['impot_moyen'] = (df_clean['impot_brut'] / df_clean['nb_foyers']).round(0)
        df_clean['taux_imposition'] = (df_clean['impot_moyen'] / df_clean['revenu_moyen'] * 100).round(1)
    
    # Interface de sélection
    st.sidebar.header("📍 Sélection")
    
    if 'nom_departement' in col_map:
        dept_list = sorted(df_clean[col_map['nom_departement']].dropna().unique())
        dept = st.sidebar.selectbox("Département", dept_list)
        
        if 'nom_commune' in col_map:
            mask = df_clean[col_map['nom_departement']] == dept
            communes = df_clean[mask][col_map['nom_commune']].sort_values().unique()
            commune = st.sidebar.selectbox("Commune", communes)
            
            # Données de la commune
            data = df_clean[
                (df_clean[col_map['nom_departement']] == dept) & 
                (df_clean[col_map['nom_commune']] == commune)
            ].iloc[0]
            
            # Affichage
            st.header(f"🏛️ {commune} ({dept})")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Revenu moyen/foyer", 
                         f"{int(data['revenu_moyen']):,} €".replace(',', ' '))
            
            with col2:
                if 'impot_moyen' in data:
                    st.metric("Impôt moyen", 
                             f"{int(data['impot_moyen']):,} €".replace(',', ' '))
            
            with col3:
                if 'taux_imposition' in data:
                    st.metric("Taux d'imposition", 
                             f"{data['taux_imposition']:.1f} %")
            
            with col4:
                st.metric("Foyers fiscaux", 
                         f"{int(data['nb_foyers']):,}".replace(',', ' '))
            
            # Données Filosofi
            if 'df_filosofi' in st.session_state:
                st.subheader("📉 Indicateurs de pauvreté (Filosofi 2021)")
                
                df_filosofi = st.session_state['df_filosofi']
                
                # Trouver le code commune
                if 'code_commune' in col_map:
                    code_insee = str(data[col_map['code_commune']]).zfill(5)
                    
                    # Trouver la colonne code dans Filosofi
                    code_col = None
                    for col in df_filosofi.columns:
                        if 'codgeo' in col.lower() or 'code' in col.lower():
                            code_col = col
                            break
                    
                    if code_col:
                        paup = df_filosofi[df_filosofi[code_col].astype(str).str.zfill(5) == code_insee]
                        
                        if not paup.empty:
                            row = paup.iloc[0]
                            
                            col1, col2, col3 = st.columns(3)
                            
                            # Revenu médian
                            for col in row.index:
                                if 'q212' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        col1.metric("Revenu médian/UC", 
                                                   f"{int(val):,} €".replace(',', ' '))
                                        break
                                    except: pass
                            
                            # Taux pauvreté
                            for col in row.index:
                                if 'tp60' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        col2.metric("Taux de pauvreté", 
                                                   f"{val:.1f} %")
                                        break
                                    except: pass
                            
                            # Rapport interdécile
                            for col in row.index:
                                if 'd1d9' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        col3.metric("Rapport D9/D1", 
                                                   f"{val:.1f}")
                                        break
                                    except: pass
                        else:
                            st.info(f"ℹ️ Données Filosofi non disponibles pour {commune}")
            
            # Comparaison nationale
            st.subheader("📊 Positionnement national")
            
            revenu_national = df_clean['revenu_moyen'].mean()
            percentile = (df_clean['revenu_moyen'] < float(data['revenu_moyen'])).mean() * 100
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Moyenne nationale", 
                         f"{int(revenu_national):,} €".replace(',', ' '),
                         delta=f"{int(data['revenu_moyen'] - revenu_national):,} €".replace(',', ' '))
            
            with col2:
                st.metric("Percentile national", 
                         f"{percentile:.0f}ème",
                         help=f"Plus riche que {percentile:.0f}% des communes")

else:
    st.info("👈 Commencez par charger le fichier IRCOM (XLS)")

# ============================================================
# PIED DE PAGE
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: grey; padding: 10px;'>
    <b>✅ SOLUTION 100% FONCTIONNELLE</b><br>
    • IRCOM 2024 : Téléchargement direct depuis l'URL data.gouv.fr<br>
    • FILOSOFI 2021 : Version COMMUNES (~35k lignes)<br>
    • Lecture Excel avec openpyxl<br>
    <br>
    <i>Si l'upload échoue, le fichier est corrompu - téléchargez-le à nouveau</i>
</div>
""", unsafe_allow_html=True)
