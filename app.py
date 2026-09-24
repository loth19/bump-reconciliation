import streamlit as st
import pandas as pd
import os
import pickle
import plotly.express as px
try:
    from src.engine import load_data, bulk_reconcile, generate_excel_report, parse_date_robust, clean_id
except ModuleNotFoundError:
    from engine import load_data, bulk_reconcile, generate_excel_report, parse_date_robust, clean_id

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

with st.sidebar:
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR05_C-Gg3m6e75o1LhF8s7XbB5j_3jI1K8-g&s", width=120)
    st.subheader("⚡ Bump Finance")
    st.markdown("Outil de réconciliation universel des sessions de recharge.")
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
            
        roaming_id_col = st.selectbox("🟠 Colonne Roaming Session ID :", options=options, index=default_index)

with col2:
    st.subheader("2️⃣ Factures CPO (Dossier ou Import)")
    st.caption("Sélectionne la méthode la plus adaptée pour fournir les factures CPO :")
    
    cpo_method = st.radio("Méthode d'importation :", options=["📁 Dossier local (chemin)", "📤 Glisser-déposer (fichiers/ZIP)"], horizontal=True)
    
    cpo_folder_path = None
    uploaded_cpo_files = None
    
    if cpo_method == "📁 Dossier local (chemin)":
        cpo_folder_path = st.text_input("Chemin du dossier CPO :", value=st.session_state.get("cached_cpo_folder_path", ""), placeholder="C:\\Users\\...\\CPO Cdr")
    else:
        uploaded_cpo_files = st.file_uploader("Glisse tes factures CPO (fichiers Excel/CSV ou archive ZIP) :", type=["xlsx", "csv", "zip"], accept_multiple_files=True, key="cpo_upload")

st.divider()

has_cpo_input = (cpo_method == "📁 Dossier local (chemin)" and cpo_folder_path) or (cpo_method == "📤 Glisser-déposer (fichiers/ZIP)" and uploaded_cpo_files)

if df_cto_preview is not None and has_cpo_input:
    if st.button("🚀 Lancer l'Aspiration Universelle", use_container_width=True, type="primary"):
        with st.spinner("Recherche en cours du Roaming Session ID sur tous les fichiers..."):
            try:
                actual_cpo_folder = ""
                if cpo_method == "📁 Dossier local (chemin)":
                    actual_cpo_folder = cpo_folder_path
                else:
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
                anomalies = bulk_reconcile(df_cto=df_cto, roaming_id_col=roaming_id_col, cpo_folder_path=actual_cpo_folder)
                
                st.session_state["reconcile_results"] = anomalies
                if cpo_method == "📁 Dossier local (chemin)":
                    st.session_state["cached_cpo_folder_path"] = cpo_folder_path
                st.session_state["cached_roaming_id_col"] = roaming_id_col
                
                save_cache(
                    cpo_folder_path=cpo_folder_path if cpo_method == "📁 Dossier local (chemin)" else "",
                    roaming_id_col=roaming_id_col,
                    anomalies_df=anomalies,
                    cto_filename=st.session_state.get("cached_cto_filename", ""),
                    cto_preview=df_cto_preview
                )
                
            except Exception as e:
                st.error(f"Une erreur s'est produite : {e}")

if st.session_state.get("reconcile_results") is not None:
    anomalies = st.session_state["reconcile_results"]
    
    if not anomalies.empty and 'ID_Retrouvé' in anomalies.columns and 'Fichier_Source' in anomalies.columns:
        anomalies['is_xlsx'] = anomalies['Fichier_Source'].str.lower().str.endswith('.xlsx')
        anomalies = anomalies.sort_values(by=['ID_Retrouvé', 'is_xlsx'], ascending=[True, False])
        anomalies = anomalies.drop_duplicates(subset=['ID_Retrouvé'], keep='first')
        anomalies = anomalies.drop(columns=['is_xlsx'])
        anomalies = anomalies.reset_index(drop=True)
    
    df_cto_preview = st.session_state.get("cached_cto_preview")
    roaming_id_col = st.session_state.get("cached_roaming_id_col")
    
    missing_ids = set()
    df_missing = pd.DataFrame()
    
    if df_cto_preview is not None and roaming_id_col in df_cto_preview.columns:
        all_cto_ids = set(df_cto_preview[roaming_id_col].apply(clean_id).tolist())
        all_cto_ids.discard('nan')
        all_cto_ids.discard('')
        
        found_ids = set()
        if not anomalies.empty and 'ID_Retrouvé' in anomalies.columns:
            for val in anomalies['ID_Retrouvé'].dropna():
                for v in str(val).split(','):
                    v_clean = clean_id(v)
                    if v_clean:
                        found_ids.add(v_clean)
        
        missing_ids = all_cto_ids - found_ids
        mask_missing = df_cto_preview[roaming_id_col].apply(lambda x: clean_id(x) in missing_ids)
        df_missing = df_cto_preview[mask_missing].copy()
    
    st.divider()
    st.success("✅ CODE MIS A JOUR : GESTION DES MANQUANTS ACTIVE")
    st.subheader("👻 Sessions Manquantes (Introuvables chez le CPO)")
    
    if len(missing_ids) > 0:
        st.warning(f"Il y a **{len(missing_ids)} sessions** dans ton fichier CTO original qui n'apparaissent dans AUCUNE facture CPO.")
        st.dataframe(df_missing)
    else:
        st.success("🎉 Toutes les sessions de ton CTO ont été retrouvées au moins une fois dans les factures CPO.")

    st.divider()
    st.subheader("🔍 Sessions Retrouvées (En commun)")

    if anomalies.empty:
        st.info("Aucun des Roaming Session IDs du CTO n'a été retrouvé dans les factures.")
    else:
        st.error(f"🚨 ALERTE : {len(anomalies)} sessions du CTO ont été retrouvées dans les factures CPO !")
        
        st.subheader("📊 Indicateurs Clés (KPI)")
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
        
        st.divider()
        st.subheader("📋 Liste Détaillée des Sessions")
        st.dataframe(anomalies)
        
        col_down, col_done = st.columns(2)
        with col_down:
            excel_data = generate_excel_report(anomalies)
            st.download_button("📥 Télécharger le Rapport Complet (Excel)", data=excel_data, file_name="Rapport_Anomalies_Bump.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
        with col_done:
            if st.button("🏁 Terminé (Effacer et Réinitialiser)", use_container_width=True, type="secondary"):
                st.session_state["reconcile_results"] = None
                st.session_state["cached_cpo_folder_path"] = ""
                st.session_state["cached_roaming_id_col"] = ""
                st.session_state["cached_cto_filename"] = ""
                st.session_state["cached_cto_preview"] = None
                clear_cache()
                st.rerun()
