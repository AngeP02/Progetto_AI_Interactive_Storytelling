import re
import os
import json
import logging
import webbrowser
from threading import Timer
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

from QuestMaster.Game import creategame, QuestPlan

# Carica variabili d'ambiente
load_dotenv()

# Import esistenti (Assicurati che questi file esistano o adattali se necessario)
try:
    from QuestMaster.Generate_PDDL.no_LLM_2 import generate_valid_pddl_guaranteed
    from QuestMaster.Lore.Lore2 import generate_lore_document
except ImportError:
    print("⚠️ ATTENZIONE: Moduli QuestMaster non trovati. Assicurati della struttura delle cartelle.")


    # Mock functions per evitare crash se mancano i file durante il test del chatbot
    def generate_valid_pddl_guaranteed(**kwargs):
        return (True, "PDDL Mock Generato")


    def generate_lore_document(config):
        return "path/to/mock_lore.md"

# Configurazione Path
BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"
OUTPUT_FOLDER = SCRIPT_DIR / "pddl_output"
# Modifica il path se necessario
FAST_DOWNWARD = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"
HUMAN_LOOP_FILE = BASE_DIR / "HumanInTheLoop" / "Frontend.html"
GAME_OUTPUT_DIR = BASE_DIR / "static" / "generated_games"
GAME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__,
            static_folder=str(BASE_DIR / "static"),
            template_folder=str(BASE_DIR / "ChatBot"))
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestMasterLLM:
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY mancante nel file .env!")

        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.conversation_history = []

    def call_gpt(self, user_prompt, system_prompt="", json_mode=False):
        """
        Gestisce la chiamata a OpenAI.
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Errore chiamata OpenAI: {e}")
            return "Mi dispiace, sto avendo problemi di connessione con il cervello neurale (OpenAI Error)."

    def generate_welcome_message(self):
        system_prompt = """You are the AI assistant for QuestMaster. You are enthusiastic, professional, and engaging.
        Your goal is to welcome the user to the Interactive Story Creator."""

        prompt = """Generate a short, warm welcome message (max 60 words).
        Explain that you combine LLM creativity with PDDL logic.
        Ask if they want:
        1. Manual Setup
        2. Random Mode"""

        return self.call_gpt(prompt, system_prompt)

    def generate_genres(self):
        system_prompt = "You are a fiction expert. Output strictly valid JSON."
        prompt = """Generate a list of 10 diverse story genres.
        Return JSON format: {"genres": ["Fantasy", "Sci-Fi", ...]}"""

        response = self.call_gpt(prompt, system_prompt, json_mode=True)
        try:
            data = json.loads(response)
            return data.get("genres", [])
        except:
            return ["Fantasy", "Sci-Fi", "Mystery", "Horror", "Cyberpunk", "Western", "Romance", "Thriller",
                    "Historical", "Comedy"]

    def generate_tones(self):
        system_prompt = "You are a storytelling expert. Output strictly valid JSON."
        prompt = """Generate 4 distinct narrative tones.
        Return JSON format: {"tones": ["Dark", "Epic", ...]}"""

        response = self.call_gpt(prompt, system_prompt, json_mode=True)
        try:
            data = json.loads(response)
            return data.get("tones", [])
        except:
            return ["Epic & Solemn", "Dark & Gritty", "Light & Humorous", "Mysterious & Surreal"]

    def process_custom_genre(self, custom_genre):
        system_prompt = "You are a literary critic."
        prompt = f"The user chose the genre: '{custom_genre}'. Write a very short (15 words max) encouraging comment about it."
        return self.call_gpt(prompt, system_prompt)

    def generate_random_config(self):
        system_prompt = "You are a creative Game Master. Output strictly valid JSON."
        prompt = """Generate a RANDOM adventure configuration.
        Return JSON format:
        {
            "genre": "string",
            "length": "Short (2-5 min) | Medium (5-10 min) | Long (10+ min)",
            "tone": "string",
            "graphics": "Illustrated | Text-Only",
            "theme": "string (max 100 chars)"
        }"""

        response = self.call_gpt(prompt, system_prompt, json_mode=True)
        try:
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error parsing random config: {e}")
            return {
                "genre": "Steampunk",
                "length": "Medium (5-10 min)",
                "tone": "Adventurous",
                "graphics": "Illustrated",
                "theme": "A clockwork robot searches for its creator."
            }

    def generate_contextual_response(self, user_input, context):
        system_prompt = f"You are the QuestMaster assistant. Context: {context}. Be concise, engaging, and professional."

        # --- MODIFICA QUI: Istruzioni più specifiche per evitare risposte generiche o liste duplicate ---
        instructions = {
            "manual_mode_start": "Acknowledge manual mode enthusiastically. Ask the user to select a GENRE from the options below. IMPORTANT: Do NOT list specific genres in the text, just ask them to choose.",

            "genre_explanation": "The user chose this genre. Write a very brief positive comment about it (max 10 words), then ask to select the story LENGTH.",

            "length_explanation": "The user chose this length. Acknowledge the choice specifically (e.g., 'Great, a medium adventure!'), then ask to select the narrative TONE.",

            "tone_explanation": "The user chose this tone. Acknowledge it, then ask to select the GRAPHICAL mode (Illustrated vs Text).",

            "graphics_explanation": "The user chose this graphics mode. Acknowledge it, then enthusiastically ask for a short PLOT/THEME description.",

            "random_mode_intro": "Enthusiastically announce that you are generating a unique random adventure configuration."
        }

        specific_instruction = instructions.get(context, "Reply to the user input.")
        prompt = f"User Input: '{user_input}'. Instruction: {specific_instruction}"

        return self.call_gpt(prompt, system_prompt)


# Inizializzazione LLM
llm = QuestMasterLLM()
user_sessions = {}


@app.route('/')
def index():
    try:
        with open('Frontend.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template_string(content)
    except FileNotFoundError:
        return "Frontend.html not found", 404


@app.route('/api/health', methods=['GET'])
def health():
    """Verifica la connessione a OpenAI"""
    status = "offline"
    try:
        llm.client.models.list()
        status = "online"
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        status = "offline"

    return jsonify({
        'status': 'running',
        'backend_llm': 'OpenAI GPT-4o',
        'connection': status
    })


@app.route('/api/welcome', methods=['POST'])
def welcome():
    message = llm.generate_welcome_message()
    return jsonify({
        'success': True,
        'message': message,
        'options': ['Manual Setup', 'Random Mode']
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_choice = data.get('message', '')
        session_id = data.get('session_id', 'default')
        current_step = data.get('step', 'welcome')

        if session_id not in user_sessions:
            user_sessions[session_id] = {'config': {}}

        session = user_sessions[session_id]
        response_data = {'success': True}

        # --- LOGICA STATI CHAT ---
        if current_step == 'welcome':
            if user_choice == 'Random Mode':
                intro = llm.generate_contextual_response(user_choice, "random_mode_intro")
                config = llm.generate_random_config()
                session['config'] = config

                formatted_config = (f"<strong>Genre:</strong> {config['genre']}<br>"
                                    f"<strong>Length:</strong> {config['length']}<br>"
                                    f"<strong>Tone:</strong> {config['tone']}<br>"
                                    f"<strong>Graphics:</strong> {config['graphics']}<br>"
                                    f"<strong>Theme:</strong> {config['theme']}")

                response_data.update({
                    'message': f"{intro}<br><br>{formatted_config}<br><br>Ready to start?",
                    'options': ['Quest Begins!', 'Regenerate Configuration'],
                    'next_step': 'final_confirmation'
                })
            elif user_choice == 'Manual Setup':
                # Qui chiediamo a GPT di introdurre la scelta, ma SENZA elencare i generi nel testo
                msg = llm.generate_contextual_response(user_choice, "manual_mode_start")
                genres = llm.generate_genres()
                response_data.update({
                    'message': msg,
                    'options': genres + ['Custom Genre'],
                    'next_step': 'genre_selection'
                })

        elif current_step == 'genre_selection':
            if user_choice == 'Custom Genre':
                response_data.update({
                    'message': "Please type your custom genre:",
                    'show_text_input': True,
                    'next_step': 'custom_genre'
                })
            else:
                session['config']['genre'] = user_choice
                # Qui GPT commenterà il genere scelto e chiederà la lunghezza
                msg = llm.generate_contextual_response(user_choice, "genre_explanation")
                response_data.update({
                    'message': msg,
                    'options': ['Short (2-5 min)', 'Medium (5-10 min)', 'Long (10+ min)'],
                    'next_step': 'length_selection'
                })

        elif current_step == 'custom_genre':
            session['config']['genre'] = user_choice
            comment = llm.process_custom_genre(user_choice)
            msg = llm.generate_contextual_response(user_choice, "genre_explanation")
            response_data.update({
                'message': f"{comment}<br><br>{msg}",
                'options': ['Short (2-5 min)', 'Medium (5-10 min)', 'Long (10+ min)'],
                'next_step': 'length_selection'
            })

        elif current_step == 'length_selection':
            session['config']['length'] = user_choice
            # Qui GPT riconoscerà la scelta della lunghezza prima di chiedere il tono
            msg = llm.generate_contextual_response(user_choice, "length_explanation")
            tones = llm.generate_tones()
            response_data.update({
                'message': msg,
                'options': tones,
                'next_step': 'tone_selection'
            })

        elif current_step == 'tone_selection':
            session['config']['tone'] = user_choice
            msg = llm.generate_contextual_response(user_choice, "tone_explanation")
            response_data.update({
                'message': msg,
                'options': ['Illustrated', 'Text Only'],
                'next_step': 'graphics_selection'
            })

        elif current_step == 'graphics_selection':
            session['config']['graphics'] = user_choice
            msg = llm.generate_contextual_response(user_choice, "graphics_explanation")
            response_data.update({
                'message': msg,
                'show_text_input': True,
                'text_placeholder': 'Describe your plot idea...',
                'next_step': 'theme_input'
            })

        elif current_step == 'theme_input':
            session['config']['theme'] = user_choice
            c = session['config']
            summary = (f"<strong>Genre:</strong> {c['genre']}<br>"
                       f"<strong>Length:</strong> {c['length']}<br>"
                       f"<strong>Tone:</strong> {c['tone']}<br>"
                       f"<strong>Graphics:</strong> {c['graphics']}<br>"
                       f"<strong>Theme:</strong> {c.get('theme')}")

            response_data.update({
                'message': f"Setup Complete!<br><br>{summary}<br><br>Start generation?",
                'options': ['Start the Quest!', 'Edit Configuration'],
                'next_step': 'final_confirmation'
            })

        elif current_step == 'final_confirmation':
            if user_choice in ['Start the Quest!', 'Quest Begins!']:
                response_data.update({
                    'message': "Initializing Quest Generation Engine...",
                    'next_step': 'generating',
                    'options': []
                })
            elif user_choice == 'Regenerate Configuration':
                config = llm.generate_random_config()
                session['config'] = config
                formatted_config = (f"<strong>Genre:</strong> {config['genre']}<br>"
                                    f"<strong>Length:</strong> {config['length']}<br>"
                                    f"<strong>Tone:</strong> {config['tone']}<br>"
                                    f"<strong>Graphics:</strong> {config['graphics']}<br>"
                                    f"<strong>Theme:</strong> {config['theme']}")
                response_data.update({
                    'message': f"New Config:<br>{formatted_config}<br>Accept?",
                    'options': ['Quest Begins!', 'Regenerate Configuration'],
                    'next_step': 'final_confirmation'
                })
            else:
                response_data.update({
                    'message': "Let's start over. Choose a genre:",
                    'options': llm.generate_genres() + ['Custom Genre'],
                    'next_step': 'genre_selection'
                })

        return jsonify(response_data)

    except Exception as e:
        logger.exception("Chat Error")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/generate-quest-stream', methods=['GET'])
def generate_quest_stream():
    """Genera la quest con aggiornamenti di stato in tempo reale (SSE)"""

    def generate():
        session_id = request.args.get('session', 'default')
        if session_id not in user_sessions:
            yield f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': 'Session not found'})}\n\n"
            return

        session = user_sessions[session_id]

        # 1. LORE
        yield f"data: {json.dumps({'step': 'lore', 'status': 'running', 'message': 'Writing Lore with GPT...'})}\n\n"
        try:
            lore_path = generate_lore_document(session['config'])
            yield f"data: {json.dumps({'step': 'lore', 'status': 'complete', 'message': 'Lore Generated.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 'lore', 'status': 'error', 'message': str(e)})}\n\n"
            return

        # 2. PDDL
        yield f"data: {json.dumps({'step': 'pddl', 'status': 'running', 'message': 'Calculating PDDL Logic...'})}\n\n"
        try:
            success, msg = generate_valid_pddl_guaranteed(
                lore_path=LORE_FILE,
                output_dir=OUTPUT_FOLDER,
                fd_path=FAST_DOWNWARD,
                personalize=True
            )
            status = 'complete' if success else 'error'
            yield f"data: {json.dumps({'step': 'pddl', 'status': status, 'message': msg})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 'pddl', 'status': 'error', 'message': str(e)})}\n\n"
            return

        # 3. Comments / Finalize
        yield f"data: {json.dumps({'step': 'comments', 'status': 'running', 'message': 'Finalizing...'})}\n\n"
        yield f"data: {json.dumps({'step': 'comments', 'status': 'complete', 'message': 'Done.'})}\n\n"

        # 4. Done
        yield f"data: {json.dumps({'step': 'done', 'status': 'complete', 'message': 'Quest Ready!', 'redirect': f'/review.html?session={session_id}'})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/review.html')
def review_page():
    """
    Carica la pagina HTML di revisione dalla cartella HumanInTheLoop
    """
    try:
        if not HUMAN_LOOP_FILE.exists():
            return f"<h1>Errore</h1><p>File non trovato: {HUMAN_LOOP_FILE}</p><p>Controlla che il file esista in QuestMaster/HumanInTheLoop/Frontend.html</p>", 404

        with open(HUMAN_LOOP_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template_string(content)
    except Exception as e:
        return f"<h1>Errore Server</h1><p>{str(e)}</p>", 500


# --- API PER LA PAGINA DI REVISIONE (HUMAN IN THE LOOP) ---

@app.route('/api/get-lore', methods=['POST'])
def get_lore():
    """Carica il contenuto del file Lore.md."""
    try:
        if not LORE_FILE.exists():
            # Se il file non esiste, creane uno dummy per evitare crash
            return jsonify({
                'success': True,
                'sections': {'Errore': 'File Lore.md non trovato nel percorso specificato.'}
            })

        with open(LORE_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        sections = parse_lore_sections(content)
        return jsonify({'success': True, 'sections': sections})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/get-pddl', methods=['POST'])
def get_pddl():
    """Carica Domain e Problem PDDL."""
    try:
        # Assumiamo nomi standard per i file generati
        domain_path = OUTPUT_FOLDER / "domain.pddl"
        problem_path = OUTPUT_FOLDER / "problem.pddl"

        domain_content = ""
        problem_content = ""
        editable_names = []

        if domain_path.exists():
            with open(domain_path, 'r', encoding='utf-8') as f:
                domain_content = f.read()

        if problem_path.exists():
            with open(problem_path, 'r', encoding='utf-8') as f:
                problem_content = f.read()
                editable_names = extract_pddl_objects(problem_content)

        return jsonify({
            'success': True,
            'domain': domain_content if domain_content else "; Domain file not found",
            'problem': problem_content if problem_content else "; Problem file not found",
            'editable_names': editable_names
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/update-and-regenerate', methods=['POST'])
def update_and_regenerate():
    """Riceve le modifiche dall'utente e rigenera il PDDL."""
    try:
        data = request.json
        new_lore = data.get('lore', '')
        name_changes = data.get('names', {})  # Dizionario { old_name: new_name }

        # 1. Salva la Lore aggiornata
        with open(LORE_FILE, 'w', encoding='utf-8') as f:
            f.write(new_lore)

        # 2. (Opzionale) Applica il rinomina nel PDDL o nella Lore
        # Qui dovresti implementare la logica che sostituisce i nomi nei file
        # Per ora facciamo solo un pass-through della rigenerazione

        # 3. Chiama la funzione di rigenerazione (Simulata o Reale)
        # success, msg = generate_valid_pddl_guaranteed(...)

        # MOCK per test:
        success = True

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'validation_failed': True,
                'reflection_suggestions': [
                    {'issue': 'Mock Error', 'suggestion': 'This is a mock suggestion.'}
                ]
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/generate-game', methods=['POST'])
def generate_game():
    """
    Orchestra la generazione:
    1. Chiama QuestPlan per creare il piano narrativo (Markdown).
    2. Chiama creategame per creare il file HTML giocabile.
    3. Restituisce l'URL del gioco.
    """
    try:
        session_id = request.json.get('session_id', 'default')

        # File intermedi e finali
        plan_output_path = OUTPUT_FOLDER / "quest_plan.md"
        game_filename = f"game_{session_id}.html"
        game_output_path = GAME_OUTPUT_DIR / game_filename

        # 2. ESECUZIONE QUEST PLANNER
        # Chiama la funzione importata da QuestPlan.py
        # Nota: Passiamo stringhe di percorsi convertite da Pathlib
        plan_content = QuestPlan.run_quest_plan_generation()

        if not plan_content or "Error" in plan_content:
            raise Exception("Fallimento nella generazione del Quest Plan.")

        # 3. ESECUZIONE CREATE GAME
        # Chiama la funzione importata da creategame.py
        success = creategame.run_create_game(
            str(plan_output_path),
            str(game_output_path)
        )

        if not success:
            raise Exception("Fallimento nella generazione del file HTML del gioco.")

        # 4. RITORNO URL
        # L'URL deve puntare alla cartella static dove abbiamo salvato il file
        game_url = f"/static/generated_games/{game_filename}"

        return jsonify({
            'success': True,
            'game_url': game_url
        })

    except Exception as e:
        logger.exception("Errore generazione gioco")
        return jsonify({'success': False, 'error': str(e)})


