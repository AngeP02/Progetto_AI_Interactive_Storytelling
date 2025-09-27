from flask import Flask, render_template, request, session, redirect, url_for
import ollama
import json

app = Flask(__name__)
# Usare una chiave robusta in produzione, ma va bene per il debug
app.secret_key = "questmaster_secret"

OLLAMA_CLIENT = ollama.Client(host="http://localhost:11434")
MODEL_NAME = "llama3:latest"

# --- SYSTEM INSTRUCTION in Italiano ---
SYSTEM_INSTRUCTION = (
    "Sei QuestMaster, un Game Master interattivo di storie. "
    "DEVI rispondere SOLO con un singolo oggetto JSON valido (nessun testo extra all'esterno del JSON) "
    "e DEVI rispondere in ITALIANO. Il JSON DEVE avere esattamente questa forma:\n"
    '{\n'
    '  "message": "Testo in italiano da mostrare all\'utente",\n'
    '  "options": ["Opzione 1", "Opzione 2", ...]\n'
    '}\n'
    "Se non ci sono opzioni, restituisci una lista vuota per 'options'. Non usare recinti di codice. Sii conciso."
)


def extract_json_from_text(text):
    """
    Rende il parsing JSON più robusto ignorando i dati di log/evaluazione di Ollama
    che precedono l'oggetto JSON.
    """
    if not text:
        return None

    # 1. Trova l'inizio del JSON (la prima parentesi graffa aperta)
    start = text.find('{')
    if start == -1:
        return None

    # Inizia l'analisi da quel punto
    text_cleaned = text[start:].strip()

    # 2. Tenta l'analisi diretta del testo rimanente
    try:
        return json.loads(text_cleaned)
    except Exception:
        pass

    # 3. Scansiona per trovare l'oggetto {...} bilanciato (il tuo codice originale, migliorato)
    depth = 0
    # Resetta la ricerca sul testo pulito
    for i in range(len(text_cleaned)):
        ch = text_cleaned[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                # Abbiamo trovato l'oggetto bilanciato
                candidate = text_cleaned[:i + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    # In caso di errore di parsing (es. JSON malformato),
                    # possiamo continuare a cercare se il JSON non era il primo blocco
                    # Tuttavia, con Ollama che di solito mette un solo JSON, è meglio fallire qui.
                    return None  # Fallimento

    return None  # Nessun JSON valido trovato


# NOTA: Assicurati che le funzioni 'safe_json' e 'build_prompt'
# utilizzino la nuova 'extract_json_from_text' e che la 'SYSTEM_INSTRUCTION'
# sia ancora in Italiano e che forzi la risposta JSON.


def safe_json(text):
    # ... (il resto della funzione safe_json) ...
    # Questa funzione deve essere robusta:

    data = extract_json_from_text(text)
    if isinstance(data, dict) and "message" in data:
        message = str(data.get("message", "")).strip()
        options = data.get("options", [])
        if not isinstance(options, list): options = []
        return {"message": message, "options": options}

    # Fallback
    return {"message": text.strip(), "options": []}


# --- LOGICA DI STATO DEL CHATBOT ---
@app.route("/", methods=["GET", "POST"])
def chatbot():
    # Inizializzazione della sessione
    if "history" not in session or "state" not in session:
        session["history"] = []
        # Stato iniziale: Scelta Manuale/Casuale
        session["state"] = "INIT_CHOICE"

        initial_prompt = (
                SYSTEM_INSTRUCTION +
                "\n\nInizia la sessione. Saluta l'utente e chiedi: Vuoi configurare l'avventura da solo (Manuale) "
                "o lasciare che QuestMaster scelga tutto (Casuale)? Rispondi con i pulsanti 'Manuale' e 'Casuale'."
        )
        try:
            response = OLLAMA_CLIENT.generate(model=MODEL_NAME, prompt=initial_prompt)
            model_text = response.get("response", "")
            data = safe_json(model_text)
        except Exception as e:
            data = {"message": f"Errore di connessione a Ollama: {e}. Riprova più tardi.", "options": []}
            session["state"] = "ERROR"

        session["history"].append({"role": "assistant", "message": data["message"], "options": data.get("options", [])})
        # Forza il salvataggio della sessione dopo la modifica iniziale
        session.modified = True

        # Gestione delle risposte dell'utente (POST)
    if request.method == "POST":
        user_message = request.form.get("user_message", "").strip()
        if not user_message:
            return redirect(url_for('chatbot'))

        # Se l'utente non sta inviando il form di configurazione completa
        if user_message != "CONFIG_SUBMITTED":
            session["history"].append({"role": "user", "message": user_message})

        # --- LOGICA DI TRANSIZIONE DELLO STATO ---

        # 1. Stato INIT_CHOICE: Gestione della prima scelta (Manuale/Casuale)
        if session["state"] == "INIT_CHOICE":
            if user_message == "Manuale":
                session["state"] = "CONFIG_GENRE"
                # Richiesta LLM per i generi dinamici
                genre_prompt = (
                        SYSTEM_INSTRUCTION +
                        "\n\nL'utente ha scelto Manuale. Genera un set di 4 opzioni per il Genere dell'avventura "
                        "(es. Fantasy Medievale, Sci-Fi, Noir Culinario). Non generare opzioni per il Tono o Lunghezza ora. "
                        "Includi anche 'Altro...' come opzione per l'input libero. "
                        "Rispondi con un messaggio che invita alla scelta del genere."
                )
                try:
                    response = OLLAMA_CLIENT.generate(model=MODEL_NAME, prompt=genre_prompt)
                    data = safe_json(response.get("response", ""))

                    # Salva le opzioni LLM per l'uso nel template HTML
                    session['llm_genres'] = data.get('options', ['Fantasy', 'Sci-Fi', 'Thriller'])

                    # Messaggio di benvenuto al modulo di configurazione
                    assistant_message = (
                        "Ottimo! Ora possiamo procedere con la configurazione. "
                        "Usa il modulo sottostante per definire la tua avventura."
                    )
                    session["history"].append({"role": "assistant", "message": assistant_message, "options": []})

                    # Passa allo stato in cui viene visualizzato il form completo
                    session["state"] = "CONFIG_FORM"

                except Exception as e:
                    assistant_message = f"Errore nel generare i generi. Riprova. Errore: {e}"
                    session["history"].append(
                        {"role": "assistant", "message": assistant_message, "options": ["Riprova"]})
                    session["state"] = "INIT_CHOICE"  # Ritorna allo stato iniziale in caso di errore

            elif user_message == "Casuale":
                session["state"] = "CONFIG_RANDOM"

                # ... Logica per la modalità casuale (omessa qui per brevità, ma usa un prompt LLM specifico) ...

                # Messaggio di conferma e risultato Casual
                session["history"].append(
                    {"role": "assistant", "message": "QuestMaster ha scelto per te!", "options": []})
                # session["state"] = "ADVENTURE_READY"

            else:
                # Gestisce risposte non attese nello stato iniziale
                pass

        # 2. Stato CONFIG_FORM: L'utente invia il form completo (non gestito dai pulsanti chat)
        elif session["state"] == "CONFIG_FORM" and user_message == "CONFIG_SUBMITTED":

            # Recupera i dati dal form completo
            genre = request.form.get("genre", "Sconosciuto")
            length = request.form.get("length", "Media")
            theme = request.form.get("theme", "Nessuna trama fornita")
            graphics = request.form.get("graphics", "Non Illustrata")

            # Aggiorna la cronologia con il riepilogo dell'input dell'utente
            summary_message = (
                f"Configurazione completata: Genere: {genre}, Lunghezza: {length}, "
                f"Trama: '{theme}', Grafica: {graphics}."
            )
            session["history"].append({"role": "user", "message": summary_message})

            # Chiamata LLM per la generazione del PDDL (obiettivo finale)
            pddl_prompt = (
                    SYSTEM_INSTRUCTION +
                    f"\n\nObiettivo: Estrai la logica PDDL. Il Genere è '{genre}'. La Trama è: '{theme}'. "
                    "Devi estrarre e restituire i seguenti parametri logici essenziali: "
                    "1) LORE (Ambientazione e Personaggi principali), 2) OBIETTIVO LOGICO (L'azione finale che risolve la quest). "
                    "Rispondi SOLO con un JSON esteso, usando le chiavi 'lore' e 'objective'. Il 'message' deve riassumere l'estrazione in Italiano. "
                    "Esempio JSON: {'message': 'Ecco l'analisi logica...', 'lore': 'Una taverna in rovina...', 'objective': '(and (palla-salvata) (gatto-felice))'}."
            )

            try:
                response = OLLAMA_CLIENT.generate(model=MODEL_NAME, prompt=pddl_prompt)
                model_text = response.get("response", "")

                # Nota: qui avrai bisogno di un parser JSON più specifico per le chiavi 'lore' e 'objective'
                # o istruire l'LLM a includere i dati estratti nel 'message' se preferisci la semplicità.
                # Per ora usiamo safe_json e assumiamo l'LLM metta l'output nel 'message'.
                pddl_data = safe_json(model_text)

                session["history"].append({"role": "assistant", "message": pddl_data["message"], "options": []})
                session["state"] = "ADVENTURE_READY"

            except Exception as e:
                session["history"].append(
                    {"role": "assistant", "message": f"Errore LLM durante l'analisi PDDL: {e}", "options": []})
                session["state"] = "ERROR"

        # 3. Altri stati: (omessi)

        session.modified = True  # Salva le modifiche alla sessione

    # Renderizza il template con i dati aggiornati
    # Passiamo anche i generi dinamici al template per popolare la SELECT
    return render_template(
        "Frontend2.html",
        chat_history=session["history"],
        current_state=session["state"],
        llm_genres=session.get('llm_genres', [])  # Passa i generi generati
    )


if __name__ == "__main__":
    app.run(debug=True)