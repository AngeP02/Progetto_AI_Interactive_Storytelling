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

from collections import deque
from typing import Tuple, List, Set, Dict

def validate_lore_solvability(elements: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Simula il world logic e verifica se esiste un percorso dallo start al goal
    soddisfacendo requisiti (keys, items, obstacle effects).
    Ritorna (is_solvable, list_of_failure_reasons).
    Assunzioni su elements:
      - elements['locations']: list of names
      - elements['connections']: list of {from,to,requires}
      - elements['item_logic']: list of {item,found_at,requires,effect}
      - elements['obstacle_logic']: list of {obstacle,blocks,requires,effect}
      - elements['win_condition']: testo (si accetta che contenga 'treasure' o 'golden_artifact' etc)
    """
    # Preprocessing: index maps
    locs = elements.get('locations', [])
    conns = elements.get('connections', [])
    items = {it['item']: it for it in elements.get('item_logic', [])}
    obstacles = {obs['obstacle']: obs for obs in elements.get('obstacle_logic', [])}
    start = locs[0] if locs else "start"
    goal_loc = locs[-1] if locs else "goal"

    # Build adjacency with requirement sets (requires is string; normalize to set of tokens)
    adj: Dict[str, List[Tuple[str, Set[str]]]] = {}
    for c in conns:
        fr, to = c['from'], c['to']
        req = c.get('requires', 'none')
        # break multiple requirements by AND/AND/space/commas
        req_tokens = set([s.strip() for s in re.split(r'\band\b|,|AND| ', req) if s.strip() and s.strip().lower() != 'none'])
        adj.setdefault(fr, []).append((to, req_tokens))
        # try add reverse if not present (your generator often creates explicit both)
        # don't assume symmetric unless provided; but we can add symmetrical edge if no explicit reverse present
        if not any(x for x in conns if x['from'] == to and x['to'] == fr):
            adj.setdefault(to, []).append((fr, set()))

    # Map item positions
    item_at = {it['item']: it['found_at'] for it in elements.get('item_logic', [])}

    # Map obstacles blocking edges -> blocks field often like 'locA->locB'
    edge_blockers: Dict[Tuple[str,str], Dict[str,str]] = {}
    for obs in elements.get('obstacle_logic', []):
        blocks = obs.get('blocks','')
        if '->' in blocks:
            a,b = [p.strip() for p in blocks.split('->')[:2]]
            edge_blockers[(a,b)] = {'obstacle': obs['obstacle'], 'requires': obs.get('requires'), 'effect': obs.get('effect')}
            # if bidirectional blocked, also block reverse
            edge_blockers[(b,a)] = {'obstacle': obs['obstacle'], 'requires': obs.get('requires'), 'effect': obs.get('effect')}

    # BFS over states: (loc, frozenset(has_items), frozenset(solved_obstacles))
    State = Tuple[str, frozenset, frozenset]
    init_items = frozenset()
    init_solved = frozenset()
    init_state: State = (start, init_items, init_solved)
    q = deque([init_state])
    seen: Set[State] = {init_state}

    # Helper: can traverse edge?
    def can_traverse(loc_from, loc_to, have_items:Set[str], solved:Set[str]) -> Tuple[bool,str]:
        # check blocker
        if (loc_from, loc_to) in edge_blockers:
            obs = edge_blockers[(loc_from, loc_to)]
            obs_req_raw = obs.get('requires','')
            reqs = set([s.strip() for s in re.split(r'\band\b|,|AND| ', obs_req_raw) if s.strip()])
            # if we already solved the obstacle, ok
            if obs['obstacle'] in solved:
                return True, ""
            # check if we have required items
            if reqs.issubset(have_items):
                return True, ""
            else:
                return False, f"edge_blocked_by_{obs['obstacle']}"
        # else check connection-level requirements (from adj list)
        for to, reqs in adj.get(loc_from, []):
            if to == loc_to:
                if reqs.issubset(have_items):
                    return True, ""
                else:
                    return False, f"missing_req_{','.join(reqs) if reqs else 'none'}"
        # no explicit connection -> can't move
        return False, "no_connection"

    failures = []

    # Main BFS
    while q:
        loc, have, solved = q.popleft()
        have_set = set(have)
        solved_set = set(solved)

        # check pickup of any item at location
        for itm, itm_loc in item_at.items():
            if itm_loc == loc and itm not in have_set:
                # check precondition 'requires' for picking item (e.g., needs: has_torch) -> for simplicity assume requires are item names
                itm_req_raw = items.get(itm, {}).get('requires', '')
                reqs = set([s.strip() for s in re.split(r'\band\b|,|AND| ', itm_req_raw) if s.strip() and s.strip().lower()!='none'])
                if reqs.issubset(have_set):
                    new_have = frozenset(set(have_set) | {itm})
                    new_state = (loc, new_have, frozenset(solved_set))
                    if new_state not in seen:
                        seen.add(new_state)
                        q.append(new_state)

        # try solve obstacles adjacent to this location (if obstacle requires some item to resolve and gives effect)
        for ((a,b), obsinfo) in list(edge_blockers.items()):
            if a == loc:
                obs_name = obsinfo['obstacle']
                if obs_name not in solved_set:
                    obs_reqs = set([s.strip() for s in re.split(r'\band\b|,|AND| ', obsinfo.get('requires','')) if s.strip()])
                    if obs_reqs.issubset(have_set):
                        new_solved = frozenset(solved_set | {obs_name})
                        new_state = (loc, frozenset(have_set), new_solved)
                        if new_state not in seen:
                            seen.add(new_state)
                            q.append(new_state)

        # move to neighbors
        for to, _ in adj.get(loc, []):
            can, reason = can_traverse(loc, to, have_set, solved_set)
            if can:
                new_state = (to, frozenset(have_set), frozenset(solved_set))
                if new_state not in seen:
                    seen.add(new_state)
                    q.append(new_state)
            else:
                # record a possible failure reason for debugging
                failures.append(f"blocked {loc}->{to} reason:{reason}")

        # check goal: protagonist at goal and some artifact possession if expected
        # check simple pattern: win_condition might mention item name or 'golden_artifact'
        win_text = (elements.get('win_condition') or "").lower()
        has_goal_item = False
        for it in have_set:
            if it in win_text or 'golden' in win_text and 'golden' in it:
                has_goal_item = True
        at_goal = (loc == goal_loc)
        need_artifact = ('golden' in win_text) or ('artifact' in win_text) or ('has_' in win_text)
        if at_goal and (not need_artifact or has_goal_item):
            return True, []

    # if BFS ended, not solvable; deduplicate failures
    fail_set = list(dict.fromkeys(failures))[:10]
    if not fail_set:
        fail_set = ["No path from start to goal found"]
    return False, fail_set


def fix_unresolvable_lore(lore_data):
    """
    Ripara una lore non risolvibile spostando items per eliminare dipendenze circolari.
    Strategia:
    1. Identifica tutti i path bloccati
    2. Sposta gli items necessari in posizioni raggiungibili
    3. Assicura che lo start abbia almeno un item base
    """
    locations = lore_data['locations']
    items = lore_data['items']
    obstacles = lore_data['obstacles']

    start_loc = locations[0]

    # Mappa item -> location
    item_locations = {item['item']: item['found_at'] for item in items}

    # Strategia 1: Sposta items necessari per sbloccare il primo ostacolo allo start
    for obs in obstacles:
        blocked_path = obs['blocks']
        required_item = obs['requires']

        if '->' not in blocked_path:
            continue

        from_loc, to_loc = [x.strip() for x in blocked_path.split('->')]

        # Se l'ostacolo blocca il primo movimento da start
        if from_loc == start_loc:
            if required_item in item_locations:
                current_loc = item_locations[required_item]

                # Se l'item è irraggiungibile, spostalo a start
                if current_loc != start_loc:
                    logger.info(
                        f"🔧 Sposto {required_item} da {current_loc} a {start_loc} per superare {obs['obstacle']}")

                    for item in items:
                        if item['item'] == required_item:
                            item['found_at'] = start_loc
                            item['requires'] = 'none'  # Rendilo immediatamente accessibile
                            item_locations[required_item] = start_loc

    # Strategia 2: Assicura progressione lineare - ogni item deve essere raggiungibile
    # prima di essere necessario per un ostacolo
    location_order = {loc: i for i, loc in enumerate(locations)}

    for obs in obstacles:
        blocked_path = obs['blocks']
        required_item = obs['requires']

        if '->' not in blocked_path or required_item not in item_locations:
            continue

        from_loc, to_loc = [x.strip() for x in blocked_path.split('->')]

        # L'item deve trovarsi in una location raggiungibile PRIMA del blocco
        item_loc = item_locations[required_item]

        # Se l'item è oltre l'ostacolo che richiede quell'item, spostalo prima
        if location_order.get(item_loc, 999) >= location_order.get(to_loc, 0):
            # Trova una location raggiungibile prima dell'ostacolo
            target_loc = from_loc

            logger.info(f"🔧 Sposto {required_item} da {item_loc} a {target_loc} per superare {obs['obstacle']}")

            for item in items:
                if item['item'] == required_item:
                    item['found_at'] = target_loc
                    # Rimuovi requisiti complessi per items critici
                    if target_loc == start_loc:
                        item['requires'] = 'none'
                    item_locations[required_item] = target_loc

    # Strategia 3: Assicura che ci sia almeno un item accessibile a start
    start_items = [item for item in items if item['found_at'] == start_loc]

    if not start_items:
        # Sposta il primo item disponibile a start
        if items:
            items[0]['found_at'] = start_loc
            items[0]['requires'] = 'none'
            logger.info(f"🔧 Sposto {items[0]['item']} a {start_loc} come item iniziale")

    return lore_data


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

    system_prompt = """You are a game logic designer. Create LINEAR quest systems where each step unlocks the next.
    GOLDEN RULE: Every item needed to pass an obstacle must be found BEFORE that obstacle."""

    prompt = f"""Design a LINEAR QUEST with {pddl['depth_min']}-{pddl['depth_max']} locations.

    Genre: {genre}
    Theme: {theme}

    ⚠️ CRITICAL RULES:
    1. Items must be placed BEFORE the obstacles that need them
    2. First location (start) must have at least 1 item with needs:none
    3. Each location should have exactly 1 item
    4. Each obstacle blocks the path to the NEXT location
    5. The item to pass an obstacle must be in the CURRENT or PREVIOUS location

    SIMPLE WORKING EXAMPLE:

    TITLE: The Lost Key Quest

    MISSION: Find the golden artifact in the treasure vault

    LOCATIONS & CONNECTIONS:
    start -> forest (requires: none)
    forest -> cave (requires: none)
    cave -> castle (requires: none)
    castle -> vault (requires: none)

    ITEMS:
    iron_key (at: start, needs: none, unlocks: forest_unlocked)
    torch (at: forest, needs: none, unlocks: cave_unlocked)
    silver_key (at: cave, needs: none, unlocks: castle_unlocked)
    golden_artifact (at: vault, needs: none, unlocks: quest_complete)

    OBSTACLES:
    locked_gate (blocks: start->forest, needs: iron_key, effect: forest_unlocked)
    dark_passage (blocks: forest->cave, needs: torch, effect: cave_unlocked)
    iron_door (blocks: cave->castle, needs: silver_key, effect: castle_unlocked)

    WIN CONDITION: has_golden_artifact

    ---

    NOW CREATE YOUR QUEST following this EXACT pattern:
    - {pddl['depth_min']}-{pddl['depth_max']} locations (including start and vault)
    - Place items BEFORE or AT the location of obstacles that need them
    - NEVER place an item after the obstacle that requires it
    - Keep it simple: one item per location, one obstacle per connection

    FORMAT (use EXACTLY this format):

    TITLE: [Your quest name]

    MISSION: [One sentence]

    LOCATIONS & CONNECTIONS:
    [location1] -> [location2] (requires: none)
    [location2] -> [location3] (requires: none)
    ...

    ITEMS:
    [item_name] (at: [location], needs: none, unlocks: [effect])
    ...

    OBSTACLES:
    [obstacle_name] (blocks: [loc1]->[loc2], needs: [item], effect: [effect])
    ...

    WIN CONDITION: has_[final_item]
    """

    if config.get("reflection_feedback"):
        prompt += "\n\nFEEDBACK:\n" + config["reflection_feedback"]

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
        if obs['blocks'].startswith('start') and obs['requires'] not in [itm['item'] for itm in elements['item_logic'] if itm['found_at'] == 'start']:
            # Sposta l'item necessario all'inizio
            for itm in elements['item_logic']:
                if itm['item'] == obs['requires']:
                    itm['found_at'] = elements['locations'][0]  # start
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


def fix_and_validate_lore(elements: Dict[str, Any], max_fix_attempts: int = 3) -> Tuple[
    bool, List[str], Dict[str, Any]]:
    """
    Tenta di riparare e validare la lore iterativamente.
    Ritorna: (is_solvable, reasons, fixed_elements)
    """

    for fix_attempt in range(max_fix_attempts):
        logger.info(f"🔧 Tentativo di fix #{fix_attempt + 1}")

        # Valida prima
        solvable, reasons = validate_lore_solvability(elements)

        if solvable:
            logger.info("✅ Lore risolvibile!")
            return True, [], elements

        logger.warning(f"⚠️ Problemi rilevati: {reasons}")

        # Analizza i problemi e applica fix specifici
        elements = apply_targeted_fixes(elements, reasons)

    # Ultimo tentativo di validazione
    solvable, reasons = validate_lore_solvability(elements)
    return solvable, reasons, elements


def apply_targeted_fixes(elements: Dict[str, Any], reasons: List[str]) -> Dict[str, Any]:
    """
    Applica fix specifici basati sui problemi rilevati.
    """
    locations = elements['locations']
    start_loc = locations[0] if locations else 'start'

    # Mappa item -> posizione
    item_map = {item['item']: item for item in elements['item_logic']}

    # Analizza ogni problema
    for reason in reasons:
        logger.info(f"  🔍 Analizzo: {reason}")

        # Pattern: "blocked A->B reason:edge_blocked_by_OBSTACLE"
        if 'edge_blocked_by_' in reason:
            match = re.search(r'blocked\s+(\S+)->(\S+)\s+reason:edge_blocked_by_(\w+)', reason)
            if match:
                from_loc, to_loc, obstacle_name = match.groups()

                # Trova l'ostacolo
                obstacle = next((obs for obs in elements['obstacle_logic']
                                 if obs['obstacle'] == obstacle_name), None)

                if obstacle:
                    required_item = obstacle.get('requires', '')

                    # Se l'item richiesto esiste, spostalo in una posizione accessibile
                    if required_item in item_map:
                        current_loc = item_map[required_item]['found_at']

                        # Determina dove spostarlo
                        # Se il blocco è da start, metti l'item a start
                        if from_loc == start_loc:
                            target_loc = start_loc
                        else:
                            # Altrimenti metti nella location di partenza del blocco
                            target_loc = from_loc

                        if current_loc != target_loc:
                            logger.info(f"    ✏️ Sposto {required_item}: {current_loc} → {target_loc}")
                            item_map[required_item]['found_at'] = target_loc
                            item_map[required_item]['requires'] = 'none'  # Rendilo accessibile

        # Pattern: "blocked A->B reason:missing_req_CONDITION"
        elif 'missing_req_' in reason:
            match = re.search(r'blocked\s+(\S+)->(\S+)\s+reason:missing_req_(\S+)', reason)
            if match:
                from_loc, to_loc, required_condition = match.groups()

                # Cerca l'item che fornisce questa condizione
                providing_item = None
                for item in elements['item_logic']:
                    effect = item.get('effect', '')
                    # Se l'effect contiene la condizione richiesta
                    if required_condition in effect or required_condition.replace('has_', '') == item['item']:
                        providing_item = item
                        break

                if providing_item:
                    current_loc = providing_item['found_at']
                    # Sposta l'item in una location precedente nel path
                    try:
                        from_idx = locations.index(from_loc)
                        # Metti nella location precedente o a start
                        target_loc = locations[max(0, from_idx - 1)]
                    except ValueError:
                        target_loc = start_loc

                    if current_loc != target_loc:
                        logger.info(f"    ✏️ Sposto {providing_item['item']}: {current_loc} → {target_loc}")
                        providing_item['found_at'] = target_loc
                        providing_item['requires'] = 'none'

    return elements


def generate_lore_document(config: Dict[str, Any]) -> str:
    """
    Genera un Lore Document LOGICO-STRUTTURALE per PDDL.
    Versione corretta con fix integrato.
    """
    logger.info(f"Generazione Lore Document (logico) per configurazione: {config}")

    attempt = 0
    max_attempts = config.get("max_attempts", 5)
    elements = None
    solvable = False

    while attempt < max_attempts:
        attempt += 1
        logger.info(f"--- Tentativo {attempt} di generazione lore ---")

        # Genera elementi iniziali
        elements = generate_story_elements(config)
        if not elements:
            logger.warning("❌ Nessun elemento generato, ritento...")
            continue

        # ⭐ FIX INTEGRATO: Tenta di riparare e validare
        solvable, reasons, elements = fix_and_validate_lore(elements, max_fix_attempts=3)

        if solvable:
            logger.info("✅ Lore risultante risolvibile!")
            break
        else:
            # Genera feedback per il prossimo tentativo
            feedback = (
                f"The generated quest was not solvable. Problems found:\n"
                f"{chr(10).join('- ' + r for r in reasons[:5])}\n\n"
                f"CRITICAL RULES TO FIX THIS:\n"
                f"1. If obstacle blocks 'start->X' and needs 'item_Y', place item_Y AT START\n"
                f"2. Items must be placed BEFORE the obstacles that require them\n"
                f"3. Never create circular dependencies\n"
                f"4. First location should have at least one item with requires:'none'\n"
                f"\nRegenerate following these rules strictly."
            )
            logger.warning(f"⚠️ Lore NON risolvibile dopo fix. Reasons:\n{chr(10).join(reasons)}")
            config["reflection_feedback"] = feedback

    if not solvable:
        logger.error("❌ Impossibile generare un lore risolvibile dopo tutti i tentativi")
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
# ================= REFLECTION LOOP + VALIDAZIONE =================




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