def parse_lore_sections(lore_text):
    """Divide il markdown della Lore in sezioni per l'editor."""
    sections = {}
    current_section = "Intro"
    buffer = []

    for line in lore_text.split('\n'):
        if line.strip().startswith('## '):
            if buffer:
                sections[current_section] = '\n'.join(buffer).strip()
            current_section = line.strip().replace('## ', '')
            buffer = []
        else:
            buffer.append(line)

    if buffer:
        sections[current_section] = '\n'.join(buffer).strip()

    return sections

def extract_pddl_objects(problem_text):
    """Estrae nomi di oggetti modificabili dal Problem PDDL (logica semplificata)."""
    objects = []
    try:
        # Cerca la sezione (:objects ...)
        match = re.search(r'\(:objects(.*?)\)', problem_text, re.DOTALL)
        if match:
            content = match.group(1)
            # Pulisci e dividi, ignorando i tipi (es. - location)
            tokens = content.split()
            for i, token in enumerate(tokens):
                if not token.startswith('-') and (i + 1 >= len(tokens) or not tokens[i + 1].startswith('-')):
                    # Filtro grezzo, in produzione serve un parser migliore
                    if token.isalnum():
                        objects.append(token)
    except Exception:
        pass
    return list(set(objects))  # Rimuovi duplicati

if __name__ == '__main__':
    print("🚀 QuestMaster Backend (OpenAI Edition) Starting...")


    def open_browser():
        webbrowser.open_new_tab('http://127.0.0.1:5000')


    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1, open_browser).start()

        # AGGIUNGI use_reloader=False QUI SOTTO
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)