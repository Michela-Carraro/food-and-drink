import streamlit as st
import pandas as pd
import numpy as np

# Configurazione della pagina
st.set_page_config(
    page_title="The Fresh Connection Lite - Simulation",
    page_icon="🍊",
    layout="wide"
)

# Titolo principale e descrizione del corso
st.title("🍊 The Fresh Connection Lite")
st.subheader("Master in Food and Drink Retailing and Logistics - Simulazione di Supply Chain")
st.markdown("""
Benvenuti nella simulazione interattiva di ottimizzazione logistica per **JuiceCo**, azienda produttrice di succhi d'arancia freschi premium.
Il vostro obiettivo come Team di Direzione Logistica è massimizzare il **Profitto Netto** e minimizzare lo **Spreco Alimentare**, 
trovando il perfetto bilanciamento tra costi di trasporto, vincoli biologici della catena del freddo e penali contrattuali della GDO.
""")

st.divider()

# Struttura a colonne: Sinistra per gli Input (Decisioni), Destra per gli Output (Risultati)
col_input, col_output = st.columns([1, 2])

with col_input:
    st.header("🛠️ Decisioni Strategiche")
    st.markdown("Modificate i parametri logistici per il prossimo round operativo:")
    
    # 1. Dimensione del lotto
    batch_size = st.slider(
        "Dimensione del Lotto di Spedizione (Bottiglie)",
        min_value=500,
        max_value=10000,
        value=2000,
        step=500,
        help="Lotti grandi riducono il costo unitario di trasporto ma aumentano i tempi di sosta in magazzino."
    )
    
    # 2. Frequenza di consegna
    frequency_options = {
        "Giornaliera": 1,
        "Bisettimanale (2 volte a settimana)": 3,
        "Settimanale": 7
    }
    frequency_label = st.selectbox(
        "Frequenza di Consegna al Ce.Di. della GDO",
        options=list(frequency_options.keys()),
        index=1,
        help="Consegne frequenti garantiscono freschezza ma aumentano drasticamente i costi fissi di viaggio."
    )
    days_between_deliveries = frequency_options[frequency_label]
    
    # 3. Qualità della Catena del Freddo
    cold_chain_level = st.radio(
        "Investimento nella Catena del Freddo (IoT & Mezzi)",
        options=["Standard (Basso Investimento)", "Premium (Alto Investimento - Sensori e Refrigerazione Costante)"],
        index=0,
        help="Il livello Premium protegge l'orologio biologico del succo, riducendo la velocità di degradazione qualitativa durante il transito."
    )
    
    # 4. Scorta di Sicurezza
    safety_stock_days = st.slider(
        "Scorta di Sicurezza in Magazzino (Giorni di Copertura)",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="Più giorni di scorta proteggono dagli stockout dovuti alla variabilità della domanda, ma aumentano il rischio di scadenza del prodotto."
    )

# --- MOTORE MATEMATICO DELLA SIMULAZIONE (Logiche di Backend) ---

# Parametri fissi di mercato
DOMANDA_POTENZIALE_SETTIMANALE = 10000
PREZZO_VENDITA_SCAFFALE = 5.00
PREZZO_CESSIONE_INGROSSO = 3.50
COSTO_PRODUZIONE_UNITARIO = 2.00
SHELF_LIFE_TOTALE_GIORNI = 24
SOGLIA_CONTRATTUALE_RSL = 70.0 # Carrefour rifiuta sotto il 70%

# Calcolo Giorni in Transito e Degradazione
giorni_transito_base = 2 if days_between_deliveries == 1 else (4 if days_between_deliveries == 3 else 7)
if batch_size > 5000:
    giorni_transito_base += 1 # Rallentamenti per consolidamento lotti pesanti

# Impatto Catena del Freddo sulla degradazione accelerata
moltiplicatore_degrado = 1.0 if cold_chain_level.startswith("Premium") else 1.3
giorni_vita_persi_in_transito = giorni_transito_base * moltiplicatore_degrado

# Calcolo Shelf-Life Residua Reale (RSL %) all'arrivo
giorni_residui_all_arrivo = SHELF_LIFE_TOTALE_GIORNI - giorni_vita_persi_in_transito - safety_stock_days
rsl_percentuale = (giorni_residui_all_arrivo / SHELF_LIFE_TOTALE_GIORNI) * 100
rsl_percentuale = max(0.0, min(100.0, rsl_percentuale))

# Calcolo Rifiuti e Spreco Alimentare (Food Waste %)
saturazione_scaffale_rischio = (batch_size / 2000) * (days_between_deliveries / 2)
food_waste_percent = 2.0 + (safety_stock_days * 3.5) + (saturazione_scaffale_rischio * 1.5)
if rsl_percentuale < SOGLIA_CONTRATTUALE_RSL:
    food_waste_percent += 40.0 # Penalità massiccia se la merce arriva al limite della soglia GDO
food_waste_percent = max(0.0, min(100.0, food_waste_percent))

# Calcolo Out-of-Stock (OOS %)
oos_percent = 15.0 - (safety_stock_days * 3.0) + (days_between_deliveries * 2.0)
if batch_size < 1000 and days_between_deliveries > 3:
    oos_percent += 25.0 # Sotto-scorta critico
oos_percent = max(0.0, min(100.0, oos_percent))

# --- BILANCIO FINANZIARIO ECONOMICO ---
unita_richieste = DOMANDA_POTENZIALE_SETTIMANALE
unita_perse_oos = unita_richieste * (oos_percent / 100)
unita_consegnate_potenziali = unita_richieste - unita_perse_oos

unita_scadute_waste = unita_consegnate_potenziali * (food_waste_percent / 100)
unita_vendute_sane = unita_consegnate_potenziali - unita_scadute_waste

