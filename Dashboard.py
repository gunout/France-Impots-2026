# dashboard_impots_france_2026.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import zipfile
import io
from pathlib import Path
import tempfile

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Fiscalité France 2026",
    page_icon="💰",
    layout="wide"
)

# --- 1. CHARGEMENT IRCOM (DONNÉES FISCALES PRINCIPALES) ---
@st.cache_data(ttl=86400)  # Cache 24h
def load_ircom_data():
    """
    Charge les données IRCOM (Impôt sur le Revenu par Commune)
    Source : data.gouv.fr - mise à jour septembre 2025
    """
    url = "https://www.data.gouv.fr/fr/datasets/r/dfbdb71b-ee76-4b9b-9471-57634a0f2181"
    
    try:
        with st.spinner("📥 Téléchargement des données fiscales IRCOM 2024..."):
            response = requests.get(url)
            response.raise_for_status()
        
        with st.spinner("🔄 Extraction et traitement..."):
            # Décompression du ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # Lister les fichiers
                fichiers = z.namelist()
                
                # Chercher le fichier national ou régional
                fichier_principal = None
                for f in fichiers:
                    if 'france-entiere' in f.lower() and f.endswith('.csv'):
                        fichier_principal = f
                        break
                
                if not fichier_principal:
                    # Sinon prendre le premier CSV
                    fichier_principal = [f for f in fichiers if f.endswith('.csv')][0]
                
                # Lecture du fichier
                with z.open(fichier_principal) as csv_file:
                    df = pd.read_csv(csv_file, sep=';', encoding='utf-8', dtype=str)
        
        # Nettoyage et conversion
        df_clean = df.copy()
        
        # Identification des colonnes (noms variables selon millésime)
        col_mapping = {
            'codgeo': 'code_commune',
            'libgeo': 'nom_commune',
            'epci': 'code_epci',
            'libepci': 'nom_epci',
            'dep': 'code_departement',
            'libdep': 'nom_departement',
            'reg': 'code_region',
            'libreg': 'nom_region',
            'nb_foyers': 'nb_foyers_fiscaux',
            'nb_parts': 'nb_parts_fiscales',
            'nb_pers': 'nb_personnes',
            'rev_tot': 'revenu_brut_total',
            'rev_decl': 'revenu_declare_total',
            'rev_moy': 'revenu_moyen',
            'rev_med': 'revenu_median',
            'imp_tot': 'impot_total',
            'imp_moy': 'impot_moyen'
        }
        
        # Renommage des colonnes existantes
        existing_cols = {col: new_col for col, new_col in col_mapping.items() 
                        if col in df_clean.columns}
        df_clean = df_clean.rename(columns=existing_cols)
        
        # Conversion numérique
        numeric_cols = ['nb_foyers_fiscaux', 'nb_parts_fiscales', 'nb_personnes',
                       'revenu_brut_total', 'revenu_declare_total', 'revenu_moyen',
                       'revenu_median', 'impot_total', 'impot_moyen']
        
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(
                    df_clean[col].astype(str).str.replace(',', '.'),
                    errors='coerce'
                )
        
        # Calculs dérivés
        if 'impot_total' in df_clean.columns and 'nb_foyers_fiscaux' in df_clean.columns:
            df_clean['impot_moyen_calcule'] = (
                df_clean['impot_total'] / df_clean['nb_foyers_fiscaux']
            ).round(0)
        
        if 'revenu_brut_total' in df_clean.columns and 'nb_foyers_fiscaux' in df_clean.columns:
            df_clean['revenu_moyen_foyer'] = (
                df_clean['revenu_brut_total'] / df_clean['nb_foyers_fiscaux']
            ).round(0)
        
        # Taux d'imposition moyen
        if 'impot_total' in df_clean.columns and 'revenu_brut_total' in df_clean.columns:
            df_clean['taux_imposition_moyen'] = (
                df_clean['impot_total'] / df_clean['revenu_brut_total'] * 100
            ).round(1)
        
        return df_clean
        
    except Exception as e:
        st.error(f"Erreur chargement IRCOM : {e}")
        return pd.DataFrame()

