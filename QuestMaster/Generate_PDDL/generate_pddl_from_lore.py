import os
import re
import requests
from pathlib import Path
import subprocess

# ========== CONFIGURAZIONE ==========
MODEL_NAME = "llama3"
OUTPUT_DIR = Path("Generated_PDDL")
OUTPUT_DIR.mkdir(exist_ok=True)
OLLAMA_URL = "http://localhost:11434/api/generate"


# ========== PARSING DEL LORE ==========
def parse_lore_document(lore_text):
    branching = re.findall(r"Branching Factor.*?(\d+).*?(\d+)", lore_text, re.S)
    branching_min, branching_max = map(int, branching[0]) if branching else (2, 4)

    depth = re.findall(r"Depth Constraints.*?(\d+).*?(\d+)", lore_text, re.S)
    depth_min, depth_max = map(int, depth[0]) if depth else (5, 10)

    entities = {}
    entities["characters"] = list(set(re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", lore_text)))
    entities["locations"] = list(set(re.findall(r"(?:in|at|on|within)\s+([A-Z][a-zA-Z\s]+)", lore_text)))
    entities["objects"] = list(set(re.findall(r"\b(?:code|device|artifact|weapon|system|file|key)\b", lore_text, re.I)))

    return {
        "branching_min": branching_min,
        "branching_max": branching_max,
        "depth_min": depth_min,
        "depth_max": depth_max,
        "entities": entities
    }


# ========== FUNZIONE REST API ==========
def call_ollama(prompt, system_prompt="", temperature=0.7, num_predict=500):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=500)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        return ""


# ========== NORMALIZZAZIONE ==========
def normalize_name(name):
    name = re.sub(r'[^a-zA-Z0-9]+', '_', str(name))
    name = name.strip('_').lower()
    if name and not name[0].isalpha():
        name = 'e_' + name
    return name if len(name) >= 2 else None


def get_normalized_entities(lore_data):
    common_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but',
                    'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does'}

    chars_set = set()
    for c in lore_data['entities']['characters']:
        if c.lower() not in common_words and len(c) >= 3:
            normalized = normalize_name(c)
            if normalized:
                chars_set.add(normalized)
        if len(chars_set) >= 3:
            break
    chars = list(chars_set)[:3]
    if len(chars) < 2:
        chars.extend(['hero', 'villain'][:2 - len(chars)])

    locs_set = set()
    for l in lore_data['entities'].get('locations', []):
        normalized = normalize_name(l)
        if normalized:
            locs_set.add(normalized)
        if len(locs_set) >= 5:
            break
    locs = list(locs_set)[:5]
    if len(locs) < 3:
        defaults = ['entrance', 'corridor', 'chamber', 'vault', 'exit']
        for default in defaults:
            if default not in locs:
                locs.append(default)
            if len(locs) >= 5:
                break

    objs_set = set()
    for o in lore_data['entities'].get('objects', []):
        normalized = normalize_name(o)
        if normalized:
            objs_set.add(normalized)
        if len(objs_set) >= 3:
            break
    objs = list(objs_set)[:3]
    if len(objs) < 2:
        defaults = ['key', 'artifact', 'tool']
        for default in defaults:
            if default not in objs:
                objs.append(default)
            if len(objs) >= 3:
                break

    return chars, locs, objs


# ========== ANALISI PDDL GENERATO ==========
def extract_entities_from_pddl(problem_content):
    """Estrae entità dichiarate nel problem PDDL"""
    entities = {'characters': [], 'locations': [], 'objects': []}

    # Trova sezione :objects
    objects_match = re.search(r'\(:objects\s+(.*?)\)', problem_content, re.DOTALL)
    if not objects_match:
        return entities

    objects_section = objects_match.group(1)

    # Estrai per tipo
    for line in objects_section.split('\n'):
        line = line.strip()
        if '- character' in line:
            entities['characters'] = [w for w in line.split() if w not in ['-', 'character']]
        elif '- location' in line:
            entities['locations'] = [w for w in line.split() if w not in ['-', 'location']]
        elif '- object' in line:
            entities['objects'] = [w for w in line.split() if w not in ['-', 'object']]

    return entities


