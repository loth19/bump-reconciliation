import streamlit as st
import pandas as pd
import os
import pickle
import plotly.express as px
from src.engine import load_data, bulk_reconcile, generate_excel_report

st.set_page_config(page_title="Bump - Réconciliation Pro", page_icon="⚡", layout="wide")

CACHE_FILE = ".reco_cache.pkl"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    return None

def save_cache(cpo_folder_path, roaming_id_col, anomalies_df, cto_filename, cto_preview):
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump({
                "cpo_folder_path": cpo_folder_path,
                "roaming_id_col": roaming_id_col,
                "anomalies_df": anomalies_df,
                "cto_filename": cto_filename,
                "cto_preview": cto_preview
            }, f)
    except Exception:
        pass

def clear_cache():
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
        except Exception:
            pass

# Chargement du cache au premier chargement de la session Streamlit
if "loaded_from_disk" not in st.session_state:
    cache = load_cache()
    if cache:
        st.session_state["reconcile_results"] = cache.get("anomalies_df")
        st.session_state["cached_cpo_folder_path"] = cache.get("cpo_folder_path", "")
        st.session_state["cached_roaming_id_col"] = cache.get("roaming_id_col", "")
        st.session_state["cached_cto_filename"] = cache.get("cto_filename", "")
        st.session_state["cached_cto_preview"] = cache.get("cto_preview")
    else:
        st.session_state["reconcile_results"] = None
        st.session_state["cached_cpo_folder_path"] = ""
        st.session_state["cached_roaming_id_col"] = ""
        st.session_state["cached_cto_filename"] = ""
        st.session_state["cached_cto_preview"] = None
    st.session_state["loaded_from_disk"] = True

# Barre latérale simplifiée et sécurisée (design entreprise épuré)
with st.sidebar:
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR05_C-Gg3m6e75o1LhF8s7XbB5j_3jI1K8-g&s", width=120)
    st.subheader("⚡ Bump Finance")
    st.markdown("Outil de réconciliation universel des sessions de recharge.")
    
    # Vider la mémoire se fait désormais via le bouton Terminé en bas de page
    pass
            
    st.divider()
    st.caption("Version 2.3 - Entreprise")