# --- 2. CHARGEMENT FILOSOFI (DONNÉES COMPLÉMENTAIRES) ---
@st.cache_data(ttl=86400)
def load_filosofi_data():
    """
    Charge les données FILOSOFI (pauvreté, inégalités)
    Source : data.gouv.fr - mise à jour février 2026
    """
    url = "https://www.data.gouv.fr/fr/datasets/r/d1f5bb6b-00be-4869-99d5-e8d7e71c12ea"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Détection du format (XLS ou CSV)
        content_type = response.headers.get('content-type', '')
        
        if 'excel' in content_type.lower() or '.xls' in url:
            df = pd.read_excel(io.BytesIO(response.content), sheet_name=0, dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(response.content), sep=';', encoding='latin1', dtype=str)
        
        # Nettoyage minimal
        df_clean = df.copy()
        
        # Renommage intelligent
        col_map = {
            'CODGEO': 'code_commune',
            'LIBGEO': 'nom_commune',
            'Q212': 'revenu_median_uc',  # Médiane des revenus par UC
            'TP60': 'taux_pauvrete_60',  # Taux de pauvreté à 60%
            'TP61': 'taux_pauvrete_40',  # Taux de pauvreté à 40%
            'TP62': 'taux_pauvrete_50',  # Taux de pauvreté à 50%
            'D1D9': 'rapport_interdecile',  # D9/D1 - inégalités
        }
        
        existing_map = {k: v for k, v in col_map.items() if k in df_clean.columns}
        df_clean = df_clean.rename(columns=existing_map)
        
        # Conversion numérique
        for col in existing_map.values():
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(
                    df_clean[col].astype(str).str.replace(',', '.'),
                    errors='coerce'
                )
        
        return df_clean
        
    except Exception as e:
        st.warning(f"⚠️ Données FILOSOFI non disponibles : {e}")
        return pd.DataFrame()

# --- 3. FONCTIONS DE VISUALISATION ---
def display_commune_stats(df_ircom, df_filosofi, commune, code_insee=None):
    """Affiche tous les indicateurs pour une commune"""
    
    # Données IRCOM
    if code_insee:
        data_commune = df_ircom[df_ircom['code_commune'].astype(str).str.zfill(5) == code_insee]
    else:
        data_commune = df_ircom[df_ircom['nom_commune'].str.upper() == commune.upper()]
    
    if data_commune.empty:
        st.warning(f"Commune '{commune}' non trouvée")
        return
    
    row = data_commune.iloc[0]
    
    # KPIs principaux
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Foyers fiscaux",
            f"{int(row['nb_foyers_fiscaux']):,}".replace(',', ' ')
        )
    
    with col2:
        st.metric(
            "Revenu moyen / foyer",
            f"{int(row['revenu_moyen_foyer']):,} €".replace(',', ' ')
        )
    
    with col3:
        if 'revenu_median' in row.index and pd.notna(row['revenu_median']):
            st.metric(
                "Revenu médian",
                f"{int(row['revenu_median']):,} €".replace(',', ' ')
            )
    
    with col4:
        if 'impot_moyen' in row.index and pd.notna(row['impot_moyen']):
            st.metric(
                "Impôt moyen",
                f"{int(row['impot_moyen']):,} €".replace(',', ' ')
            )
        elif 'impot_moyen_calcule' in row.index:
            st.metric(
                "Impôt moyen",
                f"{int(row['impot_moyen_calcule']):,} €".replace(',', ' ')
            )
    
    with col5:
        if 'taux_imposition_moyen' in row.index and pd.notna(row['taux_imposition_moyen']):
            st.metric(
                "Taux d'imposition moyen",
                f"{row['taux_imposition_moyen']:.1f} %"
            )
    
    # Données Filosofi (pauvreté)
    if not df_filosofi.empty and code_insee:
        data_pauvrete = df_filosofi[df_filosofi['code_commune'].astype(str).str.zfill(5) == code_insee]
        
        if not data_pauvrete.empty:
            st.subheader("📊 Indicateurs de pauvreté et inégalités (FILOSOFI 2021)")
            col1, col2, col3 = st.columns(3)
            
            row_p = data_pauvrete.iloc[0]
            
            with col1:
                if 'revenu_median_uc' in row_p.index and pd.notna(row_p['revenu_median_uc']):
                    st.metric(
                        "Revenu médian par UC*",
                        f"{int(row_p['revenu_median_uc']):,} €".replace(',', ' ')
                    )
            
            with col2:
                if 'taux_pauvrete_60' in row_p.index and pd.notna(row_p['taux_pauvrete_60']):
                    st.metric(
                        "Taux de pauvreté (60%)",
                        f"{row_p['taux_pauvrete_60']:.1f} %"
                    )
            
            with col3:
                if 'rapport_interdecile' in row_p.index and pd.notna(row_p['rapport_interdecile']):
                    st.metric(
                        "Rapport interdécile D9/D1",
                        f"{row_p['rapport_interdecile']:.1f}"
                    )
            
            st.caption("* UC = Unité de consommation")

