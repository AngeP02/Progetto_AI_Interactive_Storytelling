import os
import requests
import logging
import json
import re
from typing import Dict, Any, List, Tuple

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
                "num_predict": max_tokens,
                "num_ctx": 4096
            }
        }

        logger.info(f"Chiamata Ollama in corso... (timeout: 180s)")
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()

    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout nella chiamata Ollama - prova ad aumentare il timeout o semplificare il prompt")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("❌ Impossibile connettersi a Ollama - verifica che sia in esecuzione (ollama serve)")
        return None
    except Exception as e:
        logger.error(f"❌ Errore chiamata Ollama: {e}")
        return None


def generate_story_elements(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera gli elementi LOGICI della quest in formato strutturato.
    Approccio: pensare come un game designer sistemico, non come uno scrittore.
    """
    genre = config.get("genre", "Fantasy")
    theme = config.get("theme", "An adventure full of mystery")
    tone = config.get("tone", "Neutral")
    length = config.get("length", "Medium (5-10 min)")

    # Calcola i vincoli PDDL
    pddl = calculate_pddl_constraints(length)

    system_prompt = """You are a game logic designer. Create quest systems as simple state machines.
Focus on: locations, connections, items, and conditions. Be brief and structured."""

    prompt = f"""Design a LOGICAL QUEST SYSTEM with these parameters:
Genre: {genre}
Theme: {theme}
Target: {pddl['depth_min']}-{pddl['depth_max']} steps

CRITICAL: Follow this EXACT format. Use underscores for all names (no spaces, no numbers as standalone item names).

1. TITLE: [Quest name in 5-8 words]

2. MISSION: [One sentence goal describing what to collect/defeat/reach]

3. LOCATIONS & CONNECTIONS:
start -> forest_path (requires: none)
forest_path -> dark_cave (requires: has_torch)
dark_cave -> ancient_castle (requires: key_found AND guardian_defeated)
ancient_castle -> treasure_vault (requires: puzzle_solved)

4. ITEMS:
torch (at: start, needs: none, unlocks: can_enter_cave)
silver_key (at: forest_path, needs: has_torch, unlocks: castle_door)
magic_sword (at: dark_cave, needs: silver_key, unlocks: can_fight)
golden_artifact (at: ancient_castle, needs: magic_sword, unlocks: quest_complete)

5. OBSTACLES:
locked_gate (blocks: start->forest_path, needs: iron_key, effect: gate_opened)
cave_guardian (blocks: forest_path->dark_cave, needs: magic_sword, effect: guardian_defeated)
puzzle_door (blocks: dark_cave->ancient_castle, needs: crystal_orb, effect: puzzle_solved)

6. DEPENDENCIES:
BEFORE enter_castle: need (silver_key AND guardian_defeated)
BEFORE get_artifact: need (puzzle_solved AND magic_sword)

7. WIN CONDITION: at_treasure_vault AND has_golden_artifact AND quest_complete

STRICT RULES:
- Use ONLY underscores in names (forest_path NOT "forest path")
- NO numbers as item names (use: ancient_key NOT key1)
- Every item MUST have: at, needs, unlocks
- Every obstacle MUST have: blocks, needs, effect
- Be specific, NEVER use "none" or "unknown" in at/found_at fields
- Provide {pddl['depth_min']}-{pddl['depth_max']} meaningful items and obstacles
"""

    response = call_ollama(prompt, system_prompt, max_tokens=1500, temperature=0.6)

    if not response:
        logger.error("Failed to generate story elements")
        return None

    # Parse la risposta
    return parse_logical_elements(response, config)


def parse_logical_elements(response: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estrae gli elementi LOGICI dalla risposta dell'LLM.
    Focus su connessioni, prerequisiti, effetti.
    """
    elements = {
        "title": "Untitled Quest",
        "mission": "",
        "locations": [],
        "connections": [],
        "items": [],
        "item_logic": [],
        "obstacles": [],
        "obstacle_logic": [],
        "dependencies": [],
        "win_condition": "",
        "config": config
    }

    lines = response.split('\n')
    current_section = None

    logger.info("🔍 Inizio parsing risposta LLM...")

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        upper_line = line.upper()

        # Identifica sezioni
        if 'TITLE' in upper_line and ':' in line:
            title_text = line.split(':', 1)[1].strip().strip('"').strip('*')
            if title_text and title_text != "**":
                elements['title'] = title_text
            logger.info(f"📌 Title trovato: {elements['title']}")
            continue
        elif 'MISSION' in upper_line and ':' in line:
            current_section = 'mission'
            mission_text = line.split(':', 1)[1].strip().strip('*')
            if mission_text and mission_text != "**":
                elements['mission'] = mission_text
            continue
        elif 'LOCATION' in upper_line and 'CONNECTION' in upper_line:
            current_section = 'connections'
            logger.info("📍 Sezione CONNECTIONS attivata")
            continue
        elif 'ITEM' in upper_line and 'OBSTACLE' not in upper_line:
            current_section = 'items'
            logger.info("🎁 Sezione ITEMS attivata")
            continue
        elif 'OBSTACLE' in upper_line:
            current_section = 'obstacles'
            logger.info("🚧 Sezione OBSTACLES attivata")
            continue
        elif 'DEPENDENC' in upper_line:
            current_section = 'dependencies'
            logger.info("🔗 Sezione DEPENDENCIES attivata")
            continue
        elif 'WIN' in upper_line and 'CONDITION' in upper_line:
            current_section = 'win_condition'
            win_text = line.split(':', 1)[1].strip() if ':' in line else ''
            if win_text:
                elements['win_condition'] = win_text.strip('*')
            continue

        # Pulisci prefissi comuni
        if line.startswith('-'):
            line = line[1:].strip()
        if line.startswith('*'):
            line = line[1:].strip()

        # Parsing per sezione
        if current_section == 'mission' and line and not any(
                x in line.upper() for x in ['LOCATION', 'ITEM', 'OBSTACLE']):
            elements['mission'] += ' ' + line.strip('*')

        elif current_section == 'connections' and line and '->' in line:
            connection = parse_connection(line)
            if connection:
                elements['connections'].append(connection)
                if connection['from'] not in elements['locations']:
                    elements['locations'].append(connection['from'])
                if connection['to'] not in elements['locations']:
                    elements['locations'].append(connection['to'])
                logger.info(f"  ✓ Connection: {connection['from']} -> {connection['to']}")

        elif current_section == 'items' and line and '(' in line:
            item_logic = parse_item_logic(line)
            if item_logic:
                logger.info(f"  🔍 Item parsed: {item_logic}")
                elements['item_logic'].append(item_logic)
                if item_logic['item'] not in elements['items']:
                    elements['items'].append(item_logic['item'])
                logger.info(f"  ✓ Item: {item_logic['item']} at {item_logic['found_at']}")

        elif current_section == 'obstacles' and line and '(' in line:
            obstacle_logic = parse_obstacle_logic(line)
            if obstacle_logic:
                logger.info(f"  🔍 Obstacle parsed: {obstacle_logic}")
                elements['obstacle_logic'].append(obstacle_logic)
                if obstacle_logic['obstacle'] not in elements['obstacles']:
                    elements['obstacles'].append(obstacle_logic['obstacle'])
                logger.info(f"  ✓ Obstacle: {obstacle_logic['obstacle']}")

        elif current_section == 'dependencies' and line and 'before' in line.lower():
            dep = parse_dependency(line)
            if dep:
                elements['dependencies'].append(dep)
                logger.info(f"  ✓ Dependency: {dep['before']}")

        elif current_section == 'win_condition' and line and not any(
                x in line.upper() for x in ['TITLE', 'MISSION', 'LOCATION']):
            elements['win_condition'] += ' ' + line.strip('*')

    # Pulizia finale
    elements['mission'] = elements['mission'].strip()
    elements['win_condition'] = elements['win_condition'].strip()

    # Validazione e correzione
    elements = validate_and_fix_elements(elements)

    logger.info(
        f"📊 Parsed: {len(elements['locations'])} locations, {len(elements['items'])} items, {len(elements['obstacles'])} obstacles")

    # Fallback SOLO se necessario
    if not elements['locations'] or not elements['connections']:
        logger.warning("⚠️ Dati insufficienti, uso fallback per locations")
        elements = apply_fallback_structure(elements)

    logger.info("✅ Parsing completato e validato")
    return elements


def parse_connection(line: str) -> Dict[str, str]:
    """Parsing connessioni migliorato"""
    # Pattern principale: loc1 -> loc2 (requires: cond)
    match = re.search(
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*?(?:requires|needs)[:\s]+([^)]+)\)',
        line, re.IGNORECASE)
    if match:
        return {
            "from": match.group(1).strip(),
            "to": match.group(2).strip(),
            "requires": match.group(3).strip()
        }

    # Fallback: loc1 -> loc2 (senza condizioni)
    simple_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*([a-zA-Z_][a-zA-Z0-9_]*)', line)
    if simple_match:
        return {
            "from": simple_match.group(1).strip(),
            "to": simple_match.group(2).strip(),
            "requires": "none"
        }

    return None


