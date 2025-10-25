import os
import json
import requests
import logging

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"

def call_ollama(prompt, system_prompt=""):
    """Utility per chiamare Ollama e restituire il testo generato"""
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.8,
                "top_p": 0.9,
                "num_predict": 800
            }
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()

    except Exception as e:
        logger.error(f"Errore chiamata Ollama: {e}")
        return f"Errore generazione documento: {e}"


def generate_lore_document(config):
    """
    Genera un Lore Document (Documento della Trama) a partire dai parametri configurati.
    Restituisce il path del file generato.
    """
    genre = config.get("genre", "Fantasy")
    length = config.get("length", "Medium (5-10 min)")
    tone = config.get("tone", "Neutral")
    graphics = config.get("graphics", "Text Only")
    theme = config.get("theme", "An adventure full of mystery.")

    # System prompt: spiega al modello cosa deve produrre
    system_prompt = """You are a professional narrative designer and PDDL expert.
You must generate a complete Lore Document for an interactive quest. 
Follow this exact structure and formatting:

=== LORE DOCUMENT ===
**Quest Description:**
- Initial State:
- Goal:
- Obstacles:
- Context and World Background:

**Branching Factor:**
- Minimum number of possible actions per state.
- Maximum number of possible actions per state.

**Depth Constraints:**
- Minimum number of narrative steps to reach the goal.
- Maximum number of narrative steps to reach the goal.

Keep the tone coherent with the genre and theme.
Use concise but vivid prose (max 300 words total).
Return only the final formatted document, no explanations."""

    # Prompt specifico per la storia configurata
    prompt = f"""
Generate a Lore Document for a quest with the following setup:
- Genre: {genre}
- Length: {length}
- Tone: {tone}
- Graphics Mode: {graphics}
- Theme: {theme}

Adapt the structure and narrative details to fit this configuration.
"""
    lore_text = call_ollama(prompt, system_prompt)
    output_dir = "Generated_Lore"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"Lore_document.txt"
    file_path = os.path.join(output_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(lore_text)
    logger.info(f"Lore document salvato in: {file_path}")
    return os.path.abspath(file_path)