def display_department_map(df, dept_code):
    """Carte choroplèthe des revenus par commune"""
    
    dept_data = df[df['code_departement'].astype(str).str.zfill(2) == dept_code]
    
    if dept_data.empty:
        st.warning(f"Département {dept_code} non trouvé")
        return
    
    fig = px.choropleth_mapbox(
        dept_data,
        geojson=None,  # Nécessite un GeoJSON, simplification ici
        locations='code_commune',
        color='revenu_moyen_foyer',
        hover_name='nom_commune',
        hover_data={
            'revenu_moyen_foyer': ':,.0f',
            'nb_foyers_fiscaux': ':,.0f',
            'taux_imposition_moyen': ':.1f'
        },
        color_continuous_scale='Viridis',
        mapbox_style='open-street-map',
        zoom=8,
        title=f"Revenu moyen par foyer fiscal - Département {dept_code}",
        labels={'revenu_moyen_foyer': 'Revenu moyen (€)'}
    )
    
    fig.update_layout(margin={'r': 0, 't': 40, 'l': 0, 'b': 0})
    st.plotly_chart(fig, use_container_width=True)

def display_comparison_table(df, level='departement', top_n=20):
    """Classement des territoires"""
    
    if level == 'departement':
        grouped = df.groupby(['code_departement', 'nom_departement']).agg({
            'revenu_moyen_foyer': 'mean',
            'impot_moyen_calcule': 'mean',
            'taux_imposition_moyen': 'mean',
            'nb_foyers_fiscaux': 'sum'
        }).round(0).reset_index()
        
        display_df = grouped.nlargest(top_n, 'revenu_moyen_foyer')
        title = f"🏆 Top {top_n} départements - Revenu moyen par foyer"
    
    else:  # communes
        grouped = df.nlargest(top_n, 'revenu_moyen_foyer')[
            ['nom_commune', 'nom_departement', 'revenu_moyen_foyer', 
             'impot_moyen_calcule', 'taux_imposition_moyen']
        ]
        display_df = grouped
        title = f"🏆 Top {top_n} communes - Revenu moyen par foyer"
    
    # Formatage
    display_df['revenu_moyen_foyer'] = display_df['revenu_moyen_foyer'].apply(
        lambda x: f"{x:,.0f} €".replace(',', ' ')
    )
    
    if 'impot_moyen_calcule' in display_df.columns:
        display_df['impot_moyen_calcule'] = display_df['impot_moyen_calcule'].apply(
            lambda x: f"{x:,.0f} €".replace(',', ' ')
        )
    
    if 'taux_imposition_moyen' in display_df.columns:
        display_df['taux_imposition_moyen'] = display_df['taux_imposition_moyen'].apply(
            lambda x: f"{x:.1f} %"
        )
    
    st.subheader(title)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- 4. INTERFACE PRINCIPALE ---
