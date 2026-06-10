import os
import json
import logging
import webbrowser
import re
from threading import Timer
from pathlib import Path
import requests
from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from QuestMaster.Generate_PDDL.GenerazionePddl import generate_valid_pddl_guaranteed
from QuestMaster.Lore.GenerazioneLore import generate_lore_document
from QuestMaster.Game import CreazioneGioco, QuestPlan
import base64

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"
OUTPUT_FOLDER = SCRIPT_DIR / "pddl_output"
FAST_DOWNWARD = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"
HUMAN_LOOP_FILE = BASE_DIR / "HumanInTheLoop" / "Frontend.html"
GAME_OUTPUT_DIR = BASE_DIR / "static" / "generated_games"
GAME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__,static_folder=str(BASE_DIR / "static"),template_folder=str(BASE_DIR / "ChatBot"))
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestMasterLLM:
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY mancante nel file .env")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.conversation_history = []

    def call_gpt(self, user_prompt, system_prompt="", json_mode=False):
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
            return "Errore di connessione a GPT"

    def generate_cover_image(self, lore_text, output_path):
        try:
            system_prompt = "Sei un esperto artista visivo e ingegnere di prompt per l'IA generativa."
            summary_prompt = f"""Leggi il seguente testo (Lore) e crea una descrizione visiva dettagliata e suggestiva, 
            adatta all'immagine di copertina di un libro/storia. 
            Concentrati sull'ambientazione principale, sull'atmosfera e sul conflitto centrale.
            La descrizione deve essere vivida e concisa (massimo 50 parole).
              LORE:
              {lore_text[:2000]}
              """
            visual_description = self.call_gpt(summary_prompt, system_prompt)
            logger.info(f"Prompt generated: {visual_description}")
            response = self.client.images.generate(
                model="gpt-image-1-mini",
                prompt=f"A book cover illustration. {visual_description} Digital art style, detailed, cinematic lighting.",
                size="1024x1024",
                quality="low",
                n=1,
            )

            image_obj = response.data[0]
            img_data = None
            if hasattr(image_obj, 'url') and image_obj.url:
                img_data = requests.get(image_obj.url).content
            elif hasattr(image_obj, 'b64_json') and image_obj.b64_json:
                img_data = base64.b64decode(image_obj.b64_json)
            elif isinstance(image_obj, dict):
                if image_obj.get('url'):
                    img_data = requests.get(image_obj['url']).content
                elif image_obj.get('b64_json'):
                    img_data = base64.b64decode(image_obj['b64_json'])
            if img_data:
                with open(output_path, 'wb') as handler:
                    handler.write(img_data)
                return True, "Immagine generata e salvata con successo."
            else:
                raise ValueError(f"Impossibile estrarre i dati dell'immagine dalla risposta dell'API: {image_obj}")

        except Exception as e:
            logger.error(f"Errore generazione immagine: {e}")
            return False, f"Errore generazione immagine: {str(e)}"

    def generate_welcome_message(self):
        system_prompt = """Sei l'assistente AI di QuestMaster. Sei entusiasta, professionale e coinvolgente.
        Il tuo obiettivo è dare il benvenuto all'utente nell'Interactive Story Creator."""

        prompt = """Genera un breve e caloroso messaggio di benvenuto (massimo 60 parole).
        Spiega che unisci la creatività LLM alla logica PDDL.
        Chiedi se desiderano:
        1. Impostazione manuale
        2. Modalità casuale"""

        return self.call_gpt(prompt, system_prompt)

    def generate_genres(self):
        system_prompt = "Sei un esperto di narrativa. Genera un JSON rigorosamente valido."
        prompt = """Genera un elenco di 10 generi di storie diversi.
        Formato JSON restituito: {"genres": ["Fantasy", "Fantascienza", ...]}"""
        response = self.call_gpt(prompt, system_prompt, json_mode=True)
        try:
            data = json.loads(response)
            return data.get("genres", [])
        except:
            return ["Fantasy", "Fantascienza", "Mistero", "Horror", "Cyberpunk", "Western", "Romantico", "Thriller",
            "Storico", "Commedia"]

    def generate_tones(self):
        system_prompt = "Sei un esperto di storytelling. Genera un JSON rigorosamente valido."
        prompt = """Genera 4 toni narrativi distinti.
        Formato JSON restituito: {"tones": ["Dark", "Epic", ...]}"""
        response = self.call_gpt(prompt, system_prompt, json_mode=True)
        try:
            data = json.loads(response)
            return data.get("tones", [])
        except:
            return ["Epico", "Oscuro", "Leggero e umoristico", "Misterioso e surreale"]

    def process_custom_genre(self, custom_genre):
        system_prompt = "Sei un critico letterario."
        prompt = f"L'utente ha scelto il genere: '{custom_genre}'. Scrivi un commento molto breve (massimo 15 parole) incoraggiante al riguardo."
        return self.call_gpt(prompt, system_prompt)

    def generate_random_config(self):
        system_prompt = "Sei un Game Master creativo. Genera un JSON rigorosamente valido."
        prompt = """Genera una configurazione di avventura CASUALE.
        Restituisci il formato JSON:
        {
            "genre": "string",
            "length": "Breve (2-5 min) | Medio (5-10 min) | Lungo (10+ min)",
            "tone": "string",
            "graphics": "Illustrato | Solo testo",
            "theme": "stringa (max 100 caratteri)"
        }"""

        response = self.call_gpt(prompt, system_prompt, json_mode=True)
        try:
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error parsing random config: {e}")
            return {
                "genere": "Steampunk",
                "durata": "Media (5-10 min)",
                "tono": "Avventuroso",
                "grafica": "Illustrato",
                "tema": "Un robot meccanico alla ricerca del suo creatore."
            }

    def generate_contextual_response(self, user_input, context):
        system_prompt = f"Sei l'assistente di QuestMaster. Contesto: {context}. Sii conciso, coinvolgente e professionale."

        instructions = {
            "manual_mode_start": "Riconosci con entusiasmo la modalità manuale. Chiedi all'utente di selezionare un GENERE tra le opzioni seguenti. IMPORTANTE: NON elencare generi specifici nel testo, chiedi semplicemente di scegliere.",

            "genre_explanation": "L'utente ha scelto questo genere. Scrivi un breve commento positivo al riguardo (massimo 10 parole), quindi chiedi di selezionare la LUNGHEZZA della storia.",

            "length_explanation": "L'utente ha scelto questa lunghezza. Riconosci in modo specifico la scelta (ad esempio, 'Ottimo, un'avventura di media difficoltà!'), quindi chiedi di selezionare il TONO narrativo.",

            "tone_explanation": "L'utente ha scelto questo tono. Riconoscilo, quindi chiedi di selezionare la modalità GRAFICA (Illustrata vs Testo).",

            "graphics_explanation": "L'utente ha scelto questa modalità grafica. Riconoscilo, quindi chiedi con entusiasmo un breve Descrizione TRAMA/TEMA.",

            "random_mode_intro": "Annuncia con entusiasmo che stai generando una configurazione di avventura casuale unica."
        }

        specific_instruction = instructions.get(context, "Rispondi all'input dell'utente.")
        prompt = f"Input utente: '{user_input}'. Istruzione: {specific_instruction}"

        return self.call_gpt(prompt, system_prompt)


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

