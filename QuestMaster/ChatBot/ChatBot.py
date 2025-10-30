from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests
import json
import logging
import webbrowser
from threading import Timer
import os

from QuestMaster.Lore.Lore import generate_lore_document

from flask import Flask, render_template
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # vai da ChatBot a QuestMaster
app = Flask(__name__,
            static_folder=str(BASE_DIR / "static"),
            template_folder=str(BASE_DIR / "ChatBot"))
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestMasterLLM:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3"
        self.conversation_history = []

    def call_ollama(self, prompt, system_prompt=""):
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
        system_prompt = """You are the AI assistant for QuestMaster, a system that creates interactive stories using LLM and PDDL logic. You must be enthusiastic, engaging, and professional. Your role is to guide the user in setting up their personalized adventure."""

        prompt = """Generate a warm welcome message for QuestMaster, a system that creates personalized interactive text adventures.
                    Briefly explain that you can help create unique stories by combining creativity and logic, and ask if the user wants to:
                    1. Manual Setup (choose every detail)
                    2. Random Mode (you, as Game Master, decide everything) 
                    Keep your tone enthusiastic and professional, max 75 words."""

        return self.call_ollama(prompt, system_prompt)

    def generate_genres(self):
        system_prompt = """You're a fiction and gaming expert. You know all literary and video game genres."""
        prompt = """Generate a list of 10 classic and diverse genres for interactive stories. Include classic genres.
                    Respond ONLY with a JSON list in the format: ["Genre 1", "Genre 2", ...]
                    Examples: Fantasy, Noir, Horror, Drama, Romance, Crime, Adventure, etc."""

        response = self.call_ollama(prompt, system_prompt)
        try:
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                genres = json.loads(json_str)
                return genres
        except:
            pass
        return ["Fantasy", "Science Fiction", "Psychological","Drama", "Romance", "Comedy", "Thriller", "Historical", "Teen", "Western"]

    def generate_tones(self):
        system_prompt = """You are a storytelling expert and know all the possible narrative tones"""
        prompt = """Generate 4 different narrative tones for interactive stories.
                    Respond ONLY with a JSON list: ["Tone 1", "Tone 2", "Tone 3", "Tone 4"]
                    Examples: Epic and Solemn, Ironic and Satirical, Dark and Mysterious, etc."""
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
        return ["Epic and Solemn", "Ironic and Satirical", "Dark and Mysterious", "Light and Adventurous"]

    def process_custom_genre(self, custom_genre):
        system_prompt = """You are an experienced literary critic who appreciates creativity in narrative genres."""
        prompt = f"""The user has chosen the custom genre: "{custom_genre}"
                    Write a short, positive and encouraging comment about this choice (maximum 20 words).
                    Briefly explain why it's interesting or what narrative possibilities it offers."""
        return self.call_ollama(prompt, system_prompt)

    def generate_random_config(self):
        system_prompt = """You are a creative Game Master who loves to surprise players with unique and interesting setups."""
        prompt = """Generate a RANDOM configuration for an interactive adventure. Return ONLY a JSON with this structure:
                    {
                    "genre": "a creative genre",
                    "length": "one of: Short (2-5 min), Medium (5-10 min), Long (10+ min)",
                    "tone": "an interesting narrative tone",
                    "graphics": "one of: Illustrated, Text-Only",
                    "theme": "an original and engaging storyline of up to 100 characters"
                    }
                    Be creative and surprising!"""
        response = self.call_ollama(prompt, system_prompt)
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                config = json.loads(json_str)
                return config
        except Exception as e:
            logger.error(f"Random config parsing error: {e}")
            pass
        return {
                "genre": "Fantasy",
                "length": "Medium (5 - 10 min)",
                "tone": "Adventurous and Ironic",
                "graphics": "Illustrated",
                "theme": "An inventor must save the city with his magical machines."
                }

    def generate_contextual_response(self, user_input, context):
        system_prompt = f"""You are QuestMaster's assistant. Current context: {context}.
                            Keep your tone professional but enthusiastic. Keep your answers short and direct."""

        context_prompts = {
            "genre_explanation": """The user has chosen the genre (not gender). Briefly explain what happens next (length selection) and how length affects PDDL complexity. Max 50 words.""",

            "length_explanation": """The user has chosen the length. Now explain your choice of narrative tone and how it influences the story's atmosphere. Maximum 50 words.""",

            "tone_explanation": """The user has chosen the tone. Now ask about the graphical mode (illustrated vs. text-only), briefly explaining the difference. Max 50 words.""",

            "graphics_explanation": """The user has chosen the graphical mode. Now ask them to describe the theme/plot of the story. Give short examples and encourage creativity. Maximum 50 words.""",

            "manual_mode_start": """The user has chosen manual mode. Introduce the genre choice and explain that they can choose from generated options or enter a custom gender. Max 50 words.""",

            "random_mode_intro": """The user has chosen random mode. Describe what you're about to do (generate everything randomly) with Game Master enthusiasm. Max 50 words."""
        }

        prompt = context_prompts.get(context, f"Reply to the user in context: {context}")
        return self.call_ollama(prompt, system_prompt)

llm = QuestMasterLLM()
user_sessions = {}