def main():
    st.title("💰 Dashboard Fiscalité France 2026")
    st.markdown("""
    **Données fiscales officielles** : IRCOM 2024 (revenus 2023) - Mise à jour septembre 2025  
    **Complément** : FILOSOFI 2021 (pauvreté, inégalités) - Mise à jour février 2026
    """)
    
    # Chargement des données
    df_ircom = load_ircom_data()
    df_filosofi = load_filosofi_data()
    
    if df_ircom.empty:
        st.error("❌ Impossible de charger les données IRCOM")
        st.stop()
    
    st.success(f"✅ {len(df_ircom):,} communes chargées")
    
    # Sidebar - Navigation
    st.sidebar.header("🔍 Navigation")
    
    menu = st.sidebar.radio(
        "Mode d'affichage",
        ["Recherche par commune", "Analyse départementale", "Classements nationaux"]
    )
    
    if menu == "Recherche par commune":
        st.sidebar.subheader("📍 Sélectionnez une commune")
        
        # Sélection du département
        dept_list = sorted(df_ircom['nom_departement'].dropna().unique())
        selected_dept = st.sidebar.selectbox("Département", dept_list)
        
        # Filtrage des communes
        communes_dept = df_ircom[
            df_ircom['nom_departement'] == selected_dept
        ]['nom_commune'].sort_values().unique()
        
        selected_commune = st.sidebar.selectbox("Commune", communes_dept)
        
        # Recherche du code INSEE
        code_insee = df_ircom[
            (df_ircom['nom_departement'] == selected_dept) &
            (df_ircom['nom_commune'] == selected_commune)
        ]['code_commune'].iloc[0]
        
        # Affichage
        st.header(f"📊 {selected_commune} ({selected_dept})")
        display_commune_stats(df_ircom, df_filosofi, selected_commune, code_insee)
        
        # Données brutes
        with st.expander("📋 Voir les données détaillées"):
            row = df_ircom[
                (df_ircom['code_commune'].astype(str).str.zfill(5) == code_insee)
            ].iloc[0]
            
            details = {
                'Code INSEE': code_insee,
                'Population fiscale': f"{int(row['nb_personnes']):,}".replace(',', ' '),
                'Nombre de foyers': f"{int(row['nb_foyers_fiscaux']):,}".replace(',', ' '),
                'Revenu brut total': f"{int(row['revenu_brut_total']):,} €".replace(',', ' '),
                'Revenu déclaré total': f"{int(row['revenu_declare_total']):,} €".replace(',', ' '),
                'Impôt total': f"{int(row['impot_total']):,} €".replace(',', ' ')
            }
            
            st.json(details)
    
    elif menu == "Analyse départementale":
        st.sidebar.subheader("🗺️ Sélectionnez un département")
        
        dept_list = sorted(df_ircom[['code_departement', 'nom_departement']]
                          .dropna()
                          .drop_duplicates()
                          .values.tolist())
        
        dept_labels = [f"{d[0]} - {d[1]}" for d in dept_list]
        selected = st.sidebar.selectbox("Département", dept_labels)
        
        dept_code = selected.split(' - ')[0].zfill(2)
        dept_name = selected.split(' - ')[1]
        
        st.header(f"🗺️ Département {dept_code} - {dept_name}")
        
        # Stats départementales
        dept_data = df_ircom[df_ircom['code_departement'].astype(str).str.zfill(2) == dept_code]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Communes", len(dept_data))
        with col2:
            st.metric("Revenu moyen", 
                     f"{int(dept_data['revenu_moyen_foyer'].mean()):,} €".replace(',', ' '))
        with col3:
            st.metric("Impôt moyen",
                     f"{int(dept_data['impot_moyen_calcule'].mean()):,} €".replace(',', ' '))
        
        # Top communes du département
        st.subheader(f"🏅 Communes les plus aisées du {dept_name}")
        top_dept = dept_data.nlargest(10, 'revenu_moyen_foyer')[
            ['nom_commune', 'revenu_moyen_foyer', 'impot_moyen_calcule', 'taux_imposition_moyen']
        ]
        
        top_dept['revenu_moyen_foyer'] = top_dept['revenu_moyen_foyer'].apply(
            lambda x: f"{x:,.0f} €".replace(',', ' ')
        )
        top_dept['impot_moyen_calcule'] = top_dept['impot_moyen_calcule'].apply(
            lambda x: f"{x:,.0f} €".replace(',', ' ')
        )
        top_dept['taux_imposition_moyen'] = top_dept['taux_imposition_moyen'].apply(
            lambda x: f"{x:.1f} %"
        )
        
        st.dataframe(top_dept, use_container_width=True, hide_index=True)
        
        # Histogramme distribution
        fig = px.histogram(
            dept_data,
            x='revenu_moyen_foyer',
            nbins=30,
            title=f"Distribution des revenus moyens par commune - {dept_name}",
            labels={'revenu_moyen_foyer': 'Revenu moyen par foyer (€)', 'count': 'Nombre de communes'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    else:  # Classements
        st.header("🏆 Classements nationaux")
        
        col1, col2 = st.columns(2)
        
        with col1:
            display_comparison_table(df_ircom, level='departement', top_n=20)
        
        with col2:
            display_comparison_table(df_ircom, level='commune', top_n=20)
        
        # Graphique répartition nationale
        st.subheader("📊 Répartition nationale des revenus fiscaux")
        
        # Déciles nationaux (simplifié)
        percentiles = df_ircom['revenu_moyen_foyer'].quantile([0.1, 0.25, 0.5, 0.75, 0.9])
        
        fig = go.Figure()
        fig.add_trace(go.Box(
            x=df_ircom['revenu_moyen_foyer'].dropna(),
            name='Revenu moyen par foyer',
            boxmean='sd'
        ))
        
        fig.update_layout(
            title="Distribution nationale des revenus moyens par commune",
            xaxis_title="Revenu annuel (€)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Pied de page
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: grey; padding: 10px;'>
        <b>Sources officielles</b> : 
        <a href='https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom'>IRCOM 2024 - DGFiP/data.gouv.fr</a> • 
        <a href='https://www.data.gouv.fr/datasets/revenus-et-pauvrete-des-menages-aux-niveaux-national-et-local-revenus-localises-sociaux-et-fiscaux'>FILOSOFI 2021 - Insee</a><br>
        <b>Dernière mise à jour</b> : {}<br>
        <b>Note</b> : Les données FILOSOFI 2022-2023 sont suspendues (suppression taxe d'habitation)
    </div>
    """.format(pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')), 
    unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
