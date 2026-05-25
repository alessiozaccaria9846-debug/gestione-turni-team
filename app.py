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

# --- CONFIGURAZIONE UTENTI E RUOLI ---
UTENTI = {
    "alessio": {"nome": "Alessio Z.", "ruolo": "Admin", "password": "adminpassword123"},
    "martina": {"nome": "Martina", "ruolo": "User", "password": "userpassword123"},
    "gaia": {"nome": "Gaia", "ruolo": "User", "password": "userpassword123"},
    "costanza": {"nome": "Costanza", "ruolo": "User", "password": "userpassword123"},
    "lorenzo": {"nome": "Lorenzo", "ruolo": "User", "password": "userpassword123"},
    "francesca": {"nome": "Francesca", "ruolo": "User", "password": "userpassword123"}
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
        "richieste": [],  # Lista di dizionari con le richieste di ferie/permessi/cambi
        "storico_approvazioni": [] # Registro storico
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

# --- LOGICA DI COSTRUZIONE DEL CALENDARIO ---
def genera_calendario_mensile(anno, mese):
    """Genera una matrice (DataFrame) per il mese e anno selezionati."""
    # Trova il primo e l'ultimo giorno del mese
    primo_giorno = datetime.date(anno, mese, 1)
    if mese == 12:
        ultimo_giorno = datetime.date(anno + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        ultimo_giorno = datetime.date(anno, mese + 1, 1) - datetime.timedelta(days=1)
    
    # Genera la lista di tutti i giorni del mese
    tot_giorni = (ultimo_giorno - primo_giorno).days + 1
    giorni = [primo_giorno + datetime.timedelta(days=i) for i in range(tot_giorni)]
    
    # Lista collaboratori (escluso l'Admin)
    collaboratori = [UTENTI[u]["nome"] for u in UTENTI if UTENTI[u]["ruolo"] == "User"]
    
    # Crea un DataFrame vuoto con i giorni come indici e i collaboratori come colonne
    df_calendario = pd.DataFrame("Presente", index=giorni, columns=collaboratori)
    
    # Imposta i weekend come "Chiuso"
    for giorno in giorni:
        if giorno.weekday() in [5, 6]: # 5 = Sabato, 6 = Domenica
            df_calendario.loc[giorno, :] = "Weekend (Chiuso)"
            
    # Applica le richieste approvate presenti nel database
    for req in st.session_state.db["richieste"]:
        if req["stato"] == "Approvata":
            req_inizio = datetime.datetime.strptime(req["data_inizio"], "%Y-%m-%d").date()
            req_fine = datetime.datetime.strptime(req["data_fine"], "%Y-%m-%d").date()
            tipo = req["tipo"]
            richiedente = UTENTI[req["utente"]]["nome"]
            
            # Scorri i giorni coperti dalla richiesta
            giorno_corr = req_inizio
            while giorno_corr <= req_fine:
                # Applica solo se il giorno rientra nel mese visualizzato e non è un weekend
                if giorno_corr in df_calendario.index:
                    if giorno_corr.weekday() not in [5, 6]: # Non sovrascrivere il weekend
                        df_calendario.at[giorno_corr, richiedente] = tipo
                giorno_corr += datetime.timedelta(days=1)
                
    return df_calendario

# --- STILIZZAZIONE VISIVA DELLA TABELLA ---
def colora_celle(val):
    """Applica i colori richiesti alle celle del calendario."""
    if val == "Presente":
        return "background-color: #d4edda; color: #155724; font-weight: 500;" # Verde chiaro
    elif val in ["Ferie", "Permesso", "Cambio Orario"]:
        return "background-color: #fff3cd; color: #856404; font-weight: bold;" # Arancione/Giallo chiaro
    elif val == "Weekend (Chiuso)":
        return "background-color: #343a40; color: #6c757d; font-style: italic;" # Grigio scuro con testo grigio chiaro
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
                if data_selezionata.weekday() not in [5, 6]: # Escludiamo i weekend dal conteggio di allerta critico
                    nome = UTENTI[req["utente"]]["nome"]
                    assenze.append(f"{nome} ({req['tipo']})")
    return assenze


# ==============================================================================
# SCHERMATA DI LOGIN
# ==============================================================================
if not st.session_state.autenticato:
    st.markdown("<h1 style='text-align: center; color: #007bff;'>📅 TeamShift Portal</h1>", unsafe_style=True)
    st.markdown("<p style='text-align: center; color: #6c757d;'>Piattaforma dinamica per il monitoraggio e la gestione dei turni del team</p>", unsafe_style=True)
    
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
                
    # Mostra credenziali di prova per facilitare il primo avvio
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
    tab_calendar, tab_richieste, tab_approvazioni = st.tabs([
        "📊 Calendario Team", 
        "➕ Nuova Richiesta Personale", 
        "📥 Richieste in Sospeso (Admin)"
    ])
else:
    tab_calendar, tab_richieste = st.tabs([
        "📊 Calendario Team", 
        "➕ Invia Richiesta"
    ])


# ------------------------------------------------------------------------------
# TAB 1: CALENDARIO TEAM (Visibile a tutti)
# ------------------------------------------------------------------------------
with tab_calendar:
    st.subheader("Tabella Riassuntiva Copertura Giornaliera")
    st.markdown("*I fine settimana (Sabato e Domenica) sono contrassegnati in grigio scuro.*")
    
    # Generazione e Formattazione del Calendario
    df_cal = genera_calendario_mensile(anno_selezionato, mese_selezionato_num)
    
    # Prepariamo la tabella per mostrare il giorno della settimana vicino alla data
    df_cal_visual = df_cal.copy()
    giorni_settimana = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    nuovi_indici = [f"{giorno.strftime('%d/%m/%Y')} ({giorni_settimana[giorno.weekday()]})" for giorno in df_cal_visual.index]
    df_cal_visual.index = nuovi_indici
    
    # Render della tabella stilizzata con i colori configurati
    st.dataframe(
        df_cal_visual.style.applymap(colora_cells),
        use_container_width=True,
        height=600
    )


# ------------------------------------------------------------------------------
# TAB 2: INSERIMENTO RICHIESTE (Per tutti i collaboratori e l'admin stesso)
# ------------------------------------------------------------------------------
with tab_richieste:
    st.subheader("Invia una nuova richiesta di assenza")
    
    with st.form("form_richiesta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_inizio = st.date_input("Data Inizio", datetime.date.today())
            data_fine = st.date_input("Data Fine (Inclusa)", datetime.date.today())
        with col2:
            tipo_assenza = st.selectbox("Tipo di Assenza", ["Ferie", "Permesso", "Cambio Orario"])
            note = st.text_input("Note / Motivazione (Opzionale)", placeholder="Es. Visita medica o viaggio")
            
        submit_btn = st.form_submit_button("Invia Richiesta", use_container_width=True)
        
        if submit_btn:
            if data_inizio > data_fine:
                st.error("Errore: La data d'inizio non può essere successiva alla data di fine.")
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
                    "stato": "In attesa", # Stati possibili: "In attesa", "Approvata", "Rifiutata"
                    "data_creazione": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                st.session_state.db["richieste"].append(nuova_req)
                salva_dati(st.session_state.db)
                st.success("Richiesta inviata correttamente e in attesa di approvazione dal Responsabile.")
                st.balloons()

    # Sezione "Le Mie Richieste" in fondo alla pagina per tracciare lo stato
    st.markdown("---")
    st.subheader("Le tue richieste inviate")
    mie_req = [r for r in st.session_state.db["richieste"] if r["utente"] == st.session_state.utente_loggato]
    
    if len(mie_req) > 0:
        df_mie_req = pd.DataFrame(mie_req)
        # Rendiamo le colonne più leggibili
        df_mie_req_view = df_mie_req[["tipo", "data_inizio", "data_fine", "note", "stato"]].copy()
        df_mie_req_view.columns = ["Tipo", "Da Data", "A Data", "Note", "Stato Approvazione"]
        st.dataframe(df_mie_req_view, use_container_width=True)
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
                
                inizio_date = datetime.datetime.strptime(inizio_str, "%Y-%m-%d").date()
                fine_date = datetime.datetime.strptime(fine_str, "%Y-%m-%d").date()
                
                # Visualizzazione dettagliata della singola richiesta in un box (expander)
                titolo_box = f"Richiesta {tipo} da parte di {nome_richiedente} (dal {inizio_str} al {fine_str})"
                
                with st.container(border=True):
                    col_det, col_azioni = st.columns([2, 1])
                    
                    with col_det:
                        st.markdown(f"### **{nome_richiedente}** richiede **{tipo}**")
                        st.markdown(f"📅 **Periodo:** dal *{inizio_str}* al *{fine_str}*")
                        if note_req:
                            st.markdown(f"📝 **Note:** *\"{note_req}\"*")
                            
                        # --- ANALISI DI COPERTURA CRITICA ---
                        # Controlliamo giorno per giorno nel periodo richiesto quante persone sono già assenti
                        giorno_temp = inizio_date
                        segnala_allarme = False
                        recap_assenze = []
                        
                        while giorno_temp <= fine_date:
                            # Controlliamo solo i giorni lavorativi
                            if giorno_temp.weekday() not in [5, 6]:
                                assenti = ottieni_assenze_giorno(giorno_temp)
                                # Escludiamo il richiedente stesso per evitare falsi positivi se avesse già vecchie richieste approvate sovrapposte
                                assenti = [a for a in assenti if not a.startswith(nome_richiedente)]
                                
                                count_assenti = len(assenti)
                                if count_assenti > 0:
                                    recap_assenze.append(f"Il **{giorno_temp.strftime('%d/%m')}** ci sono già {count_assenti} assenti: {', '.join(assenti)}")
                                if count_assenti >= 2: # Regola fondamentale: se ci sono già 2 o più persone assenti
                                    segnala_allarme = True
                            giorno_temp += datetime.timedelta(days=1)
                        
                        # Alert Visivo in caso di bassa copertura
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
                        # Creazione chiavi univoche basate sull'ID della richiesta per evitare conflitti di widget
                        btn_approva = st.button("✅ Approva", key=f"app_{req_id}", use_container_width=True, type="primary")
                        btn_rifiuta = st.button("❌ Rifiuta", key=f"rif_{req_id}", use_container_width=True)
                        
                        if btn_approva:
                            # Aggiorna lo stato nel database
                            for r in st.session_state.db["richieste"]:
                                if r["id"] == req_id:
                                    r["stato"] = "Approvata"
                            salva_dati(st.session_state.db)
                            st.toast(f"Richiesta di {nome_richiedente} approvata!")
                            st.rerun()
                            
                        if btn_rifiuta:
                            # Aggiorna lo stato nel database
                            for r in st.session_state.db["richieste"]:
                                if r["id"] == req_id:
                                    r["stato"] = "Rifiutata"
                            salva_dati(st.session_state.db)
                            st.toast(f"Richiesta di {nome_richiedente} rifiutata.", icon="❌")
                            st.rerun()
```
eof

---

### Guida Completa al Deploy: Da zero alla pubblicazione online

Per avere la tua web app pronta, funzionante e raggiungibile tramite link da parte del tuo team, segui questi passaggi dettagliati.

#### Fase 1: Testare l'applicazione in Locale
Prima di pubblicarla online, puoi provarla sul tuo computer.

1. **Apri il browser su Google** (come richiesto) e cerca "scaricare Python". Vai sul sito ufficiale di Python e installa l'ultima versione disponibile per il tuo sistema operativo. Assicurati di spuntare la casella **"Add Python to PATH"** durante l'installazione su Windows.
2. Apri il tuo Terminale (Prompt dei comandi su Windows o Terminale su macOS).
3. Installa Streamlit e Pandas eseguendo questo comando:
   ```bash
   pip install streamlit pandas
   ```
4. Crea una nuova cartella sul tuo computer (es. `teamshift`) e crea all'interno un file chiamato `app.py`.
5. Copia e incolla tutto il codice del riquadro soprastante all'interno del file `app.py` e salvalo.
6. Sempre dal terminale, spostati nella cartella contenente il file ed esegui l'applicazione:
   ```bash
   streamlit run app.py
   ```
7. Si aprirà automaticamente una pagina nel tuo browser all'indirizzo `http://localhost:8501` con la tua applicazione funzionante!

---

#### Fase 2: Configurazione di GitHub (Necessaria per la pubblicazione)
Streamlit Community Cloud legge i file direttamente da GitHub per pubblicare la tua app.

1. Vai su [github.com](https://github.com) e crea un account gratuito (se non ne hai già uno).
2. Crea un nuovo repository privato o pubblico cliccando su **"New"** (Nuovo Repository).
3. Chiamalo, ad esempio, `gestione-turni-team`.
4. Carica all'interno del repository i seguenti file:
   * **`app.py`**: Il file contenente il codice Python fornito sopra.
   * **`requirements.txt`**: Un file di testo che indica a Streamlit quali librerie installare. Crealo e scrivi all'interno semplicemente:
     ```text
     streamlit
     pandas