@app.route('/')
def index():
    try:
        with open('Frontend.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template_string(content)
    except FileNotFoundError:
        return "<h1>Error: Frontend.html not found.</h1><p>Make sure the 'Frontend.html' file is in the same folder as your Python script.</p>", 404


@app.route('/api/welcome', methods=['POST'])
def welcome():
    try:
        message = llm.generate_welcome_message()
        return jsonify({
            'success': True,
            'message': message,
            'options': ['Manual Setup', 'Random Mode']
        })
    except Exception as e:
        logger.error(f"Error welcome: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_choice = data.get('message', '')
        session_id = data.get('session_id', 'default')
        current_step = data.get('step', 'welcome')
        if session_id not in user_sessions:
            user_sessions[session_id] = {
                'config': {},
                'conversation_history': []
            }
        session = user_sessions[session_id]
        response_data = {'success': True}
        if current_step == 'welcome':
            if user_choice == 'Random Mode':
                intro_msg = llm.generate_contextual_response(user_choice, "random_mode_intro")
                config = llm.generate_random_config()
                session['config'] = config
                config_msg = f"""Here's your randomly generated quest:
                                **Genre:** {config['genre']}
                                **Length:** {config['length']}
                                **Tone:** {config['tone']}
                                **Graphics:** {config['graphics']}
                                **Theme:** {config['theme']}
                                Are you ready to start your quest?"""
                response_data.update({
                    'message': intro_msg + "\n\n" + config_msg,
                    'options': ['Quest Begins!', 'Regenerate Configuration'],
                    'next_step': 'final_confirmation'
                })

            elif user_choice == 'Manual Setup':
                genres = llm.generate_genres()
                message = llm.generate_contextual_response(user_choice, "manual_mode_start")
                response_data.update({
                    'message': message + "\n\nChoose from these genres:",
                    'options': genres + ['Custom Genre'],
                    'next_step': 'genre_selection'
                })

        elif current_step == 'genre_selection':
            if user_choice == 'Custom Genre':
                response_data.update({
                    'message': "Enter the custom genre you want for your adventure:",
                    'show_text_input': True,
                    'text_placeholder': 'Write your own custom genre...',
                    'next_step': 'custom_genre'
                })
            else:
                session['config']['genre'] = user_choice
                message = llm.generate_contextual_response(user_choice, "genre_explanation")
                response_data.update({
                    'message': message,
                    'options': ['Short (2-5 min)', 'Medium (5-10 min)', 'Long (10+ min)'],
                    'next_step': 'length_selection'
                })

        elif current_step == 'custom_genre':
            session['config']['genre'] = user_choice
            comment = llm.process_custom_genre(user_choice)
            message = llm.generate_contextual_response(user_choice, "genre_explanation")
            response_data.update({
                'message': f"Excellent! \"{user_choice}\" - {comment}\n\n{message}",
                'options': ['Short (2-5 min)', 'Medium (5-10 min)', 'Long (10+ min)'],
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
                'options': ['Illustrated', 'Text Only'],
                'next_step': 'graphics_selection'
            })

        elif current_step == 'graphics_selection':
            session['config']['graphics'] = user_choice
            message = llm.generate_contextual_response(user_choice, "graphics_explanation")

            response_data.update({
                'message': message,
                'show_text_input': True,
                'text_placeholder': 'Describe the plot of your adventure...',
                'next_step': 'theme_input'
            })

        elif current_step == 'theme_input':
            session['config']['theme'] = user_choice
            config = session['config']
            final_message = f"""Setup completed successfully!
                                **Your Custom Quest:**
                                **Genre:** {config['genre']}
                                **Length:** {config['length']}
                                **Tone:** {config['tone']}
                                **Mode:** {config['graphics']}
                                **Theme:** {user_choice}
                                The PDDL system will analyze these parameters to create a coherent logical structure, while the LLM will generate the engaging narrative. Ready to get started?"""
            response_data.update({
                'message': final_message,
                'options': ['Start the Quest!', 'Edit Configuration'],
                'next_step': 'final_confirmation'
            })



        elif current_step == 'final_confirmation':
            if user_choice in ['Start the Quest!', 'Quest Begins!']:
                try:
                    lore_path = generate_lore_document(session['config'])
                    print("DEBUG LORE PATH:", lore_path)
                    response_data.update({
                        'message': f"Quest started! Lore Document saved in {lore_path}.",
                        'quest_ready': True,
                        'config': session['config']
                    })
                except Exception as e:
                    print("ERROR generating lore:", e)
                    response_data.update({
                        'message': f"Failed to generate lore: {e}",
                        'quest_ready': False,
                        'config': session['config']
                    })

            elif user_choice == 'Regenerate Configuration':
                config = llm.generate_random_config()
                session['config'] = config
                response_data.update({
                    'message': f"""New configuration generated:
                                    **Genre:** {config['genre']}
                                    **Length:** {config['length']}
                                    **Tone:** {config['tone']}
                                    **Graphics:** {config['graphics']}
                                    **Theme:** {config['theme']}
                                    Are you ready to start your quest?""",
                    'options': ['Quest Begins!', 'Regenerate Configuration'],
                    'next_step': 'final_confirmation'
                })
            else:
                response_data.update({
                    'message': "Quest cancelled or configuration incomplete.",
                    'options': [],
                    'quest_ready': False
                })

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error chat: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/health', methods=['GET'])
def health():
    try:
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
    print("Avvio QuestMaster Backend...")
    print("Assicurati che Ollama sia in esecuzione: ollama serve")
    print("Modello richiesto: llama3")
    print("Apro il frontend nel browser...")
    def open_browser():
          webbrowser.open_new_tab('http://127.0.0.1:5000')

    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1, open_browser).start()

    app.run(host='0.0.0.0', port=5000, debug=True)