@app.route('/api/apply-reflection', methods=['POST'])
def apply_reflection():
    try:
        data = request.json
        reflection_text = data.get('reflection_text', '')

        import re
        match_domain = re.search(r"---DOMAIN---(.*?)---PROBLEM---", reflection_text, re.DOTALL)
        match_problem = re.search(r"---PROBLEM---(.*)", reflection_text, re.DOTALL)

        if not match_domain or not match_problem:
            return jsonify({'success': False, 'error': 'Formato suggerimento non valido.'})

        domain_fixed = match_domain.group(1).strip()
        problem_fixed = match_problem.group(1).strip()

        domain_path = OUTPUT_FOLDER / "domain.pddl"
        problem_path = OUTPUT_FOLDER / "problem.pddl"

        with open(domain_path, 'w', encoding='utf-8') as f:
            f.write(domain_fixed)
        with open(problem_path, 'w', encoding='utf-8') as f:
            f.write(problem_fixed)

        from QuestMaster.Generate_PDDL.GenerazionePddl import FastDownwardValidator
        validator = FastDownwardValidator(FAST_DOWNWARD)
        success, message, _ = validator.validate(domain_path, problem_path, save_plan_to=OUTPUT_FOLDER)

        return jsonify({
            'success': success,
            'message': 'Correzioni applicate e PDDL rivalidato.' if success else f'Rivalidazione fallita: {message}'
        })
    except Exception as e:
        logger.exception("Errore apply-reflection")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/generate-quest-stream', methods=['GET'])
