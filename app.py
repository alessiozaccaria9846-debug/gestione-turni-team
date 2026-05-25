import streamlit as st
import pandas as pd
import datetime
import json
import os

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="TeamShift - Gestione Turni & Ferie",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZZATO PER COMPATTARE IL LAYOUT E PREVENIRE LO SCROLL ---
st.markdown("""
    <style>
        /* Riduciamo a zero i margini superiori e inferiori di Streamlit */
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        /* Riduciamo lo spazio sopra e sotto il titolo principale */
        h1 {
            margin-top: -1.5rem !important;
            margin-bottom: 0.2rem !important;
            font-size: 1.8rem !important;
            font-weight: 700 !important;
        }
        /* Rendiamo i Tabs più compatti */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 35px;
            padding-top: 2px;
            padding-bottom: 2px;
            font-size: 0.9rem !important;
        }
        /* Riduzione padding dei widget e scritte in sidebar */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURAZIONE UTENTI E RUOLI ---
UTENTI = {
    "alessio": {"nome": "Alessio Z.", "ruolo": "Admin", "password": "adminpassword123"},
    "martina": {"nome": "Martina", "ruolo": "User", "password": "userpassword123"},
    "gaia": {"nome": "Gaia", "ruolo": "User", "password": "userpassword123"},
    "costanza": {"nome": "Costanza", "ruolo": "User", "password": "userpassword123"},
    "lorenzo": {"nome": "Lorenzo", "ruolo": "User", "password": "userpassword123"},
    "francesca": {"nome": "Francesca", "ruolo": "User", "password": "userpassword123"}
}

# --- DEFINIZIONE TURNI STANDARD (Lunedì - Giovedì) ---
ORARI_BASE_SETTIMANALI = {
    "Alessio Z.": {0: "9-18", 1: "9-18", 2: "9-18", 3: "9-18"},
    "Martina":    {0: "9-18", 1: "9-18", 2: "8-17", 3: "8-17"},
    "Gaia":       {0: "8-17", 1: "9-18", 2: "9-18", 3: "8-17"},
    "Costanza":   {0: "8-17", 1: "8-17", 2: "9-18", 3: "8-17"},
    "Lorenzo":    {0: "9-18", 1: "8-17", 2: "8-17", 3: "9-18"},
    "Francesca":  {0: "9-18", 1: "9-18", 2: "9-18", 3: "9-18"}
}

DB_FILE = "turni_data.json"

# --- FUNZIONI DI GESTIONE DATABASE (JSON) ---
def carica_dati():
    """Carica i dati dal file JSON locale o inizializza un database vuoto."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Struttura dati iniziale vuota
    return {
        "richieste": [],  # Lista di richieste di ferie/permessi/cambi
        "storico_approvazioni": []
    }

def salva_dati(data):
    """Salva lo stato corrente dei dati nel file JSON locale."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Inizializzazione dei dati nella sessione di Streamlit
if "db" not in st.session_state:
    st.session_state.db = carica_dati()

# --- GESTIONE DELLO STATO DI AUTENTICAZIONE ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
    st.session_state.utente_loggato = None
    st.session_state.ruolo_utente = None
    st.session_state.nome_completo = None

def login(username, password):
    username_clean = username.lower().strip()
    if username_clean in UTENTI and UTENTI[username_clean]["password"] == password:
        st.session_state.autenticato = True
        st.session_state.utente_loggato = username_clean
        st.session_state.ruolo_utente = UTENTI[username_clean]["ruolo"]
        st.session_state.nome_completo = UTENTI[username_clean]["nome"]
        st.success(f"Benvenuto {st.session_state.nome_completo}!")
        st.rerun()
    else:
        st.error("Username o Password non corretti.")

def logout():
    st.session_state.autenticato = False
    st.session_state.utente_loggato = None
    st.session_state.ruolo_utente = None
    st.session_state.nome_completo = None
    st.rerun()

# --- LOGICA CALCOLO VENERDÌ ALTERNATO ---
def calcola_turno_venerdi(nome_utente, data_giorno):
    """
    Ritorna il turno del venerdì per l'utente in base alla data.
    Data di riferimento: Venerdì 29/05/2026.
    In quel giorno: Martina e Costanza fanno 8-17. Gaia e Lorenzo fanno 9-18. Francesca fa 9-18.
    """
    if data_giorno.weekday() != 4:
        return None
    
    if nome_utente == "Alessio Z.":
        return "9-18"
    if nome_utente == "Francesca":
        return "9-18"
        
    # Venerdì di riferimento
    ref_date = datetime.date(2026, 5, 29)
    # Calcoliamo la differenza in settimane
    delta_days = (data_giorno - ref_date).days
    delta_weeks = delta_days // 7
    
    is_pari = (delta_weeks % 2 == 0)
    
    if nome_utente in ["Martina", "Costanza"]:
        return "8-17" if is_pari else "9-18"
    elif nome_utente in ["Gaia", "Lorenzo"]:
        return "9-18" if is_pari else "8-17"
        
    return "9-18"

# --- DETERMINAZIONE ORARIO DEL GIORNO ---
def ottieni_orario_teorico(nome_utente, data_giorno):
    """Ritorna l'orario base teorico senza considerare le ferie."""
    wd = data_giorno.weekday()
    if wd in [5, 6]:
        return "Weekend (Chiuso)"
    
    # Se è venerdì, applichiamo la logica di alternanza
    if wd == 4:
        return calcola_turno_venerdi(nome_utente, data_giorno)
        
    # Altrimenti prendiamo l'orario standard
    return ORARI_BASE_SETTIMANALI.get(nome_utente, {}).get(wd, "Presente")

# --- UTILITY: CONTEGGIO GIORNI LAVORATIVI (ESCLUSI WEEKEND) ---
def calcola_giorni_lavorativi(inizio_date, fine_date):
    """Ritorna il numero di giorni lavorativi compresi tra due date (estremi inclusi)."""
    giorni_lavorativi = 0
    giorno_temp = inizio_date
    while giorno_temp <= fine_date:
        if giorno_temp.weekday() not in [5, 6]:
            giorni_lavorativi += 1
        giorno_temp += datetime.timedelta(days=1)
    return giorni_lavorativi

# --- LOGICA DI COSTRUZIONE DEL CALENDARIO MENSILE ---
def genera_calendario_mensile(anno, mese):
    """Genera una matrice (DataFrame) per il mese e anno selezionati con gli orari reali."""
    primo_giorno = datetime.date(anno, mese, 1)
    if mese == 12:
        ultimo_giorno = datetime.date(anno + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        ultimo_giorno = datetime.date(anno, mese + 1, 1) - datetime.timedelta(days=1)
    
    tot_giorni = (ultimo_giorno - primo_giorno).days + 1
    giorni = [primo_giorno + datetime.timedelta(days=i) for i in range(tot_giorni)]
    
    collaboratori = [UTENTI[u]["nome"] for u in UTENTI]
    
    # Popoliamo il dataframe partendo dagli orari teorici reali di ciascuno
    df_calendario = pd.DataFrame(index=giorni, columns=collaboratori)
    for col in collaboratori:
        for giorno in giorni:
            df_calendario.at[giorno, col] = ottieni_orario_teorico(col, giorno)
            
    # Sovrascriviamo gli orari con le richieste approvate presenti nel database (Ferie, Permessi, etc.)
    for req in st.session_state.db["richieste"]:
        if req["stato"] == "Approvata":
            req_inizio = datetime.datetime.strptime(req["data_inizio"], "%Y-%m-%d").date()
            req_fine = datetime.datetime.strptime(req["data_fine"], "%Y-%m-%d").date()
            tipo = req["tipo"]
            richiedente = UTENTI[req["utente"]]["nome"]
            
            giorno_corr = req_inizio
            while giorno_corr <= req_fine:
                if giorno_corr in df_calendario.index:
                    if giorno_corr.weekday() not in [5, 6]: # Non sovrascrivere il weekend
                        # Se è un permesso parziale, mostriamo comunque l'indicazione di permesso
                        df_calendario.at[giorno_corr, richiedente] = tipo
                giorno_corr += datetime.timedelta(days=1)
                
    return df_calendario

# --- STILIZZAZIONE VISIVA DELLA TABELLA (Colori dello Screenshot) ---
def colora_celle(val):
    """Applica i colori richiesti alle celle del calendario basandosi sullo screenshot."""
    if val == "9-18":
        return "background-color: #ccf2cb; color: #1b5e20; font-weight: 600; font-size: 0.85rem;" # Verde (Screenshot)
    elif val == "8-17":
        return "background-color: #eed7f2; color: #4a148c; font-weight: 600; font-size: 0.85rem;" # Viola (Screenshot)
    elif val == "Flexy":
        return "background-color: #cce3f5; color: #0d47a1; font-weight: 600; font-size: 0.85rem;" # Azzurro (Screenshot)
    elif val in ["Ferie", "Permesso", "Cambio Orario"]:
        return "background-color: #ffcc80; color: #e65100; font-weight: bold; font-size: 0.85rem; border-left: 4px solid #ff9100;" # Arancione (Assenza)
    elif val == "Weekend (Chiuso)":
        return "background-color: #343a40; color: #858d96; font-style: italic; font-size: 0.8rem;" # Grigio scuro
    return ""

# --- CONTEGGIO ASSENZE GIORNALIERE (ALERT DI COPERTURA) ---
def ottieni_assenze_giorno(data_selezionata):
    """Calcola quante persone sono assenti in una specifica data."""
    assenze = []
    for req in st.session_state.db["richieste"]:
        if req["stato"] == "Approvata":
            req_inizio = datetime.datetime.strptime(req["data_inizio"], "%Y-%m-%d").date()
            req_fine = datetime.datetime.strptime(req["data_fine"], "%Y-%m-%d").date()
            
            if req_inizio <= data_selezionata <= req_fine:
                if data_selezionata.weekday() not in [5, 6]:
                    nome = UTENTI[req["utente"]]["nome"]
                    assenze.append(f"{nome} ({req['tipo']})")
    return assenze


# ==============================================================================
# SCHERMATA DI LOGIN
# ==============================================================================
if not st.session_state.autenticato:
    st.markdown("<h1 style='text-align: center; color: #007bff;'>📅 TeamShift Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6c757d; font-size: 0.9rem; margin-top: -10px;'>Piattaforma dinamica per il monitoraggio e la gestione dei turni del team</p>", unsafe_allow_html=True)
    
    col_login, _ = st.columns([1, 1])
    with col_login:
        st.subheader("Accedi al portale")
        username_input = st.text_input("Username (Nome in minuscolo, es: alessio, martina)").lower().strip()
        password_input = st.text_input("Password", type="password")
        
        if st.button("Accedi", use_container_width=True):
            if username_input and password_input:
                login(username_input, password_input)
            else:
                st.warning("Per favore, compila tutti i campi.")
                
    st.info("""
    💡 **Credenziali di Test per questa demo:**
    - **Admin:** `alessio` / `adminpassword123`
    - **Collaboratori:** `martina`, `gaia`, `costanza`, `lorenzo`, `francesca` / `userpassword123`
    """)
    st.stop()


# ==============================================================================
# APP PRINCIPALE (DOPO IL LOGIN)
# ==============================================================================

# Sidebar - Profilo e Navigazione
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.nome_completo}")
    st.markdown(f"**Ruolo:** `{st.session_state.ruolo_utente}`")
    st.markdown("---")
    
    # Selettore del Periodo da visualizzare
    st.subheader("Filtro Calendario")
    oggi = datetime.date.today()
    anno_selezionato = st.selectbox("Anno", [oggi.year - 1, oggi.year, oggi.year + 1], index=1)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_selezionato_nome = st.selectbox("Mese", mesi_ita, index=oggi.month - 1)
    mese_selezionato_num = mesi_ita.index(mese_selezionato_nome) + 1
    
    st.markdown("---")
    if st.button("Esci (Logout)", type="secondary", use_container_width=True):
        logout()

# Intestazione App
st.title(f"📅 Gestione Presenze & Turni - {mese_selezionato_nome} {anno_selezionato}")

# Creazione delle schede dell'applicazione (Tabs)
if st.session_state.ruolo_utente == "Admin":
    tab_calendar, tab_richieste, tab_approvazioni, tab_statistiche = st.tabs([
        "📊 Calendario Team",
        "➕ Nuova Richiesta Personale", 
        "📥 Richieste in Sospeso (Admin)",
        "📈 Statistiche Team (Admin)"
    ])
else:
    tab_calendar, tab_richieste = st.tabs([
        "📊 Calendario Team", 
        "➕ Invia Richiesta"
    ])


# ------------------------------------------------------------------------------
# TAB 1: CALENDARIO TEAM (Interattivo con Click di Ritiro Diretto)
# ------------------------------------------------------------------------------
with tab_calendar:
    # Generazione e Formattazione del Calendario
    df_cal = genera_calendario_mensile(anno_selezionato, mese_selezionato_num)
    
    # Prepariamo la tabella per mostrare il giorno della settimana vicino alla data
    df_cal_visual = df_cal.copy()
    giorni_settimana = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sat", "Dom"]
    nuovi_indici = [f"{giorno.strftime('%d/%m/%Y')} ({giorni_settimana[giorno.weekday()]})" for giorno in df_cal_visual.index]
    df_cal_visual.index = nuovi_indici
    
    # Rendiamo il calendario interattivo permettendo la selezione di singole celle
    st.markdown("*Puoi ritirare un giorno di Ferie o Permesso approvato cliccando direttamente sulla cella corrispondente alla tua colonna.*")
    event = st.dataframe(
        df_cal_visual.style.map(colora_celle),
        use_container_width=True,
        height=480,
        on_select="rerun",
        selection_mode="single_cell"
    )

    # Gestione del Click sulla cella del calendario
    cells = []
    if event is not None:
        if isinstance(event, dict) and "selection" in event:
            cells = event["selection"].get("cells", [])
        elif hasattr(event, "selection") and hasattr(event.selection, "cells"):
            cells = event.selection.cells

    if cells:
        cell = cells[0]
        row_idx = cell.get("row")
        col_idx = cell.get("column")
        
        if row_idx is not None and col_idx is not None:
            giorno_selezionato = df_cal.index[row_idx]
            nome_collaboratore = df_cal.columns[col_idx]
            valore_cella = df_cal.iloc[row_idx, col_idx]
            
            # Controlliamo se la cella selezionata corrisponde all'utente loggato
            if nome_collaboratore == st.session_state.nome_completo:
                if valore_cella in ["Ferie", "Permesso"]:
                    st.markdown("---")
                    col_alert, col_action = st.columns([3, 1])
                    with col_alert:
                        st.warning(f"⚠️ Hai selezionato il giorno **{giorno_selezionato.strftime('%d/%m/%Y')}** contrassegnato come **{valore_cella}**.")
                    with col_action:
                        # Ritiro immediato senza necessità di approvazione Admin
                        if st.button(f"🗑️ Vuoi rimuovere il giorno di {valore_cella.lower()}?", use_container_width=True, type="primary"):
                            data_str = giorno_selezionato.strftime("%Y-%m-%d")
                            
                            # Filtriamo e rimuoviamo la richiesta che copre questo giorno specifico
                            vecchie_richieste = st.session_state.db["richieste"]
                            nuove_richieste = []
                            ritrovato = False
                            
                            for r in vecchie_richieste:
                                if r["utente"] == st.session_state.utente_loggato and r["data_inizio"] <= data_str <= r["data_fine"]:
                                    ritrovato = True
                                    # Se è una richiesta singola o l'inizio coincide con la fine, la rimuoviamo del tutto.
                                    # Altrimenti, se copre più giorni, possiamo rimuoverla per semplificazione (oppure dividere il range).
                                    # Rimuoviamo la richiesta intera come comportamento standard di annullamento.
                                    continue
                                nuove_richieste.append(r)
                            
                            if ritrovato:
                                st.session_state.db["richieste"] = nuove_richieste
                                salva_dati(st.session_state.db)
                                st.success("Richiesta rimossa con successo!")
                                st.rerun()
                            else:
                                st.error("Nessuna richiesta attiva trovata per questo specifico giorno.")
            else:
                # Informazione se clicca sulla colonna di un altro collaboratore
                st.info(f"ℹ️ Hai selezionato il turno di **{nome_collaboratore}** per il giorno {giorno_selezionato.strftime('%d/%m/%Y')}: **{valore_cella}**.")


# ------------------------------------------------------------------------------
# TAB 2: INSERIMENTO E RITIRO RICHIESTE (Dinamico e Reattivo)
# ------------------------------------------------------------------------------
with tab_richieste:
    col_ins, col_rit = st.columns(2)
    
    with col_ins:
        st.subheader("➕ Nuova Richiesta Personale")
        tipo_assenza = st.selectbox("Tipo di Assenza", ["Ferie", "Permesso"])
        
        # Inizializziamo i campi per l'inserimento
        if tipo_assenza == "Permesso":
            data_permesso = st.date_input("Data Permesso", datetime.date.today())
            data_inizio = data_permesso
            data_fine = data_permesso
            
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                ora_inizio = st.time_input("Ora Inizio", datetime.time(9, 0))
            with col_h2:
                ora_fine = st.time_input("Ora Fine", datetime.time(13, 0))
                
            dt_inizio = datetime.datetime.combine(datetime.date.today(), ora_inizio)
            dt_fine = datetime.datetime.combine(datetime.date.today(), ora_fine)
            
            if dt_fine > dt_inizio:
                ore_calcolate_permesso = (dt_fine - dt_inizio).seconds / 3600.0
                st.info(f"⏱️ Durata calcolata: **{ore_calcolate_permesso:.1f} ore**")
            else:
                ore_calcolate_permesso = 0
                st.error("L'orario di fine deve essere successivo all'orario di inizio!")
        else:
            data_inizio = st.date_input("Data Inizio", datetime.date.today())
            data_fine = st.date_input("Data Fine (Inclusa)", datetime.date.today())
            ore_calcolate_permesso = 0
            
        note = st.text_input("Note / Motivazione (Opzionale)", placeholder="Es. Visita medica o viaggio")
        invio_selezionato = st.button("Invia Richiesta", use_container_width=True, type="primary")

        if invio_selezionato:
            if data_inizio > data_fine:
                st.error("Errore: La data d'inizio non può essere successiva alla data di fine.")
            elif tipo_assenza == "Permesso" and ore_calcolate_permesso <= 0:
                st.error("Errore: Verifica l'orario inserito. Le ore di permesso devono essere maggiori di 0.")
            else:
                # Creazione nuovo record richiesta
                nuova_req = {
                    "id": len(st.session_state.db["richieste"]) + 1,
                    "utente": st.session_state.utente_loggato,
                    "nome_completo": st.session_state.nome_completo,
                    "data_inizio": data_inizio.strftime("%Y-%m-%d"),
                    "data_fine": data_fine.strftime("%Y-%m-%d"),
                    "tipo": tipo_assenza,
                    "note": note,
                    "ora_inizio": ora_inizio.strftime("%H:%M") if tipo_assenza == "Permesso" else "",
                    "ora_fine": ora_fine.strftime("%H:%M") if tipo_assenza == "Permesso" else "",
                    "ore_permesso": round(ore_calcolate_permesso, 2) if tipo_assenza == "Permesso" else 0,
                    "stato": "In attesa",
                    "data_creazione": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                st.session_state.db["richieste"].append(nuova_req)
                salva_dati(st.session_state.db)
                st.success("Richiesta inviata correttamente e in attesa di approvazione!")
                st.balloons()
                st.rerun()

    # --- SEZIONE PER IL RITIRO DIRETTO DELLE RICHIESTE ---
    with col_rit:
        st.subheader("🔄 Gestione e Ritiro Richieste Attive")
        st.write("Puoi rimuovere o annullare immediatamente qualsiasi tua richiesta in sospeso o già approvata:")
        
        mie_attive = [r for r in st.session_state.db["richieste"] if r["utente"] == st.session_state.utente_loggato and r["stato"] in ["In attesa", "Approvata"]]
        
        if len(mie_attive) > 0:
            opzioni_ritiro = {}
            for r in mie_attive:
                dettaglio = f"{r['tipo']} (dal {r['data_inizio']} al {r['data_fine']}) - [{r['stato']}]"
                opzioni_ritiro[dettaglio] = r["id"]
                
            richiesta_da_ritirare = st.selectbox("Seleziona quale richiesta vuoi annullare:", list(opzioni_ritiro.keys()))
            
            if st.button("🗑️ Ritira Richiesta Selezionata", use_container_width=True):
                id_da_cancellare = opzioni_ritiro[richiesta_da_ritirare]
                # Aggiorna il database filtrando via la richiesta eliminata
                st.session_state.db["richieste"] = [r for r in st.session_state.db["richieste"] if r["id"] != id_da_cancellare]
                salva_dati(st.session_state.db)
                st.success("Richiesta ritirata con successo e rimossa dal calendario!")
                st.rerun()
        else:
            st.info("Non hai richieste attive o approvate al momento da poter ritirare.")

    st.markdown("---")
    st.subheader("Le tue richieste storiche")
    mie_req = [r for r in st.session_state.db["richieste"] if r["utente"] == st.session_state.utente_loggato]
    
    if len(mie_req) > 0:
        df_mie_req = pd.DataFrame(mie_req)
        if "ore_permesso" not in df_mie_req.columns:
            df_mie_req["ore_permesso"] = 0
        if "ora_inizio" not in df_mie_req.columns:
            df_mie_req["ora_inizio"] = ""
        if "ora_fine" not in df_mie_req.columns:
            df_mie_req["ora_fine"] = ""
            
        df_mie_req_view = df_mie_req.copy()
        
        dettaglio_orario = []
        for idx, row in df_mie_req_view.iterrows():
            if row["tipo"] == "Permesso" and row["ora_inizio"] != "":
                dettaglio_orario.append(f"{row['ora_inizio']} - {row['ora_fine']} ({row['ore_permesso']} ore)")
            elif row["tipo"] == "Permesso":
                dettaglio_orario.append(f"{row['ore_permesso']} ore")
            else:
                dettaglio_orario.append("-")
                
        df_mie_req_view["Orario/Ore"] = dettaglio_orario
        df_mie_req_view_table = df_mie_req_view[["tipo", "data_inizio", "data_fine", "Orario/Ore", "note", "stato"]].copy()
        df_mie_req_view_table.columns = ["Tipo", "Da Data", "A Data", "Dettaglio Permesso", "Note", "Stato Approvazione"]
        st.dataframe(df_mie_req_view_table, use_container_width=True)
    else:
        st.info("Non hai ancora inserito nessuna richiesta.")


# ------------------------------------------------------------------------------
# TAB 3: APPROVAZIONI & ANALISI VISIVA COPERTURA (Solo Admin)
# ------------------------------------------------------------------------------
if st.session_state.ruolo_utente == "Admin":
    with tab_approvazioni:
        st.subheader("Richieste Ricevute da Approvare")
        
        richieste_pendenti = [r for r in st.session_state.db["richieste"] if r["stato"] == "In attesa"]
        
        if len(richieste_pendenti) == 0:
            st.success("🎉 Non ci sono richieste in sospeso al momento!")
        else:
            for req in richieste_pendenti:
                req_id = req["id"]
                utente_req = req["utente"]
                nome_richiedente = req["nome_completo"]
                tipo = req["tipo"]
                inizio_str = req["data_inizio"]
                fine_str = req["data_fine"]
                note_req = req["note"]
                ore_p = req.get("ore_permesso", 0)
                ora_in = req.get("ora_inizio", "")
                ora_fi = req.get("ora_fine", "")
                
                inizio_date = datetime.datetime.strptime(inizio_str, "%Y-%m-%d").date()
                fine_date = datetime.datetime.strptime(fine_str, "%Y-%m-%d").date()
                
                with st.container(border=True):
                    col_det, col_azioni = st.columns([2, 1])
                    
                    with col_det:
                        if tipo == "Permesso" and ora_in != "":
                            dettagli_tipo = f"{tipo} dalle ore {ora_in} alle ore {ora_fi} ({ore_p} ore totali)"
                        else:
                            dettagli_tipo = tipo
                            
                        st.markdown(f"### **{nome_richiedente}** richiede **{dettagli_tipo}**")
                        st.markdown(f"📅 **Data:** *{inizio_str}*" if inizio_str == fine_str else f"📅 **Periodo:** dal *{inizio_str}* al *{fine_str}*")
                        if note_req:
                            st.markdown(f"📝 **Note:** *\"{note_req}\"*")
                            
                        # --- ANALISI DI COPERTURA CRITICA ---
                        giorno_temp = inizio_date
                        segnala_allarme = False
                        recap_assenze = []
                        
                        while giorno_temp <= fine_date:
                            if giorno_temp.weekday() not in [5, 6]:
                                assenti = ottieni_assenze_giorno(giorno_temp)
                                assenti = [a for a in assenti if not a.startswith(nome_richiedente)]
                                
                                count_assenti = len(assenti)
                                if count_assenti > 0:
                                    recap_assenze.append(f"Il **{giorno_temp.strftime('%d/%m')}** ci sono già {count_assenti} assenti: {', '.join(assenti)}")
                                if count_assenti >= 2:
                                    segnala_allarme = True
                            giorno_temp += datetime.timedelta(days=1)
                        
                        if segnala_allarme:
                            st.markdown(
                                """<div style='background-color:#f8d7da; border-left:6px solid #dc3545; padding:12px; border-radius:4px; margin-bottom:10px;'>
                                <strong style='color:#721c24;'>⚠️ ATTENZIONE: CRITICITÀ COPERTURA!</strong><br/>
                                <span style='color:#721c24;'>Se approvi questa richiesta, ci saranno giorni con 3 o più persone assenti contemporaneamente.</span>
                                </div>""", 
                                unsafe_style=True
                            )
                        elif len(recap_assenze) > 0:
                            st.warning(f"ℹ️ Presenze registrate in quel periodo:\n" + "\n".join([f"- {r}" for r in recap_assenze]))
                        else:
                            st.success("✅ Copertura ottimale: Nessun altro collaboratore è assente in queste date.")
                            
                    with col_azioni:
                        st.write(" ")
                        st.write(" ")
                        btn_approva = st.button("✅ Approva", key=f"app_{req_id}", use_container_width=True, type="primary")
                        btn_rifiuta = st.button("❌ Rifiuta", key=f"rif_{req_id}", use_container_width=True)
                        
                        if btn_approva:
                            for r in st.session_state.db["richieste"]:
                                if r["id"] == req_id:
                                    r["stato"] = "Approvata"
                            salva_dati(st.session_state.db)
                            st.toast(f"Richiesta di {nome_richiedente} approvata!")
                            st.rerun()
                            
                        if btn_rifiuta:
                            for r in st.session_state.db["richieste"]:
                                if r["id"] == req_id:
                                    r["stato"] = "Rifiutata"
                            salva_dati(st.session_state.db)
                            st.toast(f"Richiesta di {nome_richiedente} rifiutata.", icon="❌")
                            st.rerun()


# ------------------------------------------------------------------------------
# TAB 4: SEZIONE STATISTICHE ADMIN (Solo per Admin)
# ------------------------------------------------------------------------------
if st.session_state.ruolo_utente == "Admin":
    with tab_statistiche:
        st.subheader("📈 Riepilogo Assenze, Ferie & Permessi del Team")
        st.write("Statistiche dettagliate sul consumo di Ferie (espressi in Giorni Lavorativi) e Permessi (espressi in Ore) di ciascun collaboratore.")
        
        richieste_totali = st.session_state.db["richieste"]
        
        dati_statistiche = []
        for username_chiave, info_utente in UTENTI.items():
            nome_completo = info_utente["nome"]
            
            richieste_utente = [r for r in richieste_totali if r["utente"] == username_chiave]
            
            ferie_approvate = 0
            ferie_in_attesa = 0
            permessi_approvati_ore = 0
            permessi_in_attesa_ore = 0
            
            for req in richieste_utente:
                inizio = datetime.datetime.strptime(req["data_inizio"], "%Y-%m-%d").date()
                fine = datetime.datetime.strptime(req["data_fine"], "%Y-%m-%d").date()
                tipo = req["tipo"]
                stato = req["stato"]
                ore_p_singolo = req.get("ore_permesso", 0)
                
                giorni_lav = calcola_giorni_lavorativi(inizio, fine)
                
                if tipo == "Ferie":
                    if stato == "Approvata":
                        ferie_approvate += giorni_lav
                    elif stato == "In attesa":
                        ferie_in_attesa += giorni_lav
                elif tipo == "Permesso":
                    ore_calcolate = ore_p_singolo if ore_p_singolo > 0 else (giorni_lav * 8)
                    
                    if stato == "Approvata":
                        permessi_approvati_ore += ore_calcolate
                    elif stato == "In attesa":
                        permessi_in_attesa_ore += ore_calcolate
            
            dati_statistiche.append({
                "Collaboratore": nome_completo,
                "Ferie Approvate (Giorni)": ferie_approvate,
                "Ferie In Attesa (Giorni)": ferie_in_attesa,
                "Ferie Totali Richieste (Giorni)": ferie_approvate + ferie_in_attesa,
                "Permessi Approvati (Ore)": permessi_approvati_ore,
                "Permessi In Attesa (Ore)": permessi_in_attesa_ore,
                "Permessi Totali Richiesti (Ore)": permessi_approvati_ore + permessi_in_attesa_ore
            })
            
        df_stats = pd.DataFrame(dati_statistiche)
        st.dataframe(df_stats.set_index("Collaboratore"), use_container_width=True)
        
        st.markdown("### 📊 Analisi Grafica dei consumi assenze")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.write("**Confronto Ferie Richieste (Giorni lavorativi totali)**")
            df_ferie_chart = df_stats[["Collaboratore", "Ferie Approvate (Giorni)", "Ferie In Attesa (Giorni)"]].set_index("Collaboratore")
            st.bar_chart(df_ferie_chart, color=["#ccf2cb", "#ffcc80"])
            
        with col_chart2:
            st.write("**Confronto Ore di Permesso Richieste (Ore totali)**")
            df_perm_chart = df_stats[["Collaboratore", "Permessi Approvati (Ore)", "Permessi In Attesa (Ore)"]].set_index("Collaboratore")
            st.bar_chart(df_perm_chart, color=["#cce3f5", "#ffcc80"])