def parse_item_logic(line: str) -> Dict[str, str]:
    """Estrae logica item con parsing più robusto"""
    # Rimuovi prefissi comuni
    line = line.lstrip('- *')

    # Cerca pattern: nome_item (at: loc, needs: cond, unlocks: effect)
    item_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', line)
    if not item_match:
        return None

    item_name = item_match.group(1)

    # Estrai campi con pattern più flessibili
    found_at = extract_field_flexible(line, ['at', 'found_at', 'location'], 'start')
    requires = extract_field_flexible(line, ['needs', 'requires', 'requirement'], 'none')
    effect = extract_field_flexible(line, ['unlocks', 'effect', 'grants'], item_name + '_obtained')

    return {
        "item": item_name,
        "found_at": found_at,
        "requires": requires,
        "effect": effect
    }


def parse_obstacle_logic(line: str) -> Dict[str, str]:
    """Estrae logica obstacle con parsing più robusto"""
    line = line.lstrip('- *')

    obstacle_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', line)
    if not obstacle_match:
        return None

    obstacle_name = obstacle_match.group(1)

    blocks = extract_field_flexible(line, ['blocks', 'blocking'], 'path')
    requires = extract_field_flexible(line, ['needs', 'requires'], obstacle_name + '_key')
    effect = extract_field_flexible(line, ['effect', 'result'], obstacle_name + '_cleared')

    return {
        "obstacle": obstacle_name,
        "blocks": blocks,
        "requires": requires,
        "effect": effect
    }


