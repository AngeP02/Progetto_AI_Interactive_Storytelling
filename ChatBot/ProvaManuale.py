from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests
import json
import random
import time
import logging

app = Flask(__name__)
CORS(app)

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestMasterLLM:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3"
        self.conversation_history = []

    def call_ollama(self, prompt, system_prompt=""):
        """Chiama Ollama con il prompt specificato"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 500
                }
            }

            response = requests.post(self.ollama_url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            return result.get('response', '').strip()

        except requests.exceptions.RequestException as e:
            logger.error(f"Errore chiamata Ollama: {e}")
            return "Mi dispiace, sto avendo problemi tecnici. Riprova tra un momento."
        except Exception as e:
            logger.error(f"Errore generico: {e}")
            return "Si è verificato un errore imprevisto."

    def generate_welcome_message(self):
        """Genera il messaggio di benvenuto usando Llama3"""
        system_prompt = """Sei l'assistente AI di QuestMaster, un sistema che crea storie interattive usando LLM e logica PDDL. 
Devi essere entusiasta, coinvolgente e professionale. Il tuo ruolo è guidare l'utente nella configurazione della sua avventura personalizzata."""

        prompt = """Genera un messaggio di benvenuto caloroso per QuestMaster, un sistema che crea avventure testuali interattive personalizzate. 
Spiega brevemente che puoi aiutare a creare storie uniche combinando creatività e logica, e chiedi se l'utente vuole:
1. Configurazione Manuale (scegliere ogni dettaglio)
2. Modalità Casuale (tu decidi tutto come Game Master)

Mantieni il tono entusiasta e professionale, max 150 parole."""

        return self.call_ollama(prompt, system_prompt)

    def generate_genres(self):
        """Genera una lista di generi dinamica usando Llama3"""
        system_prompt = """Sei un esperto di narrativa e gaming. Conosci tutti i generi letterari e videoludici."""

        prompt = """Genera una lista di 6 generi interessanti e vari per storie interattive. 
Includi sia generi classici che combinazioni creative moderne. 
Rispondi SOLO con una lista JSON nel formato: ["Genere 1", "Genere 2", ...]
Esempi: Fantasy Epico, Cyberpunk Noir, Horror Cosmico, Steampunk Investigativo, etc."""

        response = self.call_ollama(prompt, system_prompt)

        # Prova a estrarre JSON dalla risposta
        try:
            # Trova il JSON nella risposta
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                genres = json.loads(json_str)
                return genres
        except:
            pass

        # Fallback se non riesce a parsare il JSON
        return ["Fantasy Epico", "Fantascienza", "Horror Psicologico",
                "Cyberpunk", "Steampunk", "Post-Apocalittico"]

    def generate_tones(self):
        """Genera opzioni di tono usando Llama3"""
        system_prompt = """Sei un esperto di storytelling e conosci tutti i toni narrativi possibili."""

        prompt = """Genera 4 toni narrativi diversi per storie interattive.
Rispondi SOLO con una lista JSON: ["Tono 1", "Tono 2", "Tono 3", "Tono 4"]
Esempi: Epico e Solenne, Ironico e Satirico, Dark e Misterioso, etc."""

        response = self.call_ollama(prompt, system_prompt)

        try:
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                tones = json.loads(json_str)
                return tones
        except:
            pass

        return ["Epico e Solenne", "Ironico e Satirico", "Dark e Misterioso", "Leggero e Avventuroso"]

    def process_custom_genre(self, custom_genre):
        """Elabora e commenta un genere personalizzato"""
        system_prompt = """Sei un critico letterario esperto che apprezza la creatività nei generi narrativi."""

        prompt = f"""L'utente ha scelto il genere personalizzato: "{custom_genre}"
Scrivi un breve commento positivo e incoraggiante su questa scelta (max 50 parole).
Spiega brevemente perché è interessante o che possibilità narrative offre."""

        return self.call_ollama(prompt, system_prompt)

    def generate_random_config(self):
        """Genera una configurazione completamente casuale usando Llama3"""
        system_prompt = """Sei un Game Master creativo che ama sorprendere i giocatori con configurazioni uniche e interessanti."""

        prompt = """Genera una configurazione CASUALE per un'avventura interattiva. Restituisci SOLO un JSON con questa struttura:
{
  "genre": "un genere creativo",
  "length": "una tra: Corta (15-30 min), Media (45-60 min), Lunga (90+ min)",
  "tone": "un tono narrativo interessante", 
  "graphics": "una tra: Illustrata, Solo Testo",
  "theme": "una trama originale e coinvolgente di massimo 100 caratteri"
}

Sii creativo e sorprendente!"""

        response = self.call_ollama(prompt, system_prompt)

        try:
            # Trova il JSON nella risposta
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                config = json.loads(json_str)
                return config
        except Exception as e:
            logger.error(f"Errore parsing config casuale: {e}")
            pass

        # Fallback
        return {
            "genre": "Fantasy Steampunk",
            "length": "Media (45-60 min)",
            "tone": "Avventuroso e Ironico",
            "graphics": "Illustrata",
            "theme": "Un inventore deve salvare la città con le sue macchine magiche"
        }

    def generate_contextual_response(self, user_input, context):
        """Genera risposte contestuali per ogni fase della configurazione"""
        system_prompt = f"""Sei l'assistente di QuestMaster. Contesto attuale: {context}
Mantieni un tono professionale ma entusiasta. Risposte brevi e dirette."""

        context_prompts = {
            "genre_explanation": """L'utente ha scelto il genere. Spiega brevemente cosa succede ora 
            (selezione della lunghezza) e come la lunghezza influenza la complessità PDDL. Max 80 parole.""",

            "length_explanation": """L'utente ha scelto la lunghezza. Spiega ora la scelta del tono 
            narrativo e come influenza l'atmosfera della storia. Max 60 parole.""",

            "tone_explanation": """L'utente ha scelto il tono. Chiedi ora sulla modalità grafica 
            (illustrata vs solo testo) spiegando brevemente la differenza. Max 60 parole.""",

            "graphics_explanation": """L'utente ha scelto la modalità grafica. Ora chiedi di descrivere 
            il tema/trama della storia. Dai esempi brevi e incoraggia la creatività. Max 80 parole.""",

            "manual_mode_start": """L'utente ha scelto modalità manuale. Introduci la scelta del genere 
            e spiega che può scegliere tra opzioni generate o inserire un genere personalizzato. Max 60 parole.""",

            "random_mode_intro": """L'utente ha scelto modalità casuale. Descrivi cosa stai per fare 
            (generare tutto casualmente) con entusiasmo da Game Master. Max 50 parole."""
        }

        prompt = context_prompts.get(context, f"Rispondi all'utente nel contesto: {context}")
        return self.call_ollama(prompt, system_prompt)


