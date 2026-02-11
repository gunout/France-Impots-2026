# dashboard_impots_france_FINAL.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import zipfile
import io
import tempfile
import os

st.set_page_config(page_title="Fiscalité France 2026", layout="wide")
st.title("💰 Fiscalité France - Données Officielles 2026")

st.markdown("""
---
### 📥 TÉLÉCHARGEZ LES 2 FICHIERS MANUELLEMENT :

1. **IRCOM 2024** (impôt sur le revenu)  
   👉 [https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom](https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom)  
   ➡️ Cliquez sur **Télécharger** → Fichier **ZIP** contenant des **fichiers XLS**

2. **FILOSOFI 2021** (pauvreté, inégalités)  
   👉 [https://www.data.gouv.fr/datasets/donnees-de-revenus-localises-filosofi](https://www.data.gouv.fr/datasets/donnees-de-revenus-localises-filosofi)  
   ➡️ Cliquez sur **Télécharger** → Fichier **XLS** "Communes"
---
""")

# ============================================================
# 1. CHARGEMENT IRCOM - FORMAT XLS DANS UN ZIP
# ============================================================
st.header("📂 1. Chargez le fichier IRCOM (ZIP contenant des XLS)")

ircom_zip = st.file_uploader(
    "Téléchargez le fichier ZIP téléchargé depuis data.gouv.fr",
    type=['zip'],
    key='ircom_zip'
)

df_ircom = None

if ircom_zip:
    with st.spinner("📦 Extraction et lecture des fichiers XLS..."):
        with zipfile.ZipFile(ircom_zip) as z:
            fichiers = z.namelist()
            st.info(f"Fichiers dans le ZIP : {fichiers}")
            
            # Cherche tous les fichiers XLS
            fichiers_xls = [f for f in fichiers if f.endswith('.xls')]
            
            if not fichiers_xls:
                st.error("❌ Aucun fichier XLS trouvé dans le ZIP")
            else:
                # Prend le premier fichier XLS (souvent le national)
                with z.open(fichiers_xls[0]) as f:
                    # Lecture du XLS avec openpyxl
                    df_ircom = pd.read_excel(f, sheet_name=0, dtype=str, engine='openpyxl')
                st.success(f"✅ IRCOM chargé : {len(df_ircom):,} communes")
                
                # Affiche les colonnes disponibles
                with st.expander("📋 Voir les colonnes disponibles"):
                    st.write(df_ircom.columns.tolist())

# ============================================================
# 2. CHARGEMENT FILOSOFI - FORMAT XLS
# ============================================================
st.header("📊 2. Chargez le fichier FILOSOFI (XLS)")

filosofi_file = st.file_uploader(
    "Téléchargez le fichier XLS 'Communes' de Filosofi",
    type=['xls', 'xlsx'],
    key='filosofi_xls'
)

df_filosofi = None

if filosofi_file:
    with st.spinner("📖 Lecture du fichier Excel..."):
        df_filosofi = pd.read_excel(
            filosofi_file,
            sheet_name=0,
            dtype=str,
            engine='openpyxl'
        )
        st.success(f"✅ FILOSOFI chargé : {len(df_filosofi):,} communes")
        
        with st.expander("📋 Voir les colonnes Filosofi"):
            st.write(df_filosofi.columns.tolist())