def parse_dependency(line: str) -> Dict[str, str]:
    """Estrae dipendenza: BEFORE X: need/must_have (...)"""
    match = re.search(r'BEFORE\s+(\w+).*?(?:need|must[_\s]have)\s*\(([^)]+)\)', line, re.IGNORECASE)
    if match:
        return {
            "before": match.group(1).strip(),
            "requires": match.group(2).strip()
        }
    # Fallback generico
    if 'before' in line.lower() and ':' in line:
        parts = line.split(':', 1)
        return {
            "before": parts[0].replace('BEFORE', '').replace('before', '').strip(),
            "requires": parts[1].strip()
        }
    return None


def extract_field_flexible(line: str, field_names: List[str], default: str = "") -> str:
    """Estrae valore di un campo con multiple varianti di nomi"""
    for field_name in field_names:
        # Cerca pattern: field_name: valore o field_name valore
        pattern = f'{field_name}[:\\s]+([^,)]+)'
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Pulisci valori problematici
            if value.lower() in ['none', 'n/a', 'null', '', 'unknown']:
                continue
            return value
    return default


def validate_and_fix_elements(elements: Dict[str, Any]) -> Dict[str, Any]:
    """Valida e corregge elementi problematici"""

    # Rimuovi items con nomi numerici o troppo corti
    elements['items'] = [item for item in elements['items']
                         if not item.isdigit() and len(item) > 1]

    # Correggi item_logic con valori invalidi
    valid_item_logic = []
    for item in elements['item_logic']:
        # Skip items con nomi numerici
        if item['item'].isdigit() or len(item['item']) <= 1:
            logger.warning(f"⚠️ Skipping invalid item name: {item['item']}")
            continue

        # Correggi found_at invalido
        if item['found_at'] in ['unknown', 'none', '', 'n/a']:
            item['found_at'] = elements['locations'][0] if elements['locations'] else 'start'
            logger.info(f"  🔧 Fixed found_at for {item['item']}: {item['found_at']}")

        # Correggi effect invalido
        if item['effect'] in ['none', '', 'n/a']:
            item['effect'] = f"{item['item']}_obtained"
            logger.info(f"  🔧 Fixed effect for {item['item']}: {item['effect']}")

        valid_item_logic.append(item)

    elements['item_logic'] = valid_item_logic
    elements['items'] = [item['item'] for item in valid_item_logic]

    # Correggi obstacle_logic
    valid_obstacle_logic = []
    for obs in elements['obstacle_logic']:
        # Skip obstacles con nomi numerici
        if obs['obstacle'].isdigit() or len(obs['obstacle']) <= 1:
            logger.warning(f"⚠️ Skipping invalid obstacle name: {obs['obstacle']}")
            continue

        # Correggi blocks invalido
        if obs['blocks'] in ['unknown', 'none', '', 'n/a']:
            obs['blocks'] = 'path'
            logger.info(f"  🔧 Fixed blocks for {obs['obstacle']}: {obs['blocks']}")

        # Correggi effect invalido
        if obs['effect'] in ['none', '', 'n/a']:
            obs['effect'] = f"{obs['obstacle']}_cleared"
            logger.info(f"  🔧 Fixed effect for {obs['obstacle']}: {obs['effect']}")

        valid_obstacle_logic.append(obs)

    elements['obstacle_logic'] = valid_obstacle_logic
    elements['obstacles'] = [obs['obstacle'] for obs in valid_obstacle_logic]

    return elements