def generate_quest_stream():

    def generate():
        session_id = request.args.get('session', 'default')
        if session_id not in user_sessions:
            yield f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': 'Session not found'})}\n\n"
            return

        session = user_sessions[session_id]
        config = session['config']

        yield f"data: {json.dumps({'step': 'lore', 'status': 'running', 'message': 'Writing Lore with GPT...'})}\n\n"
        try:
            LORE_FILE.parent.mkdir(parents=True, exist_ok=True)
            lore_path = generate_lore_document(config)
            with open(LORE_FILE, 'r', encoding='utf-8') as f:
                lore_content = f.read()
            yield f"data: {json.dumps({'step': 'lore', 'status': 'complete', 'message': 'Lore Generated.'})}\n\n"
        except Exception as e:
            logger.exception("Lore generation failed")
            yield f"data: {json.dumps({'step': 'lore', 'status': 'error', 'message': str(e)})}\n\n"
            return

        cover_image_filename = None
        graphics_pref = str(config.get('graphics', '')).lower()
        if 'illustrat' in graphics_pref:
            yield f"data: {json.dumps({'step': 'illustration', 'status': 'running', 'message': 'Painting Cover Art (DALL-E 3)...'})}\n\n"
            try:
                cover_image_filename = f"cover.jpg"
                cover_image_path = GAME_OUTPUT_DIR / cover_image_filename
                success, msg = llm.generate_cover_image(lore_content, cover_image_path)
                if success:
                    session['cover_image'] = cover_image_filename
                    yield f"data: {json.dumps({'step': 'illustration', 'status': 'complete', 'message': 'Illustration Created.'})}\n\n"
                else:
                    yield f"data: {json.dumps({'step': 'illustration', 'status': 'error', 'message': msg})}\n\n"
            except Exception as e:
                logger.exception("Image generation failed")
                yield f"data: {json.dumps({'step': 'illustration', 'status': 'error', 'message': str(e)})}\n\n"
        yield f"data: {json.dumps({'step': 'pddl', 'status': 'running', 'message': 'Calculating PDDL Logic...'})}\n\n"
        try:
            success, msg = generate_valid_pddl_guaranteed(
                lore_path=LORE_FILE,
                output_dir=OUTPUT_FOLDER,
                fd_path=FAST_DOWNWARD,
                personalize=True
            )
            if success:
                yield f"data: {json.dumps({'step': 'pddl', 'status': 'complete', 'message': msg})}\n\n"
            elif "REFLECTION_PENDING::" in msg:
                suggestion = msg.split("REFLECTION_PENDING::", 1)[1]
                explanation = suggestion.split("---DOMAIN---")[0].replace("---SPIEGAZIONE---", "").strip()
                session['reflection_suggestion'] = suggestion
                yield f"data: {json.dumps({'step': 'pddl', 'status': 'reflection_needed', 'message': explanation, 'full_suggestion': suggestion})}\n\n"
                return
            else:
                yield f"data: {json.dumps({'step': 'pddl', 'status': 'error', 'message': msg})}\n\n"
                return
        except Exception as e:
            yield f"data: {json.dumps({'step': 'pddl', 'status': 'error', 'message': str(e)})}\n\n"
            return

        yield f"data: {json.dumps({'step': 'comments', 'status': 'running', 'message': 'Finalizing...'})}\n\n"
        yield f"data: {json.dumps({'step': 'comments', 'status': 'complete', 'message': 'Done.'})}\n\n"
        yield f"data: {json.dumps({'step': 'done', 'status': 'complete', 'message': 'Quest Ready!', 'redirect': f'/review.html?session={session_id}'})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/review.html')
