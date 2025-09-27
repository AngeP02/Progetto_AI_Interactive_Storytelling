from flask import Flask, render_template, request
import ollama
import json
import re

app = Flask(__name__)

OLLAMA_CLIENT = ollama.Client(host='http://localhost:11434')
MODEL_NAME = 'llama3'

# --- ROTTA PRINCIPALE (La prima pagina: il chatbot) ---
@app.route('/', methods=['GET', 'POST'])
def configure_chatbot():

    system_prompt = """Sei il 'QuestMaster' e devi guidare l'utente nella configurazione di una storia interattiva.
    Il tuo compito è suggerire 3 generi popolari e 2 insoliti.
    Rispondi SOLO con un oggetto JSON che contenga:
    - 'greeting': Un breve messaggio di benvenuto.
    - 'options': Una lista di 5 generi (3 popolari, 2 insoliti).
    """

    # 2. Chiamata all'LLM per generare i suggerimenti (Fase di Configurazione)
    try:
        response = OLLAMA_CLIENT.generate(
            model=MODEL_NAME,
            prompt=system_prompt,
            # Forza l'output in JSON per una facile parsing
            options={'format': 'json'}
        )

        # Pulizia dell'Output (Versione potenziata)
        raw_text = response['response'].strip()
        # Rimuove il Markdown (```json ... ```) se presente
        raw_text = raw_text.replace('```json', '').replace('```', '')

        match = re.search(r'\{.*\}', raw_text, re.DOTALL)  # Trova l'oggetto { ... }

        if match:
            json_string = match.group(0)
            data = json.loads(json_string)  # Tenta il caricamento
        else:
            # Se non trova l'oggetto JSON, solleva un errore
            raise ValueError("L'LLM non ha fornito una risposta JSON valida dopo la pulizia.")

        data = json.loads(response['response'])

        greeting_message = data.get('greeting', "Benvenuto in QuestMaster!")
        genre_options = data.get('options', [])

    except Exception as e:
        print(f"Errore di connessione a Ollama: {e}")
        greeting_message = "Errore: Impossibile connettersi al QuestMaster (Ollama non attivo?)."
        genre_options = ["Fantasy", "Sci-Fi", "Mistero"]

    return render_template('Frontend2.html',
                           message=greeting_message,
                           options=genre_options)


# --- Esecuzione del Server ---
if __name__ == '__main__':
    # Ricorda: devi avviare il server Ollama separatamente prima di lanciare questo file!
    app.run(debug=True)