def apply_fallback_structure(elements: Dict[str, Any]) -> Dict[str, Any]:
    """Applica una struttura di fallback valida"""
    logger.warning("⚠️ Applicazione struttura di fallback")

    if not elements['locations']:
        elements['locations'] = ["start", "forest_path", "dark_cave", "ancient_castle", "goal"]

    if not elements['connections']:
        locs = elements['locations']
        elements['connections'] = [
            {"from": locs[0], "to": locs[1], "requires": "none"},
            {"from": locs[1], "to": locs[2], "requires": "has_torch"},
            {"from": locs[2], "to": locs[3], "requires": "key_found"},
            {"from": locs[3], "to": locs[-1], "requires": "puzzle_solved"}
        ]

    if not elements['item_logic']:
        locs = elements['locations']
        elements['items'] = ["torch", "silver_key", "magic_sword", "golden_artifact"]
        elements['item_logic'] = [
            {"item": "torch", "found_at": locs[0], "requires": "none", "effect": "can_explore"},
            {"item": "silver_key", "found_at": locs[1], "requires": "has_torch", "effect": "key_found"},
            {"item": "magic_sword", "found_at": locs[2], "requires": "key_found", "effect": "can_fight"},
            {"item": "golden_artifact", "found_at": locs[3], "requires": "puzzle_solved", "effect": "quest_complete"}
        ]

    if not elements['obstacle_logic']:
        locs = elements['locations']
        elements['obstacles'] = ["locked_gate", "cave_guardian", "puzzle_door"]
        elements['obstacle_logic'] = [
            {"obstacle": "locked_gate", "blocks": f"{locs[0]}->{locs[1]}", "requires": "iron_key",
             "effect": "gate_opened"},
            {"obstacle": "cave_guardian", "blocks": f"{locs[1]}->{locs[2]}", "requires": "magic_sword",
             "effect": "guardian_defeated"},
            {"obstacle": "puzzle_door", "blocks": f"{locs[2]}->{locs[3]}", "requires": "silver_key",
             "effect": "puzzle_solved"}
        ]

    if not elements['win_condition']:
        elements[
            'win_condition'] = f"at_location({elements['locations'][-1]}) AND has_golden_artifact AND quest_complete"

    return elements