def review_page():
    try:
        if not HUMAN_LOOP_FILE.exists():
            return f"<h1>Errore</h1><p>File non trovato: {HUMAN_LOOP_FILE}</p><p>Controlla che il file esista in QuestMaster/HumanInTheLoop/Frontend.html</p>", 404
        with open(HUMAN_LOOP_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template_string(content)
    except Exception as e:
        return f"<h1>Errore Server</h1><p>{str(e)}</p>", 500

@app.route('/api/get-lore', methods=['POST'])
def get_lore():
    try:
        if not LORE_FILE.exists():
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
    try:
        domain_path = OUTPUT_FOLDER / "domain_commented.pddl"
        problem_path = OUTPUT_FOLDER / "problem_commented.pddl"
        if not domain_path.exists():
            domain_path = OUTPUT_FOLDER / "domain.pddl"
        if not problem_path.exists():
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
    try:
        data = request.json
        new_lore = data.get('lore', '')
        name_changes = data.get('names', {})
        if new_lore:
            with open(LORE_FILE, 'w', encoding='utf-8') as f:
                f.write(new_lore)
        if name_changes:
            domain_path = OUTPUT_FOLDER / "domain.pddl"
            problem_path = OUTPUT_FOLDER / "problem.pddl"
            if domain_path.exists():
                with open(domain_path, 'r', encoding='utf-8') as f:
                    domain_content = f.read()
                new_domain = apply_pddl_renaming(domain_content, name_changes)
                with open(domain_path, 'w', encoding='utf-8') as f:
                    f.write(new_domain)
            if problem_path.exists():
                with open(problem_path, 'r', encoding='utf-8') as f:
                    problem_content = f.read()
                new_problem = apply_pddl_renaming(problem_content, name_changes)
                with open(problem_path, 'w', encoding='utf-8') as f:
                    f.write(new_problem)
        return jsonify({'success': True, 'message': 'Lore e PDDL aggiornati con successo.'})
    except Exception as e:
        logger.error(f"Errore aggiornamento: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/generate-game', methods=['POST'])
def generate_game():
    try:
        session_id = request.json.get('session_id', 'default')
        plan_output_path = OUTPUT_FOLDER / "quest_plan.md"
        game_filename = f"game_{session_id}.html"
        game_output_path = GAME_OUTPUT_DIR / game_filename
        plan_content = QuestPlan.run_quest_plan_generation()
        if not plan_content or "Error" in plan_content:
            raise Exception("Fallimento nella generazione del Quest Plan.")
        with open(plan_output_path, "w", encoding="utf-8") as f:
            f.write(plan_content)
        print(f"Quest Plan salvato correttamente in: {plan_output_path}")
        cover_image_filename = user_sessions[session_id].get('cover_image')
        cover_image_url = None
        if cover_image_filename:
            cover_image_url = cover_image_filename
        success = CreazioneGioco.run_create_game(
            str(plan_output_path),
            str(game_output_path),
            cover_image_url_path=cover_image_url
        )
        if not success:
            raise Exception("Fallimento nella generazione del file HTML del gioco.")
        game_url = f"/static/generated_games/{game_filename}"
        return jsonify({
            'success': True,
            'game_url': game_url
        })
    except Exception as e:
        logger.exception("Errore generazione gioco")
        return jsonify({'success': False, 'error': str(e)})

def parse_lore_sections(lore_text):
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
    objects = []
    try:
        match = re.search(r'\(:objects(.*?)\)', problem_text, re.DOTALL)
        if match:
            content = match.group(1)
            tokens = content.split()
            for i, token in enumerate(tokens):
                if not token.startswith('-') and (i + 1 >= len(tokens) or not tokens[i + 1].startswith('-')):
                    if token.isalnum():
                        objects.append(token)
    except Exception:
        pass
    return list(set(objects))

def apply_pddl_renaming(text, name_changes):
    if not name_changes:
        return text
    updated_text = text
    for old_name, new_name in name_changes.items():
        if not old_name or not new_name:
            continue
        pattern = r'\b' + re.escape(old_name) + r'\b'
        updated_text = re.sub(pattern, new_name, updated_text)
    return updated_text


if __name__ == '__main__':
    print("QuestMaster Backend (OpenAI Edition) Starting...")
    def open_browser():
        webbrowser.open_new_tab('http://127.0.0.1:5000')
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)