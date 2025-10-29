import os
import requests
import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"


def call_ollama(prompt, system_prompt="", max_tokens=2000, temperature=0.8):
    """Utility per chiamare Ollama e restituire il testo generato"""
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_predict": max_tokens
            }
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()

    except requests.exceptions.Timeout:
        logger.error("Timeout nella chiamata Ollama")
        return None
    except Exception as e:
        logger.error(f"Errore chiamata Ollama: {e}")
        return None


def generate_story_elements(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera gli elementi base della storia in formato strutturato.
    Ritorna un dizionario con tutti gli elementi necessari.
    """
    genre = config.get("genre", "Fantasy")
    theme = config.get("theme", "An adventure full of mystery")
    tone = config.get("tone", "Neutral")

    system_prompt = """You are a creative narrative designer specializing in interactive storytelling.
    Generate story elements in a clear, structured format.
    Be creative but concise."""

    prompt = f"""Create core story elements for an interactive quest with these parameters:
Genre: {genre}
Theme: {theme}
Tone: {tone}

Generate the following in a structured format:

1. TITLE: A captivating title (max 10 words)

2. MISSION: Brief mission description (2-3 sentences) including:
   - Who is the protagonist
   - What is the main objective
   - Why it matters

3. LOCATIONS: List exactly 4 key locations (just names, one per line)

4. ITEMS: List exactly 3 key items needed for the quest (name and brief purpose, one per line)

5. CHARACTERS: List exactly 3 characters:
   - Protagonist (name and role)
   - Antagonist (name and role)
   - Ally (name and role)

6. OBSTACLES: List exactly 3 obstacles the protagonist must overcome (one per line)

7. PUZZLE: Describe one central puzzle or crucial challenge (1-2 sentences)

Keep responses clear and focused. Format with labels as shown above."""

    response = call_ollama(prompt, system_prompt, max_tokens=1500, temperature=0.85)

    if not response:
        logger.error("Failed to generate story elements")
        return None

    # Parse la risposta
    return parse_story_elements(response, config)


def parse_story_elements(response: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estrae gli elementi dalla risposta dell'LLM.
    Gestisce parsing flessibile per evitare errori di formato.
    """
    elements = {
        "title": "Untitled Quest",
        "mission": "",
        "locations": [],
        "items": [],
        "characters": [],
        "obstacles": [],
        "puzzle": "",
        "config": config
    }

    lines = response.split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Identifica sezioni
        upper_line = line.upper()
        if 'TITLE' in upper_line and ':' in line:
            elements['title'] = line.split(':', 1)[1].strip()
        elif 'MISSION' in upper_line and ':' in line:
            current_section = 'mission'
            mission_text = line.split(':', 1)[1].strip()
            if mission_text:
                elements['mission'] = mission_text
        elif 'LOCATION' in upper_line:
            current_section = 'locations'
        elif 'ITEM' in upper_line:
            current_section = 'items'
        elif 'CHARACTER' in upper_line:
            current_section = 'characters'
        elif 'OBSTACLE' in upper_line:
            current_section = 'obstacles'
        elif 'PUZZLE' in upper_line:
            current_section = 'puzzle'
            puzzle_text = line.split(':', 1)[1].strip() if ':' in line else ''
            if puzzle_text:
                elements['puzzle'] = puzzle_text
        else:
            # Aggiungi contenuto alla sezione corrente
            if current_section and line.startswith('-'):
                line = line[1:].strip()

            if current_section == 'mission' and line:
                elements['mission'] += ' ' + line
            elif current_section == 'locations' and line:
                elements['locations'].append(line)
            elif current_section == 'items' and line:
                elements['items'].append(line)
            elif current_section == 'characters' and line:
                elements['characters'].append(line)
            elif current_section == 'obstacles' and line:
                elements['obstacles'].append(line)
            elif current_section == 'puzzle' and line:
                elements['puzzle'] += ' ' + line

    # Validazione e fallback
    if not elements['locations']:
        elements['locations'] = ["Ancient Temple", "Dark Forest", "Crystal Cave", "Abandoned Tower"]
    if not elements['items']:
        elements['items'] = ["Ancient Key", "Magic Crystal", "Sacred Scroll"]
    if not elements['characters']:
        elements['characters'] = ["Hero (Protagonist)", "Shadow Lord (Antagonist)", "Wise Elder (Ally)"]
    if not elements['obstacles']:
        elements['obstacles'] = ["Locked gate blocking the path", "Guardian creature protecting the artifact",
                                 "Ancient riddle puzzle"]

    # Limita alle quantità richieste
    elements['locations'] = elements['locations'][:4]
    elements['items'] = elements['items'][:3]
    elements['characters'] = elements['characters'][:3]
    elements['obstacles'] = elements['obstacles'][:3]

    return elements


def calculate_pddl_constraints(length: str) -> Dict[str, Dict[str, int]]:
    """
    Calcola i vincoli PDDL in base alla lunghezza scelta.
    """
    constraints = {
        "Short (2-5 min)": {
            "branching_min": 2,
            "branching_max": 3,
            "depth_min": 4,
            "depth_max": 6
        },
        "Medium (5-10 min)": {
            "branching_min": 2,
            "branching_max": 4,
            "depth_min": 6,
            "depth_max": 10
        },
        "Long (10+ min)": {
            "branching_min": 3,
            "branching_max": 5,
            "depth_min": 10,
            "depth_max": 15
        }
    }

    return constraints.get(length, constraints["Medium (5-10 min)"])


def format_lore_document(elements: Dict[str, Any]) -> str:
    """
    Formatta il documento Lore in modo strutturato e leggibile.
    """
    config = elements['config']
    pddl = calculate_pddl_constraints(config.get('length', 'Medium (5-10 min)'))

    doc = f"""# {elements['title']}

## 1. Mission Description
{elements['mission']}

## 2. Setting and Context

### Key Locations:
{chr(10).join(f"- {loc}" for loc in elements['locations'])}

### Key Items:
{chr(10).join(f"- {item}" for item in elements['items'])}

### Characters:
{chr(10).join(f"- {char}" for char in elements['characters'])}

## 3. Initial State and Objective

**Initial State:** 
The protagonist begins at {elements['locations'][0] if elements['locations'] else 'the starting location'}, 
with no items in their inventory. The path forward is blocked by various obstacles.

**Mission Objective:** 
Complete the quest by overcoming all obstacles, solving the central puzzle, 
and reaching {elements['locations'][-1] if elements['locations'] else 'the final destination'}.

## 4. Obstacles and Progress Conditions

{chr(10).join(f"**Obstacle {i + 1}:** {obs}" for i, obs in enumerate(elements['obstacles']))}

**Crucial Progression (Puzzle):** 
{elements['puzzle']}

## 5. Technical Constraints (PDDL)

### Suggested Actions:
- move(from, to) - Navigate between locations
- take(item) - Pick up an item
- use(item, location) - Use an item at a specific location
- disable(obstacle) - Remove or bypass an obstacle
- solve(puzzle) - Complete a puzzle or challenge

### Branching Factor (Decision complexity):
- min = {pddl['branching_min']}
- max = {pddl['branching_max']}

### Depth Constraints (Quest duration):
- min = {pddl['depth_min']}
- max = {pddl['depth_max']}

## 6. Configuration Summary

- **Genre:** {config.get('genre', 'N/A')}
- **Length:** {config.get('length', 'N/A')}
- **Tone:** {config.get('tone', 'N/A')}
- **Graphics:** {config.get('graphics', 'N/A')}
- **Theme:** {config.get('theme', 'N/A')}

## 7. Logical Representation (for PDDL)

### Initial State:
- (at protagonist {elements['locations'][0].lower().replace(' ', '_') if elements['locations'] else 'start'})
- (path-clear {elements['locations'][0].lower().replace(' ', '_') if elements['locations'] else 'start'} {elements['locations'][1].lower().replace(' ', '_') if len(elements['locations']) > 1 else 'location2'})
{chr(10).join(f"- (exists {item.split('(')[0].strip().lower().replace(' ', '_')})" for item in elements['items'][:3])}

### Goal State:
- (at protagonist {elements['locations'][-1].lower().replace(' ', '_') if elements['locations'] else 'end'})
- (puzzle-solved)
- (quest-complete)

## 8. Object Mappings

### Locations:
{chr(10).join(f"- {loc.lower().replace(' ', '_')}" for loc in elements['locations'])}

### Items:
{chr(10).join(f"- {item.split('(')[0].strip().lower().replace(' ', '_')}" for item in elements['items'])}

### Characters:
{chr(10).join(f"- {char.split('(')[0].strip().lower().replace(' ', '_')}" for char in elements['characters'])}

"""
    return doc


def generate_lore_document(config: Dict[str, Any]) -> str:
    """
    Genera un Lore Document completo a partire dalla configurazione.
    Restituisce il path assoluto del file generato.

    Args:
        config: Dizionario con genre, length, tone, graphics, theme

    Returns:
        Path assoluto del file generato, o None in caso di errore
    """
    logger.info(f"Generazione Lore Document per configurazione: {config}")

    # Genera elementi narrativi
    elements = generate_story_elements(config)

    if not elements:
        logger.error("Impossibile generare elementi della storia")
        # Fallback con template generico
        elements = {
            "title": f"The {config.get('genre', 'Mystery')} Quest",
            "mission": config.get('theme', 'An epic adventure awaits'),
            "locations": ["Starting Point", "Mysterious Place", "Dangerous Zone", "Final Destination"],
            "items": ["Key Item", "Power Source", "Ancient Artifact"],
            "characters": ["Hero", "Villain", "Guide"],
            "obstacles": ["First Challenge", "Second Trial", "Final Test"],
            "puzzle": "A mystery that must be solved to progress",
            "config": config
        }

    # Formatta il documento
    lore_text = format_lore_document(elements)

    # Salva il file
    output_dir = "Generated_Lore"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"Lore.txt"

    file_path = os.path.join(output_dir, filename)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(lore_text)

        abs_path = os.path.abspath(file_path)
        logger.info(f"✅ Lore document salvato in: {abs_path}")
        return abs_path

    except Exception as e:
        logger.error(f"Errore nel salvataggio del file: {e}")
        return None


# Test della funzione (opzionale)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_config = {
        "genre": "Dark Fantasy",
        "length": "Medium (5-10 min)",
        "tone": "Dark and Mysterious",
        "graphics": "Illustrated",
        "theme": "A cursed knight must break an ancient spell"
    }

    result = generate_lore_document(test_config)
    if result:
        print(f"\n✅ Documento generato: {result}")
        with open(result, 'r', encoding='utf-8') as f:
            print("\n--- CONTENUTO ---")
            print(f.read())
    else:
        print("\n❌ Errore nella generazione")