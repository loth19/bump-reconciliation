import pandas as pd
import io
import os

def clean_header_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Détecte si la ligne d'en-tête réelle est décalée vers le bas et la repositionne."""
    if df.empty:
        return df
    termes_header = {
        'cpo', 'emsp', 'evse', 'session', 'duration', 'duree', 'energy', 'energie', 
        'beginning', 'end', 'start', 'debut', 'fin', 'cost', 'price', 'prix', 'amount',
        'valeur', 'billing', 'billing value', 'date', 'time', 'charger', 'chargepoint',
        'borne', 'cdr', 'id'
    }
    max_scan = min(8, len(df))
    for i in range(max_scan):
        row_vals = [str(val).strip().lower() for val in df.iloc[i].values if not pd.isna(val)]
        match_count = 0
        for val in row_vals:
            words = val.replace('_', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ').split()
            if any(w in termes_header for w in words):
                match_count += 1
        if match_count >= 3:
            new_columns = df.iloc[i].tolist()
            cleaned_columns = []
            for col_idx, col in enumerate(new_columns):
                if pd.isna(col) or str(col).strip() == '':
                    cleaned_columns.append(f"Unnamed_{col_idx}")
                else:
                    cleaned_columns.append(str(col).strip())
            df.columns = cleaned_columns
            df = df.iloc[i+1:].reset_index(drop=True)
            break
    return df

def load_data(file_or_path) -> pd.DataFrame:
    """Charge un fichier (CSV ou Excel) en DataFrame Pandas en gérant les encodages, séparateurs et en-têtes décalés."""
    is_path = isinstance(file_or_path, str)
    name = file_or_path.lower() if is_path else file_or_path.name.lower()
    df = None
    
    if name.endswith('.csv'):
        # 1. Détecter le séparateur en lisant uniquement la première ligne (rapide)
        sep = ','
        try:
            if is_path:
                with open(file_or_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline()
            else:
                first_line = file_or_path.readline().decode('utf-8', errors='ignore')
                file_or_path.seek(0)
                
            counts = {';': first_line.count(';'), ',': first_line.count(','), '\t': first_line.count('\t')}
            guessed_sep = max(counts, key=counts.get)
            if counts[guessed_sep] > 0:
                sep = guessed_sep
        except Exception:
            pass
            
        # 2. Tenter l'encodage (le plus probable en premier, puis latin-1 universel)
        for encoding in ['utf-8', 'latin-1', 'utf-8-sig']:
            try:
                if is_path:
                    df = pd.read_csv(file_or_path, sep=sep, encoding=encoding, low_memory=False)
                else:
                    file_or_path.seek(0)
                    df = pd.read_csv(file_or_path, sep=sep, encoding=encoding, low_memory=False)
                break
            except Exception:
                continue
        
        # 3. Recommencer avec on_bad_lines en cas d'erreur de structure
        if df is None:
            try:
                if is_path:
                    df = pd.read_csv(file_or_path, sep=sep, encoding='latin-1', on_bad_lines='skip', low_memory=False)
                else:
                    file_or_path.seek(0)
                    df = pd.read_csv(file_or_path, sep=sep, encoding='latin-1', on_bad_lines='skip', low_memory=False)
            except Exception:
                pass
            
    elif name.endswith(('.xls', '.xlsx')):
        try:
            df = pd.read_excel(file_or_path)
        except Exception:
            pass
            
    if df is not None:
        return clean_header_rows(df)
        
    raise ValueError(f"Impossible de lire le fichier : {name}")

def clean_id(value):
    """Nettoie un ID : enlève les espaces et les .0 résiduels."""
    s = str(value).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s

# Mappage de normalisation pour regrouper les colonnes équivalentes des différents CPOs
COLUMN_MAPPING = {
    # Date/Heure de début
    'start_date_time': 'start_date_time',
    'start_date': 'start_date_time',
    'start date': 'start_date_time',
    'start_datetime': 'start_date_time',
    'start datetime': 'start_date_time',
    'debutsession': 'start_date_time',
    'débutsession': 'start_date_time',
    'date_debut': 'start_date_time',
    'date debut': 'start_date_time',
    'session_startdatetime': 'start_date_time',
    'chargestarttime': 'start_date_time',
    'charge_start_time': 'start_date_time',
    'charge start time': 'start_date_time',
    'charge start': 'start_date_time',
    'charge_start': 'start_date_time',
    'session_start_time': 'start_date_time',
    'session start time': 'start_date_time',
    'beginning date': 'start_date_time',
    'beginning_date': 'start_date_time',
    'debut charge': 'start_date_time',
    'debut_charge': 'start_date_time',
    'date de debut': 'start_date_time',
    'date de début': 'start_date_time',
    'date_de_debut': 'start_date_time',
    'created': 'start_date_time',
    'charge start': 'start_date_time',
    
    # Date/Heure de fin
    'end_date': 'end_date',
    'end date': 'end_date',
    'end_datetime': 'end_date',
    'end datetime': 'end_date',
    'finsession': 'end_date',
    'date_fin': 'end_date',
    'date fin': 'end_date',
    'session_enddatetime': 'end_date',
    'chargeendtime': 'end_date',
    'charge_end_time': 'end_date',
    'charge end time': 'end_date',
    'charge end': 'end_date',
    'charge_end': 'end_date',
    'session_end_time': 'end_date',
    'session end time': 'end_date',
    'fin charge': 'end_date',
    'fin_charge': 'end_date',
    'date de fin': 'end_date',
    'date_de_fin': 'end_date',
    'to': 'end_date',
    'charge end': 'end_date',
    
    # Énergie (standard ou en Wh)
    'energy_consumption': 'energy_consumption',
    'energy': 'energy_consumption',
    'énergie': 'energy_consumption',
    'energie': 'energy_consumption',
    'volume': 'energy_consumption',
    'kwh': 'energy_consumption',
    'consommation': 'energy_consumption',
    'energy(kw.h)': 'energy_consumption',
    'energy (kwh)': 'energy_consumption',
    'energy (kw,h)': 'energy_consumption',
    'energy(kw,h)': 'energy_consumption',
    'energie (kwh)': 'energy_consumption',
    'energie(kwh)': 'energy_consumption',
    'energy (wh)': 'energy_consumption_wh',
    'energie (wh)': 'energy_consumption_wh',
    'energie( wh)': 'energy_consumption_wh',
    'energie (wh)': 'energy_consumption_wh',
    
    # Montant / Chiffre d'affaires HT
    'revenue_wo_vat': 'revenue_wo_vat',
    'revenue': 'revenue_wo_vat',
    'montant ht': 'revenue_wo_vat',
    'montant_ht': 'revenue_wo_vat',
    'cost': 'revenue_wo_vat',
    'price': 'revenue_wo_vat',
    'prix': 'revenue_wo_vat',
    'montant ht ': 'revenue_wo_vat',
    'montant': 'revenue_wo_vat',
    'montant ttc': 'revenue_wo_vat',
    'bill_amount': 'revenue_wo_vat',
    'invoiced_amount': 'revenue_wo_vat',
    'amount': 'revenue_wo_vat',
    'cost (eur ex vat)': 'revenue_wo_vat',
    'total cost (€)': 'revenue_wo_vat',
    'total cost': 'revenue_wo_vat',
    'total_cost': 'revenue_wo_vat',
    'total ht': 'revenue_wo_vat',
    'total ht confirmed': 'revenue_wo_vat',
    'prix conso ht': 'revenue_wo_vat',
    'montant ht energie (€)': 'revenue_wo_vat',
    'montant ht énergie (€)': 'revenue_wo_vat',
    'gireve billing value': 'revenue_wo_vat',
    'gireve billing value2': 'revenue_wo_vat',
    
    # Durée (minutes ou secondes)
    'duration_minutes': 'duration_minutes',
    'duration': 'duration_minutes',
    'durée': 'duration_minutes',
    'duree': 'duration_minutes',
    'duration(min)': 'duration_minutes',
    'duration (min)': 'duration_minutes',
    'duration (minutes)': 'duration_minutes',
    'duration(minutes)': 'duration_minutes',
    'duration(min)': 'duration_minutes',
    'duration (seconds)': 'duration_seconds',
    'charge duration (seconds)': 'duration_seconds',
    'duree (s)': 'duration_seconds',
    'duree(s)': 'duration_seconds',
    'temps total (s)': 'duration_seconds',
    'temps_total_s': 'duration_seconds',
    
    # Nom du chargeur / ID EVSE
    'charger_name': 'charger_name',
    'charger': 'charger_name',
    'chargepoint': 'charger_name',
    'charge_point': 'charger_name',
    'evseid': 'charger_name',
    'evse_id': 'charger_name',
    'evse id': 'charger_name',
    'station id (ocpi)': 'charger_name',
    'borne': 'charger_name',
    'nom borne': 'charger_name',
    'station name': 'charger_name',
    'station_name': 'charger_name',
    'externalidpdc': 'charger_name',
    'chargepointid': 'charger_name',
    'chargepointname': 'charger_name',
    'evse_idtype': 'charger_name',
    'evse_groupsnames': 'charger_name',
    'station key': 'charger_name',
    'station_key': 'charger_name',
    
    # CPO
    'cpo_id': 'cpo_id',
    'cpo_name': 'cpo_name',
    'cpo id': 'cpo_id',
    'cpo name': 'cpo_name',
}

def guess_column(df: pd.DataFrame, target: str) -> str | None:
    """Devine quelle colonne correspond à un objectif donné (ex: start_date_time, revenue_wo_vat)."""
    clean_cols = {}
    for col in df.columns:
        col_clean = str(col).strip().lower().replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('ë', 'e').replace('à', 'a').replace('ù', 'u')
        clean_cols[col_clean] = col

    # 1. Recherche par mappage strict connu d'abord (100% fiable)
    for col_clean, original_col in clean_cols.items():
        if col_clean in COLUMN_MAPPING:
            mapped_target = COLUMN_MAPPING[col_clean]
            if mapped_target == target:
                return original_col
            elif target == 'energy_consumption' and mapped_target == 'energy_consumption_wh':
                return original_col
            elif target == 'duration_minutes' and mapped_target == 'duration_seconds':
                return original_col

    # 2. Recherche sémantique par mots-clés en dernier recours (avec critères de sécurité)
    if target == 'start_date_time':
        candidates = []
        for col_clean, original_col in clean_cols.items():
            if any(k in col_clean for k in ['debut', 'start', 'beginning', 'created', 'from']):
                if not any(k in col_clean for k in ['fin', 'end', 'to']):
                    candidates.append(original_col)
        if candidates:
            return candidates[0]
            
    elif target == 'end_date':
        candidates = []
        for col_clean, original_col in clean_cols.items():
            if any(k in col_clean for k in ['fin', 'end', 'to']):
                if not any(k in col_clean for k in ['debut', 'start', 'beginning', 'from', 'created']):
                    candidates.append(original_col)
        if candidates:
            return candidates[0]

    elif target == 'energy_consumption':
        candidates = []
        for col_clean, original_col in clean_cols.items():
            if any(k in col_clean for k in ['energy', 'energie', 'kwh', 'wh', 'volume', 'conso']):
                # Éviter les colonnes de coûts énergétiques
                if not any(k in col_clean for k in ['cost', 'prix', 'price', 'tarif', 'montant', 'eur', 'currency']):
                    candidates.append(original_col)
        if candidates:
            return candidates[0]

    elif target == 'duration_minutes':
        candidates = []
        for col_clean, original_col in clean_cols.items():
            if any(k in col_clean for k in ['duration', 'duree', 'temps']):
                if not any(k in col_clean for k in ['cost', 'prix', 'price', 'tarif', 'montant', 'eur', 'currency']):
                    candidates.append(original_col)
        if candidates:
            return candidates[0]

    elif target == 'revenue_wo_vat':
        # Priorité aux colonnes contenant explicitement 'ht' ou 'ex vat'
        for col_clean, original_col in clean_cols.items():
            if any(k in col_clean for k in ['ht', 'ex vat', 'ex_vat']):
                if not 'ttc' in col_clean:
                    return original_col
        # Repli sur les termes généraux
        candidates = []
        for col_clean, original_col in clean_cols.items():
            if any(k in col_clean for k in ['montant', 'prix', 'price', 'cost', 'revenue', 'amount', 'billing', 'valeur']):
                if not any(k in col_clean for k in ['ttc', 'vat', 'tva']):
                    candidates.append(original_col)
        if candidates:
            return candidates[0]

    elif target == 'charger_name':
        candidates = []
        for col_clean, original_col in clean_cols.items():
            if any(k in col_clean for k in ['evse', 'charger', 'chargepoint', 'station', 'borne', 'pdc']):
                if not any(k in col_clean for k in ['cpo', 'emsp', 'user', 'price', 'group', 'type']):
                    candidates.append(original_col)
        if candidates:
            return candidates[0]

    return None

def bulk_reconcile(df_cto: pd.DataFrame, roaming_id_col: str, cpo_folder_path: str) -> pd.DataFrame:
    """
    Croise la liste CTO avec tous les fichiers CPO en utilisant le Roaming Session ID (ID CDR).
    
    Cherche l'ID dans l'intégralité des fichiers CPO (toutes colonnes confondues).
    """
    
    # 1. Extraction de la liste des Roaming Session IDs
    roaming_ids = set(df_cto[roaming_id_col].apply(clean_id).tolist())
    
    # Supprimer les valeurs vides ou "nan"
    roaming_ids.discard('nan')
    roaming_ids.discard('')
    
    all_anomalies = []

    # 2. Lister tous les fichiers (récursif dans tous les sous-dossiers)
    if not os.path.isdir(cpo_folder_path):
        raise ValueError(f"Le chemin spécifié n'est pas un dossier valide : {cpo_folder_path}")
        
    fichiers_cpo_paths = []
    for root, dirs, files in os.walk(cpo_folder_path):
        for file in files:
            if file.lower().endswith(('.csv', '.xlsx', '.xls')) and not file.startswith('~$'):
                fichiers_cpo_paths.append(os.path.join(root, file))
    
    if not fichiers_cpo_paths:
        raise ValueError("Aucun fichier CSV ou Excel trouvé dans ce dossier ou ses sous-dossiers.")

    # 3. Boucle sur tous les fichiers CPO
    for full_path in fichiers_cpo_paths:
        file_name = os.path.relpath(full_path, cpo_folder_path)
        try:
            df_cpo = load_data(full_path)
            
            # Détecter les colonnes candidates de manière hybride
            start_date_col = guess_column(df_cpo, 'start_date_time')
            end_date_col = guess_column(df_cpo, 'end_date')
            duration_col = guess_column(df_cpo, 'duration_minutes')
            energy_col = guess_column(df_cpo, 'energy_consumption')
            price_col = guess_column(df_cpo, 'revenue_wo_vat')
            charger_col = guess_column(df_cpo, 'charger_name')
            
            # Convertir tout en texte nettoyé pour la recherche (vectorisé pour plus de rapidité)
            df_cpo_str = df_cpo.astype(str).apply(lambda col: col.str.strip().str.replace(r'\.0$', '', regex=True))
            
            # Chercher les IDs
            mask_total = df_cpo_str.isin(roaming_ids).any(axis=1)
            
            anomalies_in_file = df_cpo[mask_total].copy()
            
            if not anomalies_in_file.empty:
                # Retrouver quel ID exact a matché
                matched_ids = []
                for idx, row in df_cpo_str[mask_total].iterrows():
                    all_found = list(set([v for v in row.values if v in roaming_ids]))
                    matched_ids.append(', '.join(all_found) if all_found else 'N/A')
                
                # Déduire le CPO (depuis colonne spécifique ou nom du fichier)
                cpo_value = None
                cpo_cols = ['cpo_id', 'cpo', 'cpo_name', 'operator', 'emsp_name']
                for col in df_cpo.columns:
                    col_clean = str(col).strip().lower().replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('ë', 'e').replace('à', 'a').replace('ù', 'u')
                    if col_clean in cpo_cols or any(k in col_clean for k in ['cpo id', 'cpo name', 'nom cpo', 'cpo_id', 'cpo_name']):
                        cpo_value = anomalies_in_file[col].iloc[0] if not anomalies_in_file[col].empty else None
                        break
                if not cpo_value or pd.isna(cpo_value):
                    base_file = os.path.basename(file_name)
                    cpo_value = os.path.splitext(base_file)[0]
                
                # Créer le dictionnaire standardisé pour cette anomalie
                for idx, row in anomalies_in_file.iterrows():
                    row_idx_local = anomalies_in_file.index.get_loc(idx)
                    row_id_matched = matched_ids[row_idx_local]
                    
                    start_date = row.get(start_date_col, None) if start_date_col else None
                    end_date = row.get(end_date_col, None) if end_date_col else None
                    charger = row.get(charger_col, None) if charger_col else None
                    
                    # Extraction et conversion de la durée (secondes en minutes si nécessaire)
                    duration = None
                    if duration_col:
                        val = row.get(duration_col, None)
                        if val is not None and not pd.isna(val):
                            try:
                                col_clean = str(duration_col).lower()
                                is_seconds = 'second' in col_clean or '(s)' in col_clean or ' s)' in col_clean
                                for k, v in COLUMN_MAPPING.items():
                                    if k in col_clean and v == 'duration_seconds':
                                        is_seconds = True
                                val_clean = str(val).replace(',', '.')
                                duration = float(val_clean) / 60.0 if is_seconds else float(val_clean)
                            except Exception:
                                pass
                    
                    # Calcul de repli si la durée n'est pas fournie mais que les dates début/fin existent
                    if (duration is None or pd.isna(duration)) and start_date and end_date:
                        try:
                            t_start = pd.to_datetime(start_date, utc=True, errors='coerce')
                            t_end = pd.to_datetime(end_date, utc=True, errors='coerce')
                            if not pd.isna(t_start) and not pd.isna(t_end):
                                diff = t_end - t_start
                                duration = diff.total_seconds() / 60.0
                        except Exception:
                            pass
                    
                    # Extraction et conversion de l'énergie (Wh en kWh si nécessaire)
                    energy = None
                    if energy_col:
                        val = row.get(energy_col, None)
                        if val is not None and not pd.isna(val):
                            try:
                                col_clean = str(energy_col).lower()
                                is_wh = 'wh' in col_clean and 'kwh' not in col_clean
                                for k, v in COLUMN_MAPPING.items():
                                    if k in col_clean and v == 'energy_consumption_wh':
                                        is_wh = True
                                val_clean = str(val).replace(',', '.')
                                energy = float(val_clean) / 1000.0 if is_wh else float(val_clean)
                            except Exception:
                                pass
                            
                    # Extraction et conversion du prix
                    price = None
                    if price_col:
                        val = row.get(price_col, None)
                        if val is not None and not pd.isna(val):
                            try:
                                price = float(str(val).replace(',', '.'))
                            except Exception:
                                pass
                    
                    anomalie_unifiee = {
                        'ID_Retrouvé': row_id_matched,
                        'Fichier_Source': file_name,
                        'CPO': cpo_value,
                        'Borne_EVSE': charger if not pd.isna(charger) else None,
                        'Date_Début': start_date if not pd.isna(start_date) else None,
                        'Date_Fin': end_date if not pd.isna(end_date) else None,
                        'Durée_Minutes': duration if not pd.isna(duration) else None,
                        'Énergie_kWh': energy if not pd.isna(energy) else None,
                        'Montant_HT': price if not pd.isna(price) else None
                    }
                    all_anomalies.append(anomalie_unifiee)
                
        except Exception as e:
            print(f"Erreur lors de la lecture de {file_name} : {e}")
            continue

    # 4. Consolidation et sélection des colonnes utiles
    if all_anomalies:
        df_result = pd.DataFrame(all_anomalies)
        
        # Sécurité pour PyArrow (convertit les objets et nettoie les NaNs)
        for col in df_result.columns:
            if col in ['Énergie_kWh', 'Montant_HT', 'Durée_Minutes']:
                df_result[col] = pd.to_numeric(df_result[col], errors='coerce')
            else:
                try:
                    df_result[col] = df_result[col].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if hasattr(x, 'strftime') else x)
                except Exception:
                    pass
                df_result[col] = df_result[col].fillna('').astype(str).replace(['nan', 'None', '<NA>'], '')
        
        # L'ordre exact souhaité par l'utilisateur
        colonnes_ordonnees = [
            'ID_Retrouvé', 'Fichier_Source', 'CPO', 'Borne_EVSE',
            'Date_Début', 'Date_Fin', 'Durée_Minutes', 'Énergie_kWh', 'Montant_HT'
        ]
        return df_result[colonnes_ordonnees]
    else:
        return pd.DataFrame()

def generate_excel_report(df_anomalies: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_anomalies.to_excel(writer, index=False, sheet_name='Anomalies')
    return output.getvalue()

def ask_gemini_about_df(df: pd.DataFrame, question: str, api_key: str) -> str:
    """Interroge l'API Gemini pour analyser le DataFrame des anomalies et répondre en langage naturel."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Convertir le DataFrame en CSV pour le passer dans le prompt
        df_csv = df.to_csv(index=False)
        
        prompt = f"""
Tu es un expert en analyse de données. Voici un tableau (format CSV) contenant les anomalies détectées lors de la réconciliation des sessions de recharge :

```csv
{df_csv}
```

Réponds à la question suivante de l'utilisateur de manière concise, précise et professionnelle en français.
Si la question nécessite un calcul (comme une somme, une moyenne ou un comptage), effectue ce calcul avec rigueur à partir des données fournies.

Question : "{question}"
"""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erreur lors de la communication avec Gemini : {e}"
