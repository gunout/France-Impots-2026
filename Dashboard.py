# dashboard_fiscalite_france_complet.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
import zipfile

# Configuration de la page
st.set_page_config(
    page_title="Fiscalité France - Dashboard Complet",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Fiscalité France - Dashboard Complet 2026")
st.markdown("""
---
### 🎯 **3 SOURCES OFFICIELLES - DONNÉES 2024-2026**
| Source | Millésime | Mise à jour | Thème |
|--------|-----------|-------------|--------|
| **IRCOM** | 2024 | Septembre 2025 | Impôt sur le revenu |
| **FILOSOFI** | 2021 | Février 2026 | Pauvreté, inégalités |
| **REI (TAXE FONCIÈRE)** | 2024-2025 | Janvier 2026 | Taxe foncière TFPB |
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
if 'col_map_ircom' not in st.session_state:
    st.session_state['col_map_ircom'] = {}

# ============================================================
# 1. IRCOM - IMPÔT SUR LE REVENU
# ============================================================
st.header("📂 1. IRCOM 2024 - Impôt sur le revenu")

ircom_file = st.file_uploader(
    "Téléchargez le fichier IRCOM XLS (France entière)",
    type=['xls', 'xlsx'],
    key='ircom_upload'
)

if ircom_file:
    try:
        df_ircom = pd.read_excel(ircom_file, sheet_name=0, dtype=str, engine='openpyxl')
        st.session_state['df_ircom'] = df_ircom
        st.success(f"✅ IRCOM chargé : {len(df_ircom):,} communes")
        
        with st.expander("📋 Aperçu IRCOM"):
            st.dataframe(df_ircom.head(10))
            st.write("**Colonnes disponibles :**")
            st.write(df_ircom.columns.tolist())
    except Exception as e:
        st.error(f"❌ Erreur IRCOM : {e}")

# ============================================================
# 2. FILOSOFI - PAUVRETÉ
# ============================================================
st.header("📉 2. FILOSOFI 2021 - Pauvreté et inégalités")

st.warning("""
⚠️ **Téléchargez la version COMMUNES (≈35 000 lignes), PAS la version IRIS (83 000 lignes)**
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
# 3. TAXE FONCIÈRE - REI
# ============================================================
st.header("🏠 3. TAXE FONCIÈRE 2024-2025 - Fichier REI")

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Téléchargement auto (data.economie.gouv.fr)"):
        url_rei = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-dir/exports/xlsx?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
        
        try:
            with st.spinner("Téléchargement REI..."):
                response = requests.get(url_rei, timeout=45)
                response.raise_for_status()
                df_taxe = pd.read_excel(io.BytesIO(response.content), sheet_name=0, dtype=str, engine='openpyxl')
                st.session_state['df_taxe'] = df_taxe
                st.success(f"✅ Taxe foncière chargée : {len(df_taxe):,} lignes")
        except Exception as e:
            st.error(f"❌ Échec : {e}")

with col2:
    taxe_file = st.file_uploader(
        "Ou upload manuel (XLSX)",
        type=['xlsx', 'xls'],
        key='taxe_upload'
    )
    
    if taxe_file:
        try:
            df_taxe = pd.read_excel(taxe_file, sheet_name=0, dtype=str, engine='openpyxl')
            st.session_state['df_taxe'] = df_taxe
            st.success(f"✅ Taxe foncière chargée : {len(df_taxe):,} lignes")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

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
    
    st.session_state['col_map_ircom'] = col_map
    
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
    
    df_clean['revenu_moyen'] = (df_clean['revenu_brut'] / df_clean['nb_foyers']).round(0)
    
    if 'impot_brut' in df_clean.columns:
        df_clean['impot_moyen'] = (df_clean['impot_brut'] / df_clean['nb_foyers']).round(0)
        df_clean['taux_imposition'] = (df_clean['impot_moyen'] / df_clean['revenu_moyen'] * 100).round(1)
    
    st.session_state['df_clean'] = df_clean

# ============================================================
# 5. PRÉPARATION DES DONNÉES TAXE FONCIÈRE
# ============================================================
def prepare_taxe_data(df):
    """Nettoie les données du fichier REI"""
    if df is None or df.empty:
        return pd.DataFrame(), {}
    
    df_taxe_clean = df.copy()
    col_map_taxe = {}
    
    for col in df_taxe_clean.columns:
        col_lower = col.lower()
        
        if any(x in col_lower for x in ['codgeo', 'code insee', 'code commune', 'depcom']):
            col_map_taxe['code_commune'] = col
        elif any(x in col_lower for x in ['libgeo', 'nom commune', 'commune']):
            col_map_taxe['nom_commune'] = col
        elif 'taux commune' in col_lower and ('tfp' in col_lower or 'foncière' in col_lower):
            col_map_taxe['taux_tfpb_commune'] = col
        elif 'taux groupement' in col_lower and ('tfp' in col_lower or 'foncière' in col_lower):
            col_map_taxe['taux_tfpb_interco'] = col
        elif 'taux département' in col_lower and ('tfp' in col_lower or 'foncière' in col_lower):
            col_map_taxe['taux_tfpb_departement'] = col
        elif 'base nette' in col_lower and ('tfp' in col_lower or 'foncière' in col_lower):
            col_map_taxe['base_tfpb'] = col
    
    # Conversion numérique
    for key in ['taux_tfpb_commune', 'taux_tfpb_interco', 'taux_tfpb_departement', 'base_tfpb']:
        if key in col_map_taxe:
            col = col_map_taxe[key]
            df_taxe_clean[key] = pd.to_numeric(
                df_taxe_clean[col].astype(str).str.replace(',', '.').str.replace(' ', ''),
                errors='coerce'
            )
    
    # Taux total
    taux_cols = []
    for t in ['taux_tfpb_commune', 'taux_tfpb_interco', 'taux_tfpb_departement']:
        if t in df_taxe_clean.columns:
            taux_cols.append(t)
    
    if taux_cols:
        df_taxe_clean['taux_tfpb_total'] = df_taxe_clean[taux_cols].sum(axis=1, skipna=True).round(2)
    
    return df_taxe_clean, col_map_taxe

# ============================================================
# 6. ANALYSE PRINCIPALE
# ============================================================
if st.session_state['df_ircom'] is not None and 'df_clean' in st.session_state:
    
    df_clean = st.session_state['df_clean']
    col_map = st.session_state['col_map_ircom']
    
    # Sélection département
    st.sidebar.header("📍 Sélection géographique")
    
    if 'nom_departement' in col_map:
        dept_list = sorted(df_clean[col_map['nom_departement']].dropna().unique())
        dept = st.sidebar.selectbox("Département", dept_list)
        
        if 'nom_commune' in col_map:
            mask = df_clean[col_map['nom_departement']] == dept
            communes = df_clean[mask][col_map['nom_commune']].sort_values().unique()
            commune = st.sidebar.selectbox("Commune", communes)
            
            # Données de la commune
            data_commune = df_clean[
                (df_clean[col_map['nom_departement']] == dept) & 
                (df_clean[col_map['nom_commune']] == commune)
            ].iloc[0]
            
            # ========================================================
            # AFFICHAGE PRINCIPAL - TOUS LES INDICATEURS
            # ========================================================
            st.header(f"🏛️ {commune} ({dept})")
            
            # LIGNE 1 : IMPÔT SUR LE REVENU
            st.subheader("📊 Impôt sur le revenu (IRCOM 2024)")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Revenu moyen / foyer",
                    f"{int(data_commune['revenu_moyen']):,} €".replace(',', ' ')
                )
            with col2:
                if 'impot_moyen' in data_commune:
                    st.metric(
                        "Impôt moyen",
                        f"{int(data_commune['impot_moyen']):,} €".replace(',', ' ')
                    )
            with col3:
                if 'taux_imposition' in data_commune:
                    st.metric(
                        "Taux d'imposition moyen",
                        f"{data_commune['taux_imposition']:.1f} %"
                    )
            with col4:
                st.metric(
                    "Foyers fiscaux",
                    f"{int(data_commune['nb_foyers']):,}".replace(',', ' ')
                )
            
            # LIGNE 2 : FILOSOFI (PAUVRETÉ)
            if st.session_state['df_filosofi'] is not None:
                st.subheader("📉 Pauvreté et inégalités (FILOSOFI 2021)")
                
                df_filosofi = st.session_state['df_filosofi']
                
                # Trouver le code commune
                if 'code_commune' in col_map:
                    code_insee = str(data_commune[col_map['code_commune']]).zfill(5)
                    
                    # Trouver colonne code dans Filosofi
                    code_col = None
                    for col in df_filosofi.columns:
                        if any(x in col.lower() for x in ['codgeo', 'code insee', 'depcom']):
                            code_col = col
                            break
                    
                    if code_col:
                        paup_data = df_filosofi[df_filosofi[code_col].astype(str).str.zfill(5) == code_insee]
                        
                        if not paup_data.empty:
                            row = paup_data.iloc[0]
                            col1, col2, col3 = st.columns(3)
                            
                            # Revenu médian
                            for col in row.index:
                                if 'q212' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        col1.metric(
                                            "Revenu médian / UC",
                                            f"{int(val):,} €".replace(',', ' '),
                                            help="Revenu disponible médian par Unité de Consommation"
                                        )
                                        break
                                    except: pass
                            
                            # Taux pauvreté
                            for col in row.index:
                                if 'tp60' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        col2.metric(
                                            "Taux de pauvreté (60%)",
                                            f"{val:.1f} %",
                                            help="Seuil à 60% du revenu médian national"
                                        )
                                        break
                                    except: pass
                            
                            # Rapport interdécile
                            for col in row.index:
                                if 'd1d9' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        col3.metric(
                                            "Rapport D9/D1",
                                            f"{val:.1f}",
                                            help="Les 10% les plus riches gagnent X fois plus que les 10% les plus pauvres"
                                        )
                                        break
                                    except: pass
                        else:
                            st.info(f"ℹ️ Données Filosofi non disponibles pour {commune}")
            
            # LIGNE 3 : TAXE FONCIÈRE
            if st.session_state['df_taxe'] is not None:
                st.subheader("🏠 Taxe foncière sur propriétés bâties (REI 2024-2025)")
                
                df_taxe_raw = st.session_state['df_taxe']
                df_taxe, taxe_col_map = prepare_taxe_data(df_taxe_raw)
                
                if not df_taxe.empty and 'code_commune' in col_map:
                    code_insee = str(data_commune[col_map['code_commune']]).zfill(5)
                    
                    # Chercher la commune
                    taxe_commune = None
                    for code_col in ['code_commune', 'CODGEO', 'Code commune']:
                        if code_col in df_taxe.columns:
                            mask = df_taxe[code_col].astype(str).str.zfill(5) == code_insee
                            if mask.any():
                                taxe_commune = df_taxe[mask].iloc[0]
                                break
                    
                    if taxe_commune is not None:
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if 'taux_tfpb_commune' in taxe_commune and pd.notna(taxe_commune['taux_tfpb_commune']):
                                st.metric(
                                    "Taux communal",
                                    f"{taxe_commune['taux_tfpb_commune']:.2f} %"
                                )
                        
                        with col2:
                            if 'taux_tfpb_interco' in taxe_commune and pd.notna(taxe_commune['taux_tfpb_interco']):
                                st.metric(
                                    "Taux intercommunal",
                                    f"{taxe_commune['taux_tfpb_interco']:.2f} %"
                                )
                        
                        with col3:
                            if 'taux_tfpb_departement' in taxe_commune and pd.notna(taxe_commune['taux_tfpb_departement']):
                                st.metric(
                                    "Taux départemental",
                                    f"{taxe_commune['taux_tfpb_departement']:.2f} %"
                                )
                        
                        with col4:
                            if 'taux_tfpb_total' in taxe_commune and pd.notna(taxe_commune['taux_tfpb_total']):
                                st.metric(
                                    "Taux total cumulé",
                                    f"{taxe_commune['taux_tfpb_total']:.2f} %",
                                    help="Taux communal + intercommunal + départemental"
                                )
                        
                        # Base nette
                        if 'base_tfpb' in taxe_commune and pd.notna(taxe_commune['base_tfpb']):
                            base_millions = taxe_commune['base_tfpb'] / 1_000_000
                            st.metric(
                                "Base nette (valeur locative)",
                                f"{base_millions:.1f} M€"
                            )
                    else:
                        st.info(f"ℹ️ Données de taxe foncière non disponibles pour {commune}")
            
            # ========================================================
            # COMPARAISONS NATIONALES
            # ========================================================
            st.subheader("📊 Positionnement national")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Revenu
                revenu_national = df_clean['revenu_moyen'].mean()
                percentile_rev = (df_clean['revenu_moyen'] < float(data_commune['revenu_moyen'])).mean() * 100
                
                st.metric(
                    "Revenu moyen - France",
                    f"{int(revenu_national):,} €".replace(',', ' '),
                    delta=f"{int(data_commune['revenu_moyen'] - revenu_national):,} €".replace(',', ' '),
                    delta_color="normal"
                )
                st.caption(f"**Percentile : {percentile_rev:.0f}ème** (plus riche que {percentile_rev:.0f}% des communes)")
            
            with col2:
                # Taux imposition
                if 'taux_imposition' in data_commune:
                    taux_national = df_clean['taux_imposition'].median()
                    percentile_taux = (df_clean['taux_imposition'] < float(data_commune['taux_imposition'])).mean() * 100
                    
                    st.metric(
                        "Taux d'imposition - France",
                        f"{taux_national:.1f} %",
                        delta=f"{data_commune['taux_imposition'] - taux_national:.1f} pts",
                        delta_color="inverse"
                    )
                    st.caption(f"**Percentile : {percentile_taux:.0f}ème** (taux plus élevé que {percentile_taux:.0f}% des communes)")
            
            # ========================================================
            # GRAPHIQUES
            # ========================================================
            st.subheader(f"📈 Distribution des revenus - {dept}")
            
            data_dept = df_clean[df_clean[col_map['nom_departement']] == dept]
            
            fig = px.histogram(
                data_dept,
                x='revenu_moyen',
                nbins=30,
                title=f"Revenu moyen par foyer fiscal - {dept}",
                labels={'revenu_moyen': 'Revenu annuel (€)', 'count': 'Nombre de communes'},
                color_discrete_sequence=['#3366CC']
            )
            
            fig.add_vline(
                x=float(data_commune['revenu_moyen']),
                line_dash="dash",
                line_color="red",
                annotation_text=f" {commune}",
                annotation_position="top"
            )
            
            fig.add_vline(
                x=revenu_national,
                line_dash="dot",
                line_color="green",
                annotation_text=" France",
                annotation_position="bottom"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # ========================================================
            # TABLEAU DE BORD RÉCAPITULATIF
            # ========================================================
            with st.expander("📋 Tableau de bord complet - Tous les indicateurs"):
                recap = {
                    "Indicateur": [
                        "Revenu moyen par foyer",
                        "Impôt moyen par foyer",
                        "Taux d'imposition moyen",
                        "Nombre de foyers fiscaux",
                        "Revenu médian par UC (Filosofi)",
                        "Taux de pauvreté (Filosofi)",
                        "Rapport interdécile (Filosofi)",
                        "Taux TFPB communal",
                        "Taux TFPB intercommunal", 
                        "Taux TFPB départemental",
                        "Taux TFPB total",
                        "Base nette TFPB"
                    ],
                    "Valeur": [],
                    "Année": []
                }
                
                # IRCOM
                recap["Valeur"].append(f"{int(data_commune['revenu_moyen']):,} €".replace(',', ' '))
                recap["Année"].append("2024")
                
                if 'impot_moyen' in data_commune:
                    recap["Valeur"].append(f"{int(data_commune['impot_moyen']):,} €".replace(',', ' '))
                else:
                    recap["Valeur"].append("N/A")
                recap["Année"].append("2024")
                
                if 'taux_imposition' in data_commune:
                    recap["Valeur"].append(f"{data_commune['taux_imposition']:.1f} %")
                else:
                    recap["Valeur"].append("N/A")
                recap["Année"].append("2024")
                
                recap["Valeur"].append(f"{int(data_commune['nb_foyers']):,}".replace(',', ' '))
                recap["Année"].append("2024")
                
                # FILOSOFI
                if st.session_state['df_filosofi'] is not None and 'code_commune' in col_map:
                    code_insee = str(data_commune[col_map['code_commune']]).zfill(5)
                    code_col = None
                    for col in df_filosofi.columns:
                        if any(x in col.lower() for x in ['codgeo', 'code insee']):
                            code_col = col
                            break
                    
                    if code_col:
                        paup = df_filosofi[df_filosofi[code_col].astype(str).str.zfill(5) == code_insee]
                        if not paup.empty:
                            row = paup.iloc[0]
                            
                            # Revenu médian
                            val_med = "N/A"
                            for col in row.index:
                                if 'q212' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        val_med = f"{int(val):,} €".replace(',', ' ')
                                    except: pass
                            recap["Valeur"].append(val_med)
                            recap["Année"].append("2021")
                            
                            # Taux pauvreté
                            val_pauvrete = "N/A"
                            for col in row.index:
                                if 'tp60' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        val_pauvrete = f"{val:.1f} %"
                                    except: pass
                            recap["Valeur"].append(val_pauvrete)
                            recap["Année"].append("2021")
                            
                            # Rapport interdécile
                            val_d1d9 = "N/A"
                            for col in row.index:
                                if 'd1d9' in col.lower():
                                    try:
                                        val = float(str(row[col]).replace(',', '.'))
                                        val_d1d9 = f"{val:.1f}"
                                    except: pass
                            recap["Valeur"].append(val_d1d9)
                            recap["Année"].append("2021")
                        else:
                            recap["Valeur"].extend(["N/A", "N/A", "N/A"])
                            recap["Année"].extend(["2021", "2021", "2021"])
                else:
                    recap["Valeur"].extend(["N/A", "N/A", "N/A"])
                    recap["Année"].extend(["2021", "2021", "2021"])
                
                # TAXE FONCIÈRE
                if st.session_state['df_taxe'] is not None and 'code_commune' in col_map:
                    code_insee = str(data_commune[col_map['code_commune']]).zfill(5)
                    df_taxe_raw = st.session_state['df_taxe']
                    df_taxe, _ = prepare_taxe_data(df_taxe_raw)
                    
                    taxe_commune = None
                    for code_col in ['code_commune', 'CODGEO', 'Code commune']:
                        if code_col in df_taxe.columns:
                            mask = df_taxe[code_col].astype(str).str.zfill(5) == code_insee
                            if mask.any():
                                taxe_commune = df_taxe[mask].iloc[0]
                                break
                    
                    if taxe_commune is not None:
                        recap["Valeur"].append(f"{taxe_commune.get('taux_tfpb_commune', 'N/A'):.2f} %" if isinstance(taxe_commune.get('taux_tfpb_commune'), (int, float)) else "N/A")
                        recap["Année"].append("2024")
                        
                        recap["Valeur"].append(f"{taxe_commune.get('taux_tfpb_interco', 'N/A'):.2f} %" if isinstance(taxe_commune.get('taux_tfpb_interco'), (int, float)) else "N/A")
                        recap["Année"].append("2024")
                        
                        recap["Valeur"].append(f"{taxe_commune.get('taux_tfpb_departement', 'N/A'):.2f} %" if isinstance(taxe_commune.get('taux_tfpb_departement'), (int, float)) else "N/A")
                        recap["Année"].append("2024")
                        
                        recap["Valeur"].append(f"{taxe_commune.get('taux_tfpb_total', 'N/A'):.2f} %" if isinstance(taxe_commune.get('taux_tfpb_total'), (int, float)) else "N/A")
                        recap["Année"].append("2024")
                        
                        recap["Valeur"].append(f"{taxe_commune.get('base_tfpb', 0)/1_000_000:.1f} M€" if isinstance(taxe_commune.get('base_tfpb'), (int, float)) else "N/A")
                        recap["Année"].append("2024")
                    else:
                        recap["Valeur"].extend(["N/A", "N/A", "N/A", "N/A", "N/A"])
                        recap["Année"].extend(["2024", "2024", "2024", "2024", "2024"])
                else:
                    recap["Valeur"].extend(["N/A", "N/A", "N/A", "N/A", "N/A"])
                    recap["Année"].extend(["2024", "2024", "2024", "2024", "2024"])
                
                df_recap = pd.DataFrame(recap)
                st.dataframe(df_recap, use_container_width=True, hide_index=True)

else:
    st.info("👈 Commencez par charger le fichier IRCOM (obligatoire) pour accéder à l'analyse")

# ============================================================
# PIED DE PAGE
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: grey; padding: 10px;'>
    <b>🏆 DASHBOARD FISCALITÉ FRANCE - VERSION COMPLÈTE 2026</b><br>
    <b>Sources :</b> 
    <a href='https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom'>IRCOM 2024</a> • 
    <a href='https://www.data.gouv.fr/datasets/donnees-de-revenus-localises-filosofi'>FILOSOFI 2021</a> • 
    <a href='https://data.economie.gouv.fr/explore/dataset/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-dir'>REI 2024-2025</a><br>
    <b>3 indicateurs - 1 interface - 0 compromis</b>
</div>
""", unsafe_allow_html=True)