st.title("⚡ Bump : L'Aspirateur Universel")
st.markdown("""
Dépose ton fichier CTO et indique le dossier contenant toutes tes factures CPO. 
L'application cherchera le **Roaming Session ID (ID CDR)** dans tous les fichiers de factures.
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ Fichier du CTO")
    st.caption("La liste des sessions sans CDR")
    cto_file = st.file_uploader("Fichier CTO", type=["xlsx", "csv"], key="cto_upload")
    
    df_cto_preview = None
    roaming_id_col = None
    
    if cto_file:
        df_cto_preview = load_data(cto_file)
        st.success(f"✅ {len(df_cto_preview)} sessions chargées")
        st.session_state["cached_cto_preview"] = df_cto_preview
        st.session_state["cached_cto_filename"] = cto_file.name
    elif st.session_state["cached_cto_preview"] is not None:
        df_cto_preview = st.session_state["cached_cto_preview"]
        st.info(f"📂 Fichier utilisé (depuis la mémoire) : {st.session_state['cached_cto_filename']}")
        
    if df_cto_preview is not None:
        st.markdown("**Sélectionne la colonne d'ID (Roaming Session ID / CDR ID) dans ton fichier CTO :**")
        options = list(df_cto_preview.columns)
        default_index = 0
        cached_col = st.session_state.get("cached_roaming_id_col", "")
        if cached_col in options:
            default_index = options.index(cached_col)
            
        roaming_id_col = st.selectbox(
            "🟠 Colonne Roaming Session ID :", 
            options=options,
            index=default_index
        )

with col2:
    st.subheader("2️⃣ Factures CPO (Dossier ou Import)")
    st.caption("Sélectionne la méthode la plus adaptée pour fournir les factures CPO :")
    
    cpo_method = st.radio(
        "Méthode d'importation :",
        options=["📁 Dossier local (chemin)", "📤 Glisser-déposer (fichiers/ZIP)"],
        horizontal=True
    )
    
    cpo_folder_path = None
    uploaded_cpo_files = None
    
    if cpo_method == "📁 Dossier local (chemin)":
        cpo_folder_path = st.text_input(
            "Chemin du dossier CPO :", 
            value=st.session_state.get("cached_cpo_folder_path", ""),
            placeholder="C:\\Users\\...\\CPO Cdr"
        )
    else:
        uploaded_cpo_files = st.file_uploader(
            "Glisse tes factures CPO (fichiers Excel/CSV ou archive ZIP) :",
            type=["xlsx", "csv", "zip"],
            accept_multiple_files=True,
            key="cpo_upload"
        )

st.divider()

# Le cache est conservé activement et n'est supprimé que via le bouton Terminé en bas
pass

# Activation du bouton
has_cpo_input = (cpo_method == "📁 Dossier local (chemin)" and cpo_folder_path) or (cpo_method == "📤 Glisser-déposer (fichiers/ZIP)" and uploaded_cpo_files)

if df_cto_preview is not None and has_cpo_input:
    if st.button("🚀 Lancer l'Aspiration Universelle", use_container_width=True, type="primary"):
        with st.spinner("Recherche en cours du Roaming Session ID sur tous les fichiers..."):
            try:
                actual_cpo_folder = ""
                if cpo_method == "📁 Dossier local (chemin)":
                    actual_cpo_folder = cpo_folder_path
                else:
                    # Traitement des fichiers téléversés dans un dossier temporaire
                    import zipfile
                    import shutil
                    
                    temp_dir = "temp_cpo_uploads"
                    if os.path.exists(temp_dir):
                        try:
                            shutil.rmtree(temp_dir)
                        except Exception:
                            pass
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    for uploaded_file in uploaded_cpo_files:
                        file_name = uploaded_file.name
                        if file_name.lower().endswith(".zip"):
                            try:
                                with zipfile.ZipFile(uploaded_file) as z:
                                    z.extractall(temp_dir)
                            except Exception as e:
                                st.error(f"Erreur lors de l'extraction de {file_name} : {e}")
                        else:
                            target_path = os.path.join(temp_dir, file_name)
                            with open(target_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                    
                    actual_cpo_folder = temp_dir
                
                df_cto = df_cto_preview.copy()
                
                anomalies = bulk_reconcile(
                    df_cto=df_cto,
                    roaming_id_col=roaming_id_col,
                    cpo_folder_path=actual_cpo_folder
                )
                
                st.session_state["reconcile_results"] = anomalies
                if cpo_method == "📁 Dossier local (chemin)":
                    st.session_state["cached_cpo_folder_path"] = cpo_folder_path
                st.session_state["cached_roaming_id_col"] = roaming_id_col
                
                # Sauvegarder dans le cache physique
                save_cache(
                    cpo_folder_path=cpo_folder_path if cpo_method == "📁 Dossier local (chemin)" else "",
                    roaming_id_col=roaming_id_col,
                    anomalies_df=anomalies,
                    cto_filename=st.session_state.get("cached_cto_filename", ""),
                    cto_preview=df_cto_preview
                )
                
            except Exception as e:
                st.error(f"Une erreur s'est produite : {e}")

# Affichage des résultats s'ils existent dans le session_state
if st.session_state["reconcile_results"] is not None:
    anomalies = st.session_state["reconcile_results"]
    
    if anomalies.empty:
        st.balloons()
        st.success("🎉 Aucune anomalie détectée ! Aucun des Roaming Session IDs n'a été retrouvé dans les factures.")
    else:
        st.error(f"🚨 ALERTE : {len(anomalies)} sessions retrouvées dans les factures CPO !")
        
        # ---- SECTION KPIs ----
        st.subheader("📊 Indicateurs Clés (KPI)")
        
        # Calculs
        total_due = anomalies['Montant_HT'].abs().sum() if 'Montant_HT' in anomalies.columns else 0.0
        total_sessions = len(anomalies)
        total_energy = anomalies['Énergie_kWh'].sum() if 'Énergie_kWh' in anomalies.columns else 0.0
        total_duration_hours = (anomalies['Durée_Minutes'].sum() / 60.0) if 'Durée_Minutes' in anomalies.columns else 0.0
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("💸 Montant Total Dû (Valeur Absolue)", f"{total_due:,.2f} €")
        with col_m2:
            st.metric("🚗 Sessions Contestées", f"{total_sessions} sessions")
        with col_m3:
            st.metric("⚡ Énergie Totale", f"{total_energy:,.1f} kWh" if not pd.isna(total_energy) else "0.0 kWh")
        with col_m4:
            st.metric("⏱️ Durée Totale", f"{total_duration_hours:,.1f} h" if not pd.isna(total_duration_hours) else "0.0 h")
        
        # ---- SECTION GRAPHIQUE ----
        st.divider()
        
        # Extraction des dates pour le filtrage par année et affichage par mois
        df_chart = anomalies.copy()
        if 'Date_Début' in df_chart.columns and not df_chart.empty:
            df_chart['Date_Parsed'] = pd.to_datetime(df_chart['Date_Début'], utc=True, errors='coerce')
            
            # Année et Mois
            df_chart['Année'] = df_chart['Date_Parsed'].dt.year.fillna(pd.Timestamp.now().year).astype(int)
            months_fr = {
                1: "01 - Janvier", 2: "02 - Février", 3: "03 - Mars", 4: "04 - Avril",
                5: "05 - Mai", 6: "06 - Juin", 7: "07 - Juillet", 8: "08 - Août",
                9: "09 - Septembre", 10: "10 - Octobre", 11: "11 - Novembre", 12: "12 - Décembre"
            }
            df_chart['Mois'] = df_chart['Date_Parsed'].dt.month.fillna(1).map(months_fr)
            df_chart['Montant_HT_Abs'] = df_chart['Montant_HT'].abs() if 'Montant_HT' in df_chart.columns else 0.0
            
            years = sorted(df_chart['Année'].unique(), reverse=True)
            
            col_title, col_filter = st.columns([3, 1])
            with col_title:
                st.subheader("📈 Analyse Financière par CPO & Mois (Montant Dû)")
            with col_filter:
                if len(years) > 1:
                    selected_year = st.selectbox("📅 Choisir l'Année :", options=years)
                else:
                    selected_year = years[0] if years else pd.Timestamp.now().year
                    st.info(f"📅 Année affichée : {selected_year}")
            
            # Filtrer par année
            df_year = df_chart[df_chart['Année'] == selected_year]
            
            if not df_year.empty:
                # Groupe par CPO et Mois pour faire l'histogramme cumulé
                df_grouped = df_year.groupby(['CPO', 'Mois'], as_index=False)['Montant_HT_Abs'].sum()
                
                # Classement des CPO par montant total dû (décroissant) pour l'ordre sur l'abscisse
                cpo_order = df_year.groupby('CPO')['Montant_HT_Abs'].sum().sort_values(ascending=False).index.tolist()
                
                # Création du graphique Plotly Express
                fig = px.bar(
                    df_grouped,
                    x='CPO',
                    y='Montant_HT_Abs',
                    color='Mois',
                    title=f"Répartition du Montant Dû (€) par CPO et par Mois en {selected_year}",
                    labels={'CPO': 'Opérateur CPO', 'Montant_HT_Abs': 'Montant Dû (€)', 'Mois': 'Mois de Recharge'},
                    category_orders={'CPO': cpo_order, 'Mois': sorted(months_fr.values())},
                    color_discrete_sequence=px.colors.qualitative.Prism,
                    text_auto='.2f'
                )
                fig.update_layout(
                    barmode='stack',
                    xaxis_title="Opérateurs CPO (classés par montant dû décroissant)",
                    yaxis_title="Total Montant Dû (valeur absolue) en €",
                    hovermode="x unified",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"Aucune donnée d'anomalie pour l'année {selected_year}.")
        
        # ---- TABLEAU DE DÉTAILS ----
        st.divider()
        st.subheader("📋 Liste Détaillée des Anomalies")
        st.dataframe(anomalies)
        
        col_down, col_done = st.columns(2)
        with col_down:
            excel_data = generate_excel_report(anomalies)
            st.download_button(
                label="📥 Télécharger le Rapport Complet (Excel)",
                data=excel_data,
                file_name="Rapport_Anomalies_Bump.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
        with col_done:
            if st.button("🏁 Terminé (Effacer et Réinitialiser)", use_container_width=True, type="secondary"):
                st.session_state["reconcile_results"] = None
                st.session_state["cached_cpo_folder_path"] = ""
                st.session_state["cached_roaming_id_col"] = ""
                st.session_state["cached_cto_filename"] = ""
                st.session_state["cached_cto_preview"] = None
                clear_cache()
                st.rerun()