# ============================================================
# 3. INTERFACE D'ANALYSE (seulement si IRCOM est chargé)
# ============================================================
if df_ircom is not None:
    st.header("📈 ANALYSE FISCALE")
    
    # === NETTOYAGE DES DONNÉES IRCOM ===
    df_clean = df_ircom.copy()
    
    # Mapping des colonnes (adaptez selon votre fichier)
    # Les noms peuvent varier, on cherche les colonnes par ressemblance
    colonnes = df_clean.columns.tolist()
    
    # Détection automatique des colonnes
    col_map = {}
    for col in colonnes:
        col_lower = col.lower()
        if 'codgeo' in col_lower or 'code_insee' in col_lower or 'code commune' in col_lower:
            col_map['code_commune'] = col
        elif 'libgeo' in col_lower or 'nom commune' in col_lower or 'commune' in col_lower:
            col_map['nom_commune'] = col
        elif 'dep' in col_lower and 'lib' not in col_lower:
            col_map['code_departement'] = col
        elif 'libdep' in col_lower or 'departement' in col_lower:
            col_map['nom_departement'] = col
        elif 'nb_foy' in col_lower or 'nombre de foyers' in col_lower:
            col_map['nb_foyers'] = col
        elif 'rev_tot' in col_lower or 'revenu total' in col_lower or 'revenu brut' in col_lower:
            col_map['revenu_total'] = col
        elif 'imp_tot' in col_lower or 'impot total' in col_lower:
            col_map['impot_total'] = col
    
    st.sidebar.header("🔧 Configuration")
    st.sidebar.write("Colonnes détectées :")
    for role, col in col_map.items():
        st.sidebar.write(f"- {role}: **{col}**")
    
    # Si des colonnes sont manquantes, permettre la sélection manuelle
    if 'revenu_total' not in col_map:
        col_map['revenu_total'] = st.sidebar.selectbox(
            "Colonne 'Revenu total'",
            options=colonnes
        )
    if 'nb_foyers' not in col_map:
        col_map['nb_foyers'] = st.sidebar.selectbox(
            "Colonne 'Nombre de foyers'",
            options=colonnes
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
    if 'revenu_brut' in df_clean.columns and 'nb_foyers' in df_clean.columns:
        df_clean['revenu_moyen'] = (df_clean['revenu_brut'] / df_clean['nb_foyers']).round(0)
    
    if 'impot_brut' in df_clean.columns and 'nb_foyers' in df_clean.columns:
        df_clean['impot_moyen'] = (df_clean['impot_brut'] / df_clean['nb_foyers']).round(0)
    
    if 'revenu_moyen' in df_clean.columns and 'impot_moyen' in df_clean.columns:
        df_clean['taux_imposition'] = (df_clean['impot_moyen'] / df_clean['revenu_moyen'] * 100).round(1)
    
    # === SÉLECTION GÉOGRAPHIQUE ===
    st.sidebar.header("📍 Sélection")
    
    # Département
    if 'nom_departement' in col_map:
        dept_list = sorted(df_clean[col_map['nom_departement']].dropna().unique())
    else:
        dept_list = ["Aucun département détecté"]
    
    if dept_list and dept_list[0] != "Aucun département détecté":
        dept = st.sidebar.selectbox("Département", dept_list)
        
        # Commune
        mask = df_clean[col_map['nom_departement']] == dept
        if 'nom_commune' in col_map:
            communes = df_clean[mask][col_map['nom_commune']].sort_values().unique()
            commune = st.sidebar.selectbox("Commune", communes)
            
            # Données de la commune
            data_commune = df_clean[
                (df_clean[col_map['nom_departement']] == dept) & 
                (df_clean[col_map['nom_commune']] == commune)
            ].iloc[0]
            
            # === AFFICHAGE PRINCIPAL ===
            st.header(f"🏛️ {commune} ({dept})")
            
            # KPIs
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if 'revenu_moyen' in data_commune and pd.notna(data_commune['revenu_moyen']):
                    st.metric(
                        "Revenu moyen / foyer",
                        f"{int(data_commune['revenu_moyen']):,} €".replace(',', ' ')
                    )
            
            with col2:
                if 'impot_moyen' in data_commune and pd.notna(data_commune['impot_moyen']):
                    st.metric(
                        "Impôt moyen",
                        f"{int(data_commune['impot_moyen']):,} €".replace(',', ' ')
                    )
            
            with col3:
                if 'taux_imposition' in data_commune and pd.notna(data_commune['taux_imposition']):
                    st.metric(
                        "Taux d'imposition moyen",
                        f"{data_commune['taux_imposition']:.1f} %"
                    )
            
            with col4:
                if 'nb_foyers' in data_commune and pd.notna(data_commune['nb_foyers']):
                    st.metric(
                        "Foyers fiscaux",
                        f"{int(data_commune['nb_foyers']):,}".replace(',', ' ')
                    )
            
            # === DONNÉES FILOSOFI ===
            if df_filosofi is not None and 'code_commune' in col_map:
                code_insee = str(data_commune[col_map['code_commune']]).zfill(5)
                
                # Chercher la colonne code commune dans Filosofi
                code_col = None
                for col in df_filosofi.columns:
                    if 'codgeo' in col.lower() or 'code insee' in col.lower() or 'code commune' in col.lower():
                        code_col = col
                        break
                
                if code_col:
                    paup_data = df_filosofi[df_filosofi[code_col].astype(str).str.zfill(5) == code_insee]
                    
                    if not paup_data.empty:
                        st.subheader("📉 Indicateurs de pauvreté et inégalités (FILOSOFI 2021)")
                        
                        row = paup_data.iloc[0]
                        col1, col2, col3 = st.columns(3)
                        
                        # Cherche les colonnes de revenu médian
                        for col in row.index:
                            if 'q212' in col.lower() or 'revenu median' in col.lower() or 'mediane' in col.lower():
                                try:
                                    val = float(str(row[col]).replace(',', '.'))
                                    col1.metric("Revenu médian / UC", f"{int(val):,} €".replace(',', ' '))
                                    break
                                except:
                                    pass
                        
                        # Cherche le taux de pauvreté
                        for col in row.index:
                            if 'tp60' in col.lower() or 'taux pauvreté' in col.lower():
                                try:
                                    val = float(str(row[col]).replace(',', '.'))
                                    col2.metric("Taux de pauvreté (60%)", f"{val:.1f} %")
                                    break
                                except:
                                    pass
                        
                        # Cherche le rapport interdécile
                        for col in row.index:
                            if 'd1d9' in col.lower() or 'rapport interdecile' in col.lower():
                                try:
                                    val = float(str(row[col]).replace(',', '.'))
                                    col3.metric("Rapport D9/D1", f"{val:.1f}")
                                    break
                                except:
                                    pass
            
            # === COMPARAISON NATIONALE ===
            st.subheader("📊 Positionnement national")
            
            if 'revenu_moyen' in df_clean.columns and 'revenu_moyen' in data_commune:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gauge
                    revenu_commune = float(data_commune['revenu_moyen'])
                    revenu_national = df_clean['revenu_moyen'].mean()
                    percentile = (df_clean['revenu_moyen'] < revenu_commune).mean() * 100
                    
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=revenu_commune,
                        number={'suffix': " €", 'font': {'size': 35}},
                        title={'text': "Revenu moyen par foyer"},
                        gauge={
                            'axis': {'range': [None, df_clean['revenu_moyen'].quantile(0.95)]},
                            'bar': {'color': "royalblue"},
                            'steps': [
                                {'range': [0, revenu_national], 'color': 'lightgray'},
                                {'range': [revenu_national, df_clean['revenu_moyen'].quantile(0.95)], 'color': 'gray'}
                            ],
                            'threshold': {
                                'line': {'color': 'red', 'width': 4},
                                'thickness': 0.75,
                                'value': revenu_national
                            }
                        }
                    ))
                    fig.update_layout(height=250, margin=dict(l=10, r=10, t=50, b=10))
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.metric(
                        "Moyenne nationale",
                        f"{int(revenu_national):,} €".replace(',', ' '),
                        delta=f"{int(revenu_commune - revenu_national):,} €".replace(',', ' '),
                        delta_color="normal"
                    )
                    st.metric(
                        "Percentile",
                        f"{percentile:.0f}ème",
                        help=f"Cette commune est plus riche que {percentile:.0f}% des communes françaises"
                    )
            
            # === DISTRIBUTION DÉPARTEMENTALE ===
            st.subheader(f"📊 Distribution des revenus dans le {dept}")
            
            data_dept = df_clean[df_clean[col_map['nom_departement']] == dept]
            
            fig = px.histogram(
                data_dept,
                x='revenu_moyen',
                nbins=30,
                title=f"Revenu moyen par commune - {dept}",
                labels={'revenu_moyen': 'Revenu moyen (€)', 'count': 'Nombre de communes'},
                color_discrete_sequence=['#3366CC']
            )
            
            # Ajout de la ligne de la commune sélectionnée
            fig.add_vline(
                x=revenu_commune,
                line_dash="dash",
                line_color="red",
                annotation_text=f" {commune}",
                annotation_position="top"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.warning("⚠️ Impossible de détecter les départements. Vérifiez les colonnes.")
        
        # Affichage brut des données
        with st.expander("📋 Voir les données brutes"):
            st.dataframe(df_clean.head(100))
            
            # Stats générales
            if 'revenu_moyen' in df_clean.columns:
                st.write(f"Revenu moyen national : {df_clean['revenu_moyen'].mean():,.0f} €")

else:
    st.info("👈 Commencez par charger le fichier ZIP IRCOM (format XLS)")

# ============================================================
# PIED DE PAGE
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: grey; padding: 10px;'>
    <b>🔍 SOURCES OFFICIELLES - MISE À JOUR FÉVRIER 2026</b><br>
    • <b>IRCOM 2024</b> : DGFiP - Données 2023 - Format XLS dans ZIP<br>
    • <b>FILOSOFI 2021</b> : INSEE - Dernier millésime disponible - Format XLS<br>
    • <b>Note</b> : Les fichiers XLS sont lus directement avec openpyxl<br>
    <br>
    <i>Licence Ouverte 2.0 - Reproducibilité garantie par upload manuel</i>
</div>
""", unsafe_allow_html=True)