def extract_goal_from_pddl(problem_content):
    """Estrae location e oggetto dal goal"""
    goal_match = re.search(r'\(:goal\s+\(and\s+(.*?)\)\)', problem_content, re.DOTALL)
    if not goal_match:
        return None, None

    goal_section = goal_match.group(1)

    goal_loc = None
    goal_obj = None

    # Cerca (at char loc)
    at_match = re.search(r'\(at\s+(\S+)\s+(\S+)\)', goal_section)
    if at_match:
        goal_loc = at_match.group(2)

    # Cerca (has char obj)
    has_match = re.search(r'\(has\s+(\S+)\s+(\S+)\)', goal_section)
    if has_match:
        goal_obj = has_match.group(2)

    return goal_loc, goal_obj


def fix_problem_connectivity(problem_content, depth_min=7):
    """
    CRITICO: Corregge il problem PDDL per garantire risolvibilità
    CON VINCOLO DI PROFONDITÀ MINIMA
    - Crea un percorso che richiede ALMENO depth_min azioni
    - Aggiunge ostacoli intermedi (location bloccate, oggetti richiesti)
    - Connessioni limitate (NO grafo completo, solo percorso lineare + branch)
    """
    print(f"🔧 Fixing problem connectivity (min depth: {depth_min})...")

    # Estrai entità
    entities = extract_entities_from_pddl(problem_content)
    locs = entities['locations']
    objs = entities['objects']
    chars = entities['characters']

    if not locs or not chars:
        print("   ⚠️ Cannot fix: missing entities")
        return problem_content

    # Estrai goal
    goal_loc, goal_obj = extract_goal_from_pddl(problem_content)

    # Trova sezione :init
    init_match = re.search(r'\(:init\s+(.*?)\s+\)', problem_content, re.DOTALL)
    if not init_match:
        print("   ⚠️ Cannot find :init section")
        return problem_content

    init_section = init_match.group(1)
    init_statements = [line.strip() for line in init_section.split('\n') if line.strip()]

    # Trova location iniziale
    start_loc = None
    for stmt in init_statements:
        if f'(at {chars[0]}' in stmt:
            match = re.search(r'\(at\s+\S+\s+(\S+)\)', stmt)
            if match:
                start_loc = match.group(1)
                break

    if not start_loc:
        start_loc = locs[0]
        init_statements.insert(0, f"(at {chars[0]} {start_loc})")

    if not goal_loc:
        goal_loc = locs[-1]

    print(f"   Building constrained path: {start_loc} -> {goal_loc}")

    # STEP 1: Crea SOLO percorso LINEARE (no shortcuts)
    try:
        start_idx = locs.index(start_loc)
        goal_idx = locs.index(goal_loc)
    except ValueError:
        print("   ⚠️ Start/goal location not in list")
        return problem_content

    # Rimuovi TUTTE le connessioni esistenti e ricrea da zero
    init_statements = [s for s in init_statements if '(connected' not in s]

    new_connections = set()

    # Percorso lineare sequenziale SENZA scorciatoie
    if start_idx < goal_idx:
        for i in range(start_idx, goal_idx):
            loc_a, loc_b = locs[i], locs[i + 1]
            new_connections.add((loc_a, loc_b))
            new_connections.add((loc_b, loc_a))  # Bidirezionale
    else:
        for i in range(start_idx, goal_idx, -1):
            loc_a, loc_b = locs[i], locs[i - 1]
            new_connections.add((loc_a, loc_b))
            new_connections.add((loc_b, loc_a))

    # Aggiungi MAX 2 connessioni extra per branching limitato
    if len(locs) >= 4:
        # Collega location non adiacenti (ma non crea shortcut al goal)
        mid1 = len(locs) // 3
        mid2 = 2 * len(locs) // 3
        if mid1 < len(locs) - 1 and mid2 < len(locs) - 1:
            new_connections.add((locs[mid1], locs[mid2]))
            new_connections.add((locs[mid2], locs[mid1]))

    print(f"   ✓ Created linear path with {len(new_connections)} connections")

    # STEP 2: Aggiungi OSTACOLI per aumentare profondità
    obstacles_added = 0

    # 2a. Location bloccate (richiedono chiavi)
    if len(objs) >= 2 and len(locs) >= 3:
        # Blocca location intermedie
        locked_locs = []
        for i in range(1, min(3, len(locs) - 1)):  # Blocca max 2 location
            locked_loc = locs[start_idx + i] if start_idx < goal_idx else locs[start_idx - i]
            if locked_loc != goal_loc:
                locked_locs.append(locked_loc)
                init_statements.append(f"(locked {locked_loc})")
                obstacles_added += 1

        # Crea chiavi per sbloccare
        for i, locked_loc in enumerate(locked_locs):
            if i < len(objs):
                key = objs[i]
                # Posiziona chiave PRIMA della location bloccata
                key_loc_idx = max(0, locs.index(locked_loc) - 1)
                key_loc = locs[key_loc_idx]
                init_statements.append(f"(at-obj {key} {key_loc})")
                init_statements.append(f"(key-for {key} {locked_loc})")
                print(f"   + Obstacle: {locked_loc} locked, key '{key}' at {key_loc}")
                obstacles_added += 2  # take + unlock

    # 2b. Oggetto richiesto dal goal
    if goal_obj and goal_obj in objs:
        obj_placed = any(goal_obj in s for s in init_statements if 'at-obj' in s)

        if not obj_placed:
            # Posiziona oggetto goal in location intermedia (non vicino a start)
            obj_loc_idx = min(len(locs) - 2, start_idx + len(locs) // 2)
            obj_loc = locs[obj_loc_idx]
            init_statements.append(f"(at-obj {goal_obj} {obj_loc})")
            print(f"   + Goal object '{goal_obj}' at {obj_loc}")
            obstacles_added += 1  # take action

    # 2c. Se ancora troppo corto, aggiungi più location bloccate
    estimated_depth = len(locs) - 1 + obstacles_added
    if estimated_depth < depth_min and len(objs) > 2:
        remaining = depth_min - estimated_depth
        print(f"   ! Path too short ({estimated_depth} < {depth_min}), adding {remaining} obstacles")

        # Aggiungi location bloccate extra
        for i in range(min(remaining // 2, len(locs) - 3)):
            extra_loc_idx = start_idx + i + 2 if start_idx < goal_idx else start_idx - i - 2
            if 0 <= extra_loc_idx < len(locs):
                extra_loc = locs[extra_loc_idx]
                if f"(locked {extra_loc})" not in init_statements and extra_loc != goal_loc:
                    init_statements.append(f"(locked {extra_loc})")
                    # Usa oggetto disponibile come chiave
                    if len([s for s in init_statements if 'key-for' in s]) < len(objs):
                        extra_key = objs[len([s for s in init_statements if 'key-for' in s])]
                        key_loc = locs[max(0, extra_loc_idx - 1)]
                        init_statements.append(f"(at-obj {extra_key} {key_loc})")
                        init_statements.append(f"(key-for {extra_key} {extra_loc})")
                        print(f"   + Extra obstacle: {extra_loc} locked, key '{extra_key}' at {key_loc}")

    # STEP 3: Aggiungi connessioni
    for loc_a, loc_b in new_connections:
        init_statements.append(f"(connected {loc_a} {loc_b})")

    # STEP 4: Aggiungi visited per start
    if f"(visited {start_loc})" not in init_statements:
        init_statements.append(f"(visited {start_loc})")

    # Ricostruisci
    new_init = "  (:init\n    " + "\n    ".join(init_statements) + "\n  )"

    problem_fixed = re.sub(
        r'\(:init\s+.*?\s+\)',
        new_init,
        problem_content,
        flags=re.DOTALL
    )

    return problem_fixed


# ========== VALIDAZIONE PREDICATI ==========
def validate_and_fix_pddl(pddl_content, file_type="domain"):
    """Valida predicati nel PDDL"""
    print(f"🔍 Validating {file_type}...")

    predicates_arity = {}
    predicates_match = re.search(r'\(:predicates\s+(.*?)\)', pddl_content, re.DOTALL)
    if predicates_match:
        predicates_section = predicates_match.group(1)
        for pred in re.finditer(r'\((\w+)([^)]*)\)', predicates_section):
            pred_name = pred.group(1)
            params = pred.group(2)
            arity = params.count('?')
            predicates_arity[pred_name] = arity

    lines = pddl_content.split('\n')
    fixed_lines = []
    in_action = False

    for line in lines:
        if ':action' in line:
            in_action = True

        if in_action and '(' in line:
            for pred_name, arity in predicates_arity.items():
                pattern = r'\(' + pred_name + r'\s+([^)]*)\)'
                matches = re.finditer(pattern, line)

                for match in matches:
                    args = match.group(1).strip()
                    arg_count = args.count('?') if args else 0

                    if arg_count != arity and arg_count > 0:
                        if arg_count < arity:
                            missing = arity - arg_count
                            for i in range(missing):
                                args += f' ?param{i}'
                            fixed = f'({pred_name} {args})'
                            line = line.replace(match.group(0), fixed)

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


# ========== GENERAZIONE CON LLM ==========
def generate_pddl_from_lore(lore_text):
    print("📖 Parsing lore document...")
    lore_data = parse_lore_document(lore_text)

    chars, locs, objs = get_normalized_entities(lore_data)

    print(f"✅ Parsed data:")
    print(f"   - Branching: {lore_data['branching_min']}-{lore_data['branching_max']}")
    print(f"   - Depth: {lore_data['depth_min']}-{lore_data['depth_max']}")
    print(f"   - Characters: {chars}")
    print(f"   - Locations: {locs}")
    print(f"   - Objects: {objs}")

    # ========== GENERAZIONE DOMAIN ==========
    print("\n🔧 Generating PDDL domain with LLM...")

    domain_system = """You are a PDDL expert. Generate ONLY valid PDDL code, NO explanations, NO markdown.
CRITICAL: Every predicate must be used with the EXACT number of parameters defined in :predicates."""

    domain_template = """(define (domain narrative-domain)
  (:requirements :strips :typing)
  (:types character location object - thing)
  (:predicates 
    (at ?c - character ?l - location)
    (has ?c - character ?o - object)
    (connected ?l1 - location ?l2 - location)
    (at-obj ?o - object ?l - location)
    (visited ?l - location)
    (locked ?l - location)
    (key-for ?o - object ?l - location)
  )
  (:action move
    :parameters (?c - character ?from - location ?to - location)
    :precondition (and (at ?c ?from) (connected ?from ?to) (not (locked ?to)))
    :effect (and (not (at ?c ?from)) (at ?c ?to) (visited ?to))
  )
  (:action take
    :parameters (?c - character ?o - object ?l - location)
    :precondition (and (at ?c ?l) (at-obj ?o ?l))
    :effect (and (has ?c ?o) (not (at-obj ?o ?l)))
  )
)"""

    domain_prompt = f"""Expand this PDDL domain by adding 2-3 new actions based on the lore:

{domain_template}

Lore context:
- Characters: {', '.join(chars)}
- Locations: {', '.join(locs)}
- Objects: {', '.join(objs)}

Add actions like:
- unlock: use a key to unlock a locked location
- interact: two characters interact
- use: use an object to trigger an effect

RULES:
1. Keep ALL existing predicates and actions
2. New actions must use predicates with correct arity:
   - (at ?c ?l) needs 2 params
   - (has ?c ?o) needs 2 params
   - (connected ?l1 ?l2) needs 2 params
3. Generate ONLY the complete domain PDDL, nothing else

Domain:"""

    domain_content = call_ollama(domain_prompt, domain_system, temperature=0.3, num_predict=1500)

    # Pulizia
    domain_content = re.sub(r'```[a-z]*\n?', '', domain_content)
    domain_content = re.sub(r'^[^(]*', '', domain_content)
    domain_content = domain_content.strip()

    if not domain_content.startswith('(define'):
        print("⚠️ LLM failed, using template")
        domain_content = domain_template

    domain_content = validate_and_fix_pddl(domain_content, "domain")

    # Fix parentesi
    open_count = domain_content.count('(')
    close_count = domain_content.count(')')
    if open_count != close_count:
        domain_content += ')' * (open_count - close_count)

    domain_path = OUTPUT_DIR / "domain.pddl"
    with open(domain_path, "w", encoding="utf-8") as f:
        f.write(domain_content)
    print(f"✅ Domain saved to {domain_path}")

    # ========== GENERAZIONE PROBLEM ==========
    print("\n🎯 Generating PDDL problem with LLM...")

    problem_system = """You are a PDDL expert. Generate ONLY valid PDDL code, NO explanations, NO markdown.
Use EXACT entity names provided. Create a solvable problem."""

    problem_template = f"""(define (problem narrative-problem)
  (:domain narrative-domain)
  (:objects
    {' '.join(chars)} - character
    {' '.join(locs)} - location
    {' '.join(objs)} - object
  )
  (:init
    (at {chars[0]} {locs[0]})
    (connected {locs[0]} {locs[1]})
    (at-obj {objs[0]} {locs[1]})
    (visited {locs[0]})
  )
  (:goal (and
    (at {chars[0]} {locs[-1]})
    (has {chars[0]} {objs[0]})
  ))
)"""

    problem_prompt = f"""Expand this PDDL problem to create a narrative with {lore_data['depth_min']}-{lore_data['depth_max']} steps:

{problem_template}

Requirements:
1. Keep (:objects) section UNCHANGED
2. Expand (:init):
   - Add (connected loc1 loc2) between ALL locations (bidirectional!)
   - Place objects with (at-obj obj loc)
   - Position characters with (at char loc)
   - Keep {chars[0]} at {locs[0]}
3. Goal: {chars[0]} must reach {locs[-1]} with {objs[0]}

Generate complete problem PDDL:"""

    problem_content = call_ollama(problem_prompt, problem_system, temperature=0.4, num_predict=1200)

    # Pulizia
    problem_content = re.sub(r'```[a-z]*\n?', '', problem_content)
    problem_content = re.sub(r'^[^(]*', '', problem_content)
    problem_content = problem_content.strip()

    if not problem_content.startswith('(define'):
        print("⚠️ LLM failed, using template")
        problem_content = problem_template

    problem_content = validate_and_fix_pddl(problem_content, "problem")

    # CRITICO: Fix connettività CON vincolo di profondità
    problem_content = fix_problem_connectivity(problem_content, lore_data['depth_min'])

    # Fix parentesi
    open_count = problem_content.count('(')
    close_count = problem_content.count(')')
    if open_count != close_count:
        problem_content += ')' * (open_count - close_count)

    problem_path = OUTPUT_DIR / "problem.pddl"
    with open(problem_path, "w", encoding="utf-8") as f:
        f.write(problem_content)
    print(f"✅ Problem saved to {problem_path}")

    return domain_path, problem_path


# ========== VALIDAZIONE ==========
def validate_with_fastdownward(domain_path, problem_path):
    fast_downward_path = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"
    if not os.path.exists(fast_downward_path):
        print("⚠️ Fast Downward not found")
        return False

    cmd = ["python", fast_downward_path, str(domain_path), str(problem_path),
           "--search", "astar(lmcut())"]

    try:
        print("▶️ Running Fast Downward...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if "Solution found!" in result.stdout or result.returncode == 0:
            print("✅ PROBLEM IS SOLVABLE!")
            plan_match = re.search(r"Plan length: (\d+)", result.stdout)
            if plan_match:
                print(f"   📊 Plan length: {plan_match.group(1)} steps")
            return True
        else:
            print("❌ No solution found")
            if "dead end" in result.stdout.lower():
                print("   Issue: Initial state unreachable")
            return False

    except subprocess.TimeoutExpired:
        print("⏱️ Timeout (problem too complex)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# ========== MAIN ==========
if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent
    lore_path = BASE_DIR / "ChatBot" / "Generated_Lore" / "Lore.txt"

    try:
        with open(lore_path, "r", encoding="utf-8") as f:
            lore_text = f.read()

        domain_path, problem_path = generate_pddl_from_lore(lore_text)

        if domain_path and problem_path:
            print("\n" + "=" * 60)
            validate_with_fastdownward(domain_path, problem_path)
        else:
            print("❌ Failed to generate PDDL")

    except FileNotFoundError:
        print(f"❌ Lore file not found: {lore_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()