# Voci di Costo
costo_produzione_totale = unita_consegnate_potenziali * COSTO_PRODUZIONE_UNITARIO

# Costi di trasporto influenzati dalle decisioni
costo_viaggio_base = 300 if days_between_deliveries == 1 else (600 if days_between_deliveries == 3 else 1200)
if cold_chain_level.startswith("Premium"):
    costo_viaggio_base *= 1.4 # Sovrapprezzo per mezzi refrigerati avanzati ed energia
numero_viaggi_settimana = 7 / days_between_deliveries
costo_trasporto_totale = costo_viaggio_base * numero_viaggi_settimana

costo_stoccaggio_scorte = safety_stock_days * 250
costo_penali_contract = unita_scadute_waste * PREZZO_CESSIONE_INGROSSO # Rimborso al retailer per merce buttata

# Ricavi e Profitto Netto
ricavi_totali = unita_vendute_sane * PREZZO_CESSIONE_INGROSSO
profitto_netto = ricavi_totali - costo_produzione_totale - costo_trasporto_totale - costo_stoccaggio_scorte - costo_penali_contract

# Calcolo Carbon Footprint (CO2) indicativo
co2_trasporto = (numero_viaggi_settimana * 120) / (batch_size / 2000)
co2_refrigerazione = 450 if cold_chain_level.startswith("Premium") else 200
co2_totale_kg = co2_trasporto + co2_refrigerazione + (unita_scadute_waste * 0.1)

# --- VISUALIZZAZIONE RISULTATI (Dashboard) ---
with col_output:
    st.header("📊 Performance Dashboard (Risultati Settimanali)")
    
    # Riga dei KPI principali
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(
        label="Profitto Netto", 
        value=f"€ {profitto_netto:,.2f}",
        delta=f"Margine unitario reale: € {((profitto_netto/unita_vendute_sane) if unita_vendute_sane > 0 else 0):.2f}",
        delta_color="normal" if profitto_netto > 0 else "inverse"
    )
    kpi2.metric(
        label="Spreco Alimentare (Food Waste)", 
        value=f"{food_waste_percent:.1f} %",
        delta="CRITICO" if food_waste_percent > 20 else "Accettabile",
        delta_color="inverse" if food_waste_percent > 20 else "normal"
    )
    kpi3.metric(
        label="Shelf-Life Residua (RSL)", 
        value=f"{rsl_percentuale:.1f} %",
        delta="Rifiuto GDO (<70%)" if rsl_percentuale < SOGLIA_CONTRATTUALE_RSL else "Conforme",
        delta_color="normal" if rsl_percentuale >= SOGLIA_CONTRATTUALE_RSL else "inverse"
    )
    kpi4.metric(
        label="Fuori Stock (OOS)", 
        value=f"{oos_percent:.1f} %",
        delta="Scaffale vuoto" if oos_percent > 10 else "Ottimale",
        delta_color="inverse" if oos_percent > 10 else "normal"
    )
    
    st.divider()
    
    # Grafici dei costi e analisi dei trade-off
    st.subheader("📉 Struttura dei Costi e Sostenibilità")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("**Analisi dei Costi Operativi Sostenuti (€)**")
        costi_data = {
            "Voce di Costo": ["Produzione Base", "Trasporto Refrigerato", "Mantenimento Scorte", "Penali Merce Scaduta / Rifiutata"],
            "Valore (€)": [float(costo_produzione_totale), float(costo_trasporto_totale), float(costo_stoccaggio_scorte), float(costo_penali_contract)]
        }
        df_costi = pd.DataFrame(costi_data)
        st.bar_chart(data=df_costi, x="Voce di Costo", y="Valore (€)", use_container_width=True)
        
    with col_chart2:
        st.markdown("**Impronta Ecologica della Strategia**")
        st.metric(label="Emissioni Totali di CO₂ equivalenti", value=f"{co2_totale_kg:.1f} kg CO₂e")
        st.progress(min(1.0, max(0.0, co2_totale_kg / 3000.0)), text="Saturazione capacità ecologica di filiera")
        
    st.divider()
    
    # Note di Analisi e Feedback del Docente Automatico
    st.subheader("🧠 Report di Consulenza Logistica (Feedback per gli studenti)")
    if rsl_percentuale < SOGLIA_CONTRATTUALE_RSL:
        st.error(f"🚨 **Rifiuto del Carico al Ce.Di.:** La vostra Shelf-Life Residua ({rsl_percentuale:.1f}%) è scesa sotto la soglia contrattuale del {SOGLIA_CONTRATTUALE_RSL}%. La GDO ha respinto la merce applicando le penali. Dovete ridurre i giorni di sosta delle scorte o investire nella Catena del Freddo Premium per rallentare il degrado biologico!")
    elif oos_percent > 12.0:
        st.warning(f"⚠️ **Scaffali Vuoti nei Punti Vendita:** Avete un tasso di Out-of-Stock molto elevato ({oos_percent:.1f}%). State perdendo quote di mercato e profitti preziosi perché la scorta di sicurezza è troppo bassa o le consegne sono troppo infrequenti per rispondere alla domanda.")
    elif food_waste_percent > 15.0:
        st.warning(f"🪰 **Eccesso di Spreco Alimentare:** State buttando via troppi succhi d'arancia a causa di lotti di spedizione eccessivi o troppi giorni di immobilizzazione delle merci. Ricordate che nel Food, lo stock che non gira scade e distrugge il margine netti.")
    else:
        st.success("💎 **Ottimo Bilanciamento Operativo!** Siete riusciti a mantenere la conformità contrattuale con la GDO, contenere lo spreco e proteggere lo scaffale dai fuori stock. Siete pronti per presentare questa configurazione!")
