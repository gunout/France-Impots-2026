# dashboard_fiscalite_france_ULTRA_ROBUSTE.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# Configuration de la page
st.set_page_config(
    page_title="Fiscalité France - Dashboard Complet",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Fiscalité France - Dashboard Complet 2026")
st.markdown("""
---
### 🎯 **3 SOURCES OFFICIELLES - FORMAT XLS/XLSX DIRECT**
| Source | Millésime | Format | Statut |
|--------|-----------|--------|--------|
| **IRCOM** | 2024 | XLS | ✅ Téléchargement manuel |
| **FILOSOFI** | 2021 | XLS | ✅ Téléchargement manuel |
| **REI (TAXE FONCIÈRE)** | 2024 | XLSX | ⚠️ Plusieurs options ci-dessous |
---
""")

# ============================================================
# INITIALISATION SESSION STATE
# ============================================================
if 'df_ircom' not in st.session_state:
    st.session_state['df_ircom'] = None
if 'df_filosofi' not in st.session_state:
    st.session_state['df_filosofi'] = None
if 'df_taxe' not in st.session_state:
    st.session_state['df_taxe'] = None
if 'df_clean' not in st.session_state:
    st.session_state['df_clean'] = None
if 'col_map' not in st.session_state:
    st.session_state['col_map'] = {}

# ============================================================
# 1. IRCOM - IMPÔT SUR LE REVENU (XLS DIRECT)
# ============================================================
st.header("📂 1. IRCOM 2024 - Impôt sur le revenu")

st.markdown("""
**👉 Téléchargez le fichier XLS (pas ZIP) :**  
[https://www.data.gouv.fr/fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom](https://www.data.gouv.fr/fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom)  
➡️ Cliquez sur **"Télécharger"** → Fichier **.xls** (direct)
""")

ircom_file = st.file_uploader(
    "Téléchargez le fichier IRCOM XLS",
    type=['xls', 'xlsx'],
    key='ircom_upload'
)

if ircom_file:
    try:
        df_ircom = pd.read_excel(ircom_file, sheet_name=0, dtype=str, engine='openpyxl')
        st.session_state['df_ircom'] = df_ircom
        st.success(f"✅ IRCOM chargé : {len(df_ircom):,} lignes")
        
        with st.expander("📋 Aperçu IRCOM"):
            st.dataframe(df_ircom.head(10))
            st.write("**Colonnes disponibles :**")
            st.write(df_ircom.columns.tolist())
    except Exception as e:
        st.error(f"❌ Erreur IRCOM : {e}")

# ============================================================
# 2. FILOSOFI - PAUVRETÉ (XLS DIRECT)
# ============================================================
st.header("📉 2. FILOSOFI 2021 - Pauvreté et inégalités")

st.markdown("""
**👉 Téléchargez la version COMMUNES (≈35k lignes) :**  
[https://www.data.gouv.fr/fr/datasets/donnees-de-revenus-localises-filosofi](https://www.data.gouv.fr/fr/datasets/donnees-de-revenus-localises-filosofi)  
➡️ Scrollez jusqu'à **"Filosofi 2021 - Communes"** → Télécharger (.xls)
""")

filosofi_file = st.file_uploader(
    "Téléchargez le fichier Filosofi Communes XLS",
    type=['xls', 'xlsx'],
    key='filosofi_upload'
)

if filosofi_file:
    try:
        df_filosofi = pd.read_excel(filosofi_file, sheet_name=0, dtype=str, engine='openpyxl')
        nb_lignes = len(df_filosofi)
        
        if nb_lignes > 40000:
            st.error(f"❌ Version IRIS détectée ({nb_lignes:,} lignes). Téléchargez la version COMMUNES.")
        else:
            st.session_state['df_filosofi'] = df_filosofi
            st.success(f"✅ FILOSOFI chargé : {nb_lignes:,} communes")
            
            with st.expander("📋 Aperçu FILOSOFI"):
                st.dataframe(df_filosofi.head(10))
                st.write("**Colonnes disponibles :**")
                st.write(df_filosofi.columns.tolist())
    except Exception as e:
        st.error(f"❌ Erreur FILOSOFI : {e}")

# ============================================================
# 3. TAXE FONCIÈRE - REI (3 SOLUTIONS DE SECOURS)
# ============================================================
st.header("🏠 3. TAXE FONCIÈRE 2024 - Fichier REI")

st.warning("""
⚠️ **L'API data.economie.gouv.fr est instable. Voici 3 solutions :**
""")

tab1, tab2, tab3 = st.tabs(["📥 SOLUTION 1 - Téléchargement auto", "📂 SOLUTION 2 - Upload manuel", "💾 SOLUTION 3 - Données de démonstration"])

with tab1:
    st.markdown("""
    **Tentative de téléchargement automatique**  
    *Source : data.economie.gouv.fr*
    """)
    
    if st.button("🚀 Télécharger les données REI"):
        urls_test = [
            "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-dir/exports/xlsx",
            "https://www.data.gouv.fr/fr/datasets/r/5a4c2f3c-7c8f-4a3d-9b2e-1d8e7f6c5b4a",
            "https://www.collectivites-locales.gouv.fr/files/statistiques/taux_fiscalite_2024.xlsx"
        ]
        
        for i, url in enumerate(urls_test):
            try:
                with st.spinner(f"Tentative {i+1}..."):
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200 and len(response.content) > 10000:
                        df_taxe = pd.read_excel(io.BytesIO(response.content), sheet_name=0, dtype=str, engine='openpyxl')
                        if len(df_taxe) > 0:
                            st.session_state['df_taxe'] = df_taxe
                            st.success(f"✅ Taxe foncière chargée : {len(df_taxe):,} lignes")
                            break
            except:
                continue

with tab2:
    st.markdown("""
    **Téléchargement manuel puis upload**  
    
    1. 👉 **Téléchargez le fichier XLSX manuellement :**  
    [https://www.data.gouv.fr/fr/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-directe-locale/](https://www.data.gouv.fr/fr/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-directe-locale/)
    
    2. Cliquez sur **"Télécharger"** (format XLSX)
    
    3. Uploadez-le ci-dessous :
    """)
    
    taxe_file = st.file_uploader(
        "Choisissez le fichier XLSX téléchargé",
        type=['xlsx', 'xls'],
        key='taxe_upload'
    )
    
    if taxe_file:
        try:
            df_taxe = pd.read_excel(taxe_file, sheet_name=0, dtype=str, engine='openpyxl')
            if len(df_taxe) > 0:
                st.session_state['df_taxe'] = df_taxe
                st.success(f"✅ Taxe foncière chargée : {len(df_taxe):,} lignes")
            else:
                st.error("❌ Fichier vide")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

with tab3:
    st.markdown("""
    **Utiliser des données de démonstration**  
    *Si les téléchargements échouent, activez cette option pour tester le dashboard*
    """)
    
    if st.button("📊 Activer les données de démonstration"):
        # Création d'un DataFrame exemple avec les communes principales
        data_demo = {
            'CODGEO': ['33063', '75056', '13055', '69123', '59350'],
            'LIBGEO': ['Bordeaux', 'Paris', 'Marseille', 'Lyon', 'Lille'],
            'TAUX_COMMUNE': [35.42, 20.50, 42.30, 38.15, 40.22],
            'TAUX_INTERCO': [8.15, 0, 6.80, 7.90, 5.45],
            'TAUX_DEPT': [18.30, 10.20, 19.45, 17.80, 16.90],
            'BASE_NETTE': [1250000000, 8500000000, 980000000, 1100000000, 780000000]
        }
        df_demo = pd.DataFrame(data_demo)
        st.session_state['df_taxe'] = df_demo
        st.success("✅ Données de démonstration chargées (5 grandes villes)")

# ============================================================
# 4. PRÉPARATION DES DONNÉES IRCOM
# ============================================================
if st.session_state['df_ircom'] is not None:
    df_ircom = st.session_state['df_ircom'].copy()
    
    # Détection automatique des colonnes
    colonnes = df_ircom.columns.tolist()
    col_map = {}
    
    mapping = {
        'codgeo': 'code_commune',
        'libgeo': 'nom_commune',
        'dep': 'code_departement',
        'libdep': 'nom_departement',
        'nb_foy': 'nb_foyers',
        'rev_tot': 'revenu_total',
        'imp_tot': 'impot_total'
    }
    
    for col in colonnes:
        col_lower = col.lower()
        for key, val in mapping.items():
            if key in col_lower:
                col_map[val] = col
    
    st.session_state['col_map'] = col_map
    
    # Sidebar - Configuration
    st.sidebar.header("🔧 Configuration IRCOM")
    
    if 'nom_departement' not in col_map:
        col_map['nom_departement'] = st.sidebar.selectbox(
            "Colonne Département", options=colonnes, key='dept_select'
        )
    if 'nom_commune' not in col_map:
        col_map['nom_commune'] = st.sidebar.selectbox(
            "Colonne Commune", options=colonnes, key='com_select'
        )
    if 'revenu_total' not in col_map:
        col_map['revenu_total'] = st.sidebar.selectbox(
            "Colonne Revenu total", options=colonnes, key='rev_select'
        )
    if 'nb_foyers' not in col_map:
        col_map['nb_foyers'] = st.sidebar.selectbox(
            "Colonne Nombre de foyers", options=colonnes, key='foy_select'
        )
    
    # Conversion et calculs
    df_clean = df_ircom.copy()
    
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
    
    # Nettoyage
    df_clean = df_clean.dropna(subset=['revenu_brut', 'nb_foyers'])
    df_clean = df_clean[df_clean['nb_foyers'] > 0]
    df_clean = df_clean[df_clean['revenu_brut'] > 0]
    
    df_clean['revenu_moyen'] = (df_clean['revenu_brut'] / df_clean['nb_foyers']).round(0)
    
    if 'impot_brut' in df_clean.columns:
        df_clean['impot_moyen'] = (df_clean['impot_brut'] / df_clean['nb_foyers']).round(0)
        df_clean['taux_imposition'] = (df_clean['impot_moyen'] / df_clean['revenu_moyen'] * 100).round(1)
    
    st.session_state['df_clean'] = df_clean
    st.sidebar.success(f"✅ {len(df_clean):,} communes valides")

# ============================================================
# 5. PRÉPARATION DES DONNÉES TAXE FONCIÈRE (VERSION ROBUSTE)
# ============================================================
def prepare_taxe_data(df):
    """Nettoie les données du fichier REI ou démo"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df_taxe_clean = df.copy()
    
    # Conversion des colonnes si elles existent
    mapping_taux = {
        'TAUX_COMMUNE': 'taux_tfpb_commune',
        'TAUX_INTERCO': 'taux_tfpb_interco',
        'TAUX_DEPT': 'taux_tfpb_departement',
        'BASE_NETTE': 'base_tfpb'
    }
    
    # Renommage si les colonnes existent
    for old, new in mapping_taux.items():
        if old in df_taxe_clean.columns:
            df_taxe_clean[new] = pd.to_numeric(df_taxe_clean[old], errors='coerce')
    
    # Calcul du taux total
    taux_cols = []
    for col in ['taux_tfpb_commune', 'taux_tfpb_interco', 'taux_tfpb_departement']:
        if col in df_taxe_clean.columns:
            taux_cols.append(col)
    
    if taux_cols:
        df_taxe_clean['taux_tfpb_total'] = df_taxe_clean[taux_cols].sum(axis=1, skipna=True).round(2)
    
    return df_taxe_clean

# ============================================================
# 6. ANALYSE PRINCIPALE
# ============================================================
if st.session_state['df_clean'] is not None:
    
    df_clean = st.session_state['df_clean']
    col_map = st.session_state['col_map']
    
    if 'nom_departement' not in col_map or 'nom_commune' not in col_map:
        st.error("❌ Colonnes Département ou Commune non définies")
        st.stop()
    
    # Sélection département
    st.sidebar.header("📍 Sélection géographique")
    
    dept_series = df_clean[col_map['nom_departement']].dropna().astype(str).str.strip()
    dept_list = sorted(dept_series.unique())
    
    if not dept_list:
        st.error("❌ Aucun département trouvé")
        st.stop()
    
    dept = st.sidebar.selectbox("Département", dept_list)
    
    # Filtrage département
    mask_dept = df_clean[col_map['nom_departement']].astype(str).str.strip() == dept
    df_dept = df_clean[mask_dept].copy()
    
    if df_dept.empty:
        st.warning(f"⚠️ Aucune commune trouvée pour {dept}")
        st.stop()
    
    # Sélection commune
    commune_series = df_dept[col_map['nom_commune']].dropna().astype(str).str.strip()
    communes_list = sorted(commune_series.unique())
    commune = st.sidebar.selectbox("Commune", communes_list)
    
    # Recherche commune
    mask_commune = (
        (df_dept[col_map['nom_commune']].astype(str).str.strip() == commune) &
        (df_dept[col_map['nom_departement']].astype(str).str.strip() == dept)
    )
    
    df_commune = df_dept[mask_commune]
    
    if df_commune.empty:
        st.error(f"❌ Commune '{commune}' non trouvée")
        st.stop()
    
    data_commune = df_commune.iloc[0]
    
    # ========================================================
    # AFFICHAGE PRINCIPAL
    # ========================================================
    st.header(f"🏛️ {commune} ({dept})")
    
    # IRCOM
    st.subheader("📊 Impôt sur le revenu (IRCOM 2024)")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Revenu moyen / foyer", 
                 f"{int(data_commune['revenu_moyen']):,} €".replace(',', ' '))
    with col2:
        if 'impot_moyen' in data_commune:
            st.metric("Impôt moyen", 
                     f"{int(data_commune['impot_moyen']):,} €".replace(',', ' '))
    with col3:
        if 'taux_imposition' in data_commune:
            st.metric("Taux d'imposition", 
                     f"{data_commune['taux_imposition']:.1f} %")
    with col4:
        st.metric("Foyers fiscaux", 
                 f"{int(data_commune['nb_foyers']):,}".replace(',', ' '))
    
    # FILOSOFI
    if st.session_state['df_filosofi'] is not None:
        st.subheader("📉 Pauvreté et inégalités (FILOSOFI 2021)")
        
        df_filosofi = st.session_state['df_filosofi']
        
        if 'code_commune' in col_map:
            code_insee = str(data_commune[col_map['code_commune']]).zfill(5)
            
            code_col = None
            for col in df_filosofi.columns:
                if any(x in col.lower() for x in ['codgeo', 'code insee', 'depcom']):
                    code_col = col
                    break
            
            if code_col:
                df_filosofi[code_col] = df_filosofi[code_col].astype(str).str.zfill(5)
                paup_data = df_filosofi[df_filosofi[code_col] == code_insee]
                
                if not paup_data.empty:
                    row = paup_data.iloc[0]
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
                                col2.metric("Taux de pauvreté (60%)", 
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
                    st.info(f"ℹ️ Données Filosofi non disponibles")
    
    # TAXE FONCIÈRE
    if st.session_state['df_taxe'] is not None:
        st.subheader("🏠 Taxe foncière (REI 2024)")
        
        df_taxe = prepare_taxe_data(st.session_state['df_taxe'])
        
        if not df_taxe.empty and 'code_commune' in col_map:
            code_insee = str(data_commune[col_map['code_commune']]).zfill(5)
            
            # Chercher la commune
            taxe_commune = None
            for code_col in ['CODGEO', 'code_commune', 'Code commune']:
                if code_col in df_taxe.columns:
                    df_taxe[code_col] = df_taxe[code_col].astype(str).str.zfill(5)
                    mask = df_taxe[code_col] == code_insee
                    if mask.any():
                        taxe_commune = df_taxe[mask].iloc[0]
                        break
            
            if taxe_commune is not None:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if 'taux_tfpb_commune' in taxe_commune:
                        st.metric("Taux communal", 
                                f"{taxe_commune['taux_tfpb_commune']:.2f} %")
                with col2:
                    if 'taux_tfpb_interco' in taxe_commune:
                        st.metric("Taux intercommunal", 
                                f"{taxe_commune['taux_tfpb_interco']:.2f} %")
                with col3:
                    if 'taux_tfpb_departement' in taxe_commune:
                        st.metric("Taux départemental", 
                                f"{taxe_commune['taux_tfpb_departement']:.2f} %")
                with col4:
                    if 'taux_tfpb_total' in taxe_commune:
                        st.metric("Taux total cumulé", 
                                f"{taxe_commune['taux_tfpb_total']:.2f} %")
                
                if 'base_tfpb' in taxe_commune:
                    base_millions = taxe_commune['base_tfpb'] / 1_000_000
                    st.metric("Base nette (valeur locative)", 
                            f"{base_millions:.1f} M€")
            else:
                st.info(f"ℹ️ Données taxe foncière non disponibles pour {commune}")
        else:
            st.info("ℹ️ Données taxe foncière non disponibles pour cette commune")
    
    # COMPARAISONS NATIONALES
    st.subheader("📊 Positionnement national")
    
    col1, col2 = st.columns(2)
    
    with col1:
        revenu_national = df_clean['revenu_moyen'].mean()
        percentile_rev = (df_clean['revenu_moyen'] < float(data_commune['revenu_moyen'])).mean() * 100
        st.metric("Revenu moyen - France",
                 f"{int(revenu_national):,} €".replace(',', ' '),
                 delta=f"{int(data_commune['revenu_moyen'] - revenu_national):,} €".replace(',', ' '))
        st.caption(f"**Percentile : {percentile_rev:.0f}ème**")
    
    # GRAPHIQUE
    st.subheader(f"📈 Distribution des revenus - {dept}")
    
    fig = px.histogram(
        df_dept,
        x='revenu_moyen',
        nbins=30,
        title=f"Revenu moyen par foyer fiscal - {dept}",
        labels={'revenu_moyen': 'Revenu annuel (€)', 'count': 'Nombre de communes'},
        color_discrete_sequence=['#3366CC']
    )
    
    fig.add_vline(x=float(data_commune['revenu_moyen']), 
                 line_dash="dash", line_color="red",
                 annotation_text=f" {commune}")
    fig.add_vline(x=revenu_national,
                 line_dash="dot", line_color="green",
                 annotation_text=" France")
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 Commencez par charger le fichier IRCOM (obligatoire)")

# ============================================================
# PIED DE PAGE
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: grey; padding: 10px;'>
    <b>🏆 DASHBOARD FISCALITÉ FRANCE - VERSION ULTRA ROBUSTE</b><br>
    • IRCOM 2024 : ✅ XLS direct<br>
    • FILOSOFI 2021 : ✅ Version COMMUNES<br>
    • TAXE FONCIÈRE : ⚠️ 3 solutions de secours + données démo<br>
    <br>
    <i>💡 Si la taxe foncière ne charge pas, utilisez l'onglet "Données de démonstration"</i>
</div>
""", unsafe_allow_html=True)