# Istanza globale del LLM
llm = QuestMasterLLM()
user_sessions = {}  # Gestione sessioni utenti (semplificata)


@app.route('/')
def index():
    """Serve il frontend HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>QuestMaster - Reindirizza al Frontend</title>
    </head>
    <body>
        <h1>QuestMaster Backend Attivo</h1>
        <p>Il backend è in esecuzione. Apri <strong>frontend.html</strong> per utilizzare l'applicazione.</p>
        <p>API endpoint disponibili:</p>
        <ul>
            <li>POST /api/welcome - Messaggio di benvenuto</li>
            <li>POST /api/chat - Chat con l'assistente</li>
            <li>POST /api/generate_options - Genera opzioni dinamiche</li>
        </ul>
    </body>
    </html>
    """


@app.route('/api/welcome', methods=['POST'])
def welcome():
    """Endpoint per il messaggio di benvenuto"""
    try:
        message = llm.generate_welcome_message()
        return jsonify({
            'success': True,
            'message': message,
            'options': ['Configurazione Manuale', 'Modalità Casuale']
        })
    except Exception as e:
        logger.error(f"Errore welcome: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint principale per la chat"""
    try:
        data = request.json
        user_choice = data.get('message', '')
        session_id = data.get('session_id', 'default')
        current_step = data.get('step', 'welcome')

        # Inizializza sessione se non esiste
        if session_id not in user_sessions:
            user_sessions[session_id] = {
                'config': {},
                'conversation_history': []
            }

        session = user_sessions[session_id]
        response_data = {'success': True}

        # Gestisci i diversi step della conversazione
        if current_step == 'welcome':
            if user_choice == 'Modalità Casuale':
                # Genera intro casuale
                intro_msg = llm.generate_contextual_response(user_choice, "random_mode_intro")
                config = llm.generate_random_config()
                session['config'] = config

                config_msg = f"""🎪 Ecco la tua Quest generata casualmente:

**📚 Genere:** {config['genre']}
**⏱️ Lunghezza:** {config['length']}  
**🎭 Tono:** {config['tone']}
**🎨 Grafica:** {config['graphics']}
**📖 Tema:** {config['theme']}

Sei pronto a iniziare la tua quest?"""

                response_data.update({
                    'message': intro_msg + "\n\n" + config_msg,
                    'options': ['Inizia la Quest!', 'Rigenera Configurazione'],
                    'next_step': 'final_confirmation'
                })

            elif user_choice == 'Configurazione Manuale':
                genres = llm.generate_genres()
                message = llm.generate_contextual_response(user_choice, "manual_mode_start")

                response_data.update({
                    'message': message + "\n\nScegli tra questi generi:",
                    'options': genres + ['Genere Personalizzato'],
                    'next_step': 'genre_selection'
                })

        elif current_step == 'genre_selection':
            if user_choice == 'Genere Personalizzato':
                response_data.update({
                    'message': "✏️ Inserisci il genere personalizzato che desideri per la tua avventura:",
                    'show_text_input': True,
                    'text_placeholder': 'Scrivi il tuo genere personalizzato...',
                    'next_step': 'custom_genre'
                })
            else:
                session['config']['genre'] = user_choice
                message = llm.generate_contextual_response(user_choice, "genre_explanation")

                response_data.update({
                    'message': message,
                    'options': ['Corta (15-30 min)', 'Media (45-60 min)', 'Lunga (90+ min)'],
                    'next_step': 'length_selection'
                })

        elif current_step == 'custom_genre':
            session['config']['genre'] = user_choice
            comment = llm.process_custom_genre(user_choice)
            message = llm.generate_contextual_response(user_choice, "genre_explanation")

            response_data.update({
                'message': f"🎨 Eccellente! \"{user_choice}\" - {comment}\n\n{message}",
                'options': ['Corta (15-30 min)', 'Media (45-60 min)', 'Lunga (90+ min)'],
                'next_step': 'length_selection'
            })

        elif current_step == 'length_selection':
            session['config']['length'] = user_choice
            tones = llm.generate_tones()
            message = llm.generate_contextual_response(user_choice, "tone_explanation")

            response_data.update({
                'message': message,
                'options': tones,
                'next_step': 'tone_selection'
            })

        elif current_step == 'tone_selection':
            session['config']['tone'] = user_choice
            message = llm.generate_contextual_response(user_choice, "graphics_explanation")

            response_data.update({
                'message': message,
                'options': ['Illustrata', 'Solo Testo'],
                'next_step': 'graphics_selection'
            })

        elif current_step == 'graphics_selection':
            session['config']['graphics'] = user_choice
            message = llm.generate_contextual_response(user_choice, "graphics_explanation")

            response_data.update({
                'message': message,
                'show_text_input': True,
                'text_placeholder': 'Descrivi la trama della tua avventura...',
                'next_step': 'theme_input'
            })

        elif current_step == 'theme_input':
            session['config']['theme'] = user_choice
            config = session['config']

            final_message = f"""🎉 Configurazione completata con successo!

**La tua Quest personalizzata:**

**📚 Genere:** {config['genre']}
**⏱️ Lunghezza:** {config['length']}
**🎭 Tono:** {config['tone']}
**🎨 Modalità:** {config['graphics']}
**📖 Tema:** {user_choice}

Il sistema PDDL analizzerà questi parametri per creare una struttura logica coerente, mentre l'LLM genererà la narrativa coinvolgente. Sei pronto per iniziare?"""

            response_data.update({
                'message': final_message,
                'options': ['Inizia la Quest!', 'Modifica Configurazione'],
                'next_step': 'final_confirmation'
            })

        elif current_step == 'final_confirmation':
            if user_choice == 'Rigenera Configurazione' or user_choice == 'Modifica Configurazione':
                # Reset e riavvio
                session['config'] = {}
                welcome_msg = llm.generate_welcome_message()
                response_data.update({
                    'message': welcome_msg,
                    'options': ['Configurazione Manuale', 'Modalità Casuale'],
                    'next_step': 'welcome'
                })
            else:
                response_data.update({
                    'message': "🚀 Quest avviata! (Qui si integrerebbe il sistema PDDL e la generazione della storia)",
                    'options': [],
                    'quest_ready': True,
                    'config': session['config']
                })

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Errore chat: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/health', methods=['GET'])
def health():
    """Endpoint per verificare lo stato del server"""
    try:
        # Test connessione Ollama
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_status = "online" if test_response.status_code == 200 else "offline"
    except:
        ollama_status = "offline"

    return jsonify({
        'status': 'running',
        'ollama': ollama_status,
        'model': llm.model
    })


if __name__ == '__main__':
    print("🎮 Avvio QuestMaster Backend...")
    print("📋 Assicurati che Ollama sia in esecuzione: ollama serve")
    print("🤖 Modello richiesto: llama3")
    print("🌐 Apri frontend.html nel browser per usare l'applicazione")

    app.run(host='0.0.0.0', port=5000, debug=True)