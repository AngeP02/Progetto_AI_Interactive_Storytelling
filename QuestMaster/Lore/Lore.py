import os
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

        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
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
    print("genre:", genre)
    print("length:", length)
    print("tone:", tone)
    print("graphics:", graphics)
    print("theme:", theme)

    # System prompt: spiega al modello cosa deve produrre
    system_prompt = """You are a narrative design professional and a PDDL expert.
    You must generate a complete Lore Document for an interactive quest, strictly following the structure provided by the template.
    Use an epic and mysterious narrative style, focused on exploration and puzzle-solving.
    Respond ONLY with the final formatted structure.

    Structure to follow scrupulously:

    # Title: [Evocative Title]

    ## 1. Mission Description
    [Brief description of the plot, the protagonist, and the central objective.]

    ## 2. Setting and Context
    Key Locations:
    - [Location A]
    - [Location B]
    - [Location C]
    - [Location D]

    Key Items:
    - [Item 1 (Essential for progress)]
    - [Item 2 (Key to an obstacle)]
    - [Item 3 (Source of energy/power)]

    Characters:
    - [Protagonist (Role)]
    - [Antagonist/Enemy (Role)]
    - [Ally/Neutral (Role)]

    ## 3. Initial State and Objective
    - Initial State: [Protagonist's starting position and state of key elements.]
    - Mission Objective: [Final action and desired outcome.]

    ## 4. Obstacles and Progress Conditions
    - Obstacle 1: [Condition for overcoming the obstacle.]
    - Obstacle 2: [Condition for overcoming the obstacle.]
    - Crucial Progression: [Crucial element or action that advances the plot (Puzzle).]

    ## 5. Technical Constraints (PDDL)
    Suggested Actions:
    - move(from, to)
    - take(item)
    - use(item, location)
    - disable(enemy)
    - solve(puzzle)

    Branching Factor (Decision complexity):
    - min = [integer]
    - max = [integer]

    Depth Constraints (Quest duration):
    - min = [integer]
    - max = [integer]

    At the end of the Lore Document, append two sections:

## 7. Logical Representation (for PDDL)
List initial and goal facts in parenthesis form.

## 8. Object Mappings
List all unique objects by category (locations, items, characters).

    """
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