def calculate_pddl_constraints(length: str) -> Dict[str, int]:
    """Calcola i vincoli PDDL in base alla lunghezza scelta."""
    constraints = {
        "Short (2-5 min)": {
            "branching_min": 2,
            "branching_max": 4,
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
    """Formatta il documento Lore in formato logico-strutturale per PDDL."""
    config = elements['config']
    pddl = calculate_pddl_constraints(config.get('length', 'Medium (5-10 min)'))

    doc = f"""# {elements['title']}

## 1. Mission Objective (Logical)
{elements['mission']}

## 2. World Structure

### Locations (Nodes):
{chr(10).join(f"- {loc}" for loc in elements['locations'])}

### Location Connections (Edges):
{chr(10).join(f"- {conn['from']} -> {conn['to']} (requires: {conn['requires']})" for conn in elements['connections'])}

## 3. Items & Acquisition Logic

{chr(10).join(f"**{item['item']}**{chr(10)}  - Found at: {item['found_at']}{chr(10)}  - Requires: {item['requires']}{chr(10)}  - Effect: {item['effect']}" for item in elements['item_logic'])}

## 4. Obstacles & Bypass Conditions

{chr(10).join(f"**{obs['obstacle']}**{chr(10)}  - Blocks: {obs['blocks']}{chr(10)}  - Requires to overcome: {obs['requires']}{chr(10)}  - Effect when solved: {obs['effect']}" for obs in elements['obstacle_logic'])}

## 5. Causal Dependency Chain

{chr(10).join(f"- BEFORE {dep['before']}: must have ({dep['requires']})" for dep in elements['dependencies']) if elements['dependencies'] else "- Linear progression with item-based gates"}

## 6. Win Condition
```
{elements['win_condition']}
```

## 7. PDDL Mapping

### Domain Actions:
- move(from, to) - Navigate between connected locations (requires: path conditions met)
- take(item, location) - Pick up an item (requires: at location, item available)
- use(item, target) - Use an item on obstacle/puzzle (requires: has item)
- solve(obstacle) - Overcome obstacle (requires: necessary items/conditions)

### Initial State (PDDL):
```
(at protagonist {elements['locations'][0]})
{chr(10).join(f"(connected {conn['from']} {conn['to']})" for conn in elements['connections'])}
{chr(10).join(f"(item-at {item['item']} {item['found_at']})" for item in elements['item_logic'])}
{chr(10).join(f"(blocks {obs['obstacle']} {obs['blocks'].split('->')[0].strip() if '->' in obs['blocks'] else 'path'})" for obs in elements['obstacle_logic'])}
```

### Goal State (PDDL):
```
(at protagonist {elements['locations'][-1]})
{chr(10).join(f"(has {item['item']})" for item in elements['item_logic'] if 'complete' in item['effect'] or 'final' in item['effect'] or 'artifact' in item['item'])}
(quest-complete)
```

## 8. Technical Constraints

- **Branching Factor:** {pddl['branching_min']}-{pddl['branching_max']} choices per decision point
- **Quest Depth:** {pddl['depth_min']}-{pddl['depth_max']} steps minimum to complete
- **Genre:** {config.get('genre', 'N/A')}
- **Tone:** {config.get('tone', 'N/A')}
- **Target Duration:** {config.get('length', 'N/A')}

## 9. State Transition Graph
```
{elements['locations'][0]} (START)
  |
  v (requires: {elements['connections'][0]['requires'] if elements['connections'] else 'none'})
{elements['locations'][1] if len(elements['locations']) > 1 else 'location_1'}
  |
  v (requires: items + obstacle solutions)
  ...
  |
  v
{elements['locations'][-1]} (GOAL)
```

## 10. Object Definitions (for PDDL)

### Types:
- location: {', '.join(elements['locations'])}
- item: {', '.join(elements['items'])}
- obstacle: {', '.join(elements['obstacles'])}
- character: protagonist

### Predicates:
- (at ?character ?location)
- (connected ?loc1 ?loc2)
- (has ?item)
- (item-at ?item ?location)
- (obstacle-active ?obstacle)
- (obstacle-solved ?obstacle)
- (blocks ?obstacle ?location)
- (requires-item ?obstacle ?item)
"""
    return doc


def generate_lore_document(config: Dict[str, Any]) -> str:
    """
    Genera un Lore Document LOGICO-STRUTTURALE per PDDL.

    Args:
        config: Dizionario con genre, length, tone, graphics, theme

    Returns:
        Path assoluto del file generato, o None in caso di errore
    """
    logger.info(f"Generazione Lore Document (logico) per configurazione: {config}")

    # Genera elementi LOGICI
    elements = generate_story_elements(config)

    if not elements:
        logger.error("Impossibile generare elementi della storia")
        return None

    # Formatta il documento
    lore_text = format_lore_document(elements)

    # Salva il file
    output_dir = "Generated_Lore"
    os.makedirs(output_dir, exist_ok=True)

    filename = "Lore_Logical.txt"
    file_path = os.path.join(output_dir, filename)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(lore_text)

        abs_path = os.path.abspath(file_path)
        logger.info(f"✅ Lore document (logico) salvato in: {abs_path}")
        return abs_path

    except Exception as e:
        logger.error(f"Errore nel salvataggio del file: {e}")
        return None


# Test della funzione
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