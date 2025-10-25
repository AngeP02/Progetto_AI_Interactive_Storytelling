import os
import re
import requests
from pathlib import Path
import subprocess
import json

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
    entities["goals"] = list(set(re.findall(r"Goal:?\s*(.+)", lore_text)))

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
    response = requests.post(OLLAMA_URL, json=payload, timeout=500)
    response.raise_for_status()
    result = response.json()
    return result.get('response', '').strip()


# ========== GENERAZIONE PDDL ==========
def validate_and_fix_pddl(pddl_content, file_type="domain"):
    """
    Valida e corregge errori comuni in PDDL generato da LLM.
    """
    print(f"🔍 Validating {file_type}...")

    # Pattern per trovare predicati nella sezione :predicates
    predicates_arity = {}
    predicates_match = re.search(r'\(:predicates\s+(.*?)\)', pddl_content, re.DOTALL)
    if predicates_match:
        predicates_section = predicates_match.group(1)
        # Trova tutti i predicati e conta i parametri
        for pred in re.finditer(r'\((\w+)([^)]*)\)', predicates_section):
            pred_name = pred.group(1)
            params = pred.group(2)
            # Conta i parametri (ogni ? indica un parametro)
            arity = params.count('?')
            predicates_arity[pred_name] = arity
            print(f"   Found predicate: {pred_name} with arity {arity}")

    # Verifica uso dei predicati nelle azioni
    lines = pddl_content.split('\n')
    fixed_lines = []
    in_action = False

    for line in lines:
        if ':action' in line:
            in_action = True

        # Cerca predicati malformati solo dentro le azioni
        if in_action and '(' in line:
            for pred_name, arity in predicates_arity.items():
                # Pattern per trovare il predicato con numero sbagliato di argomenti
                pattern = r'\(' + pred_name + r'\s+([^)]*)\)'
                matches = re.finditer(pattern, line)

                for match in matches:
                    args = match.group(1).strip()
                    arg_count = args.count('?') if args else 0

                    if arg_count != arity and arg_count > 0:
                        print(f"   ⚠️ Fixing {pred_name}: found {arg_count} args, needs {arity}")
                        # Se mancano argomenti, aggiungi placeholder
                        if arg_count < arity:
                            missing = arity - arg_count
                            for i in range(missing):
                                args += f' ?param{i}'
                            fixed = f'({pred_name} {args})'
                            line = line.replace(match.group(0), fixed)

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def generate_pddl_from_lore(lore_text):
    """
    Genera domain.pddl e problem.pddl da un testo di lore usando Ollama.
    Usa template PDDL come riferimento per garantire sintassi corretta.
    Ritorna una tupla (domain_path, problem_path) o (None, None) in caso di errore.
    """
    print("📖 Parsing lore document...")
    lore_data = parse_lore_document(lore_text)

    # FILTRO: Rimuovi parole comuni che non sono nomi propri
    common_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but',
                    'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does',
                    'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall',
                    'this', 'that', 'these', 'those', 'with', 'from', 'by', 'as', 'into', 'through'}

    # Filtra characters: rimuovi parole comuni e mantieni solo nomi di almeno 3 caratteri
    filtered_chars = [c for c in lore_data['entities']['characters']
                      if c.lower() not in common_words and len(c) >= 3]
    lore_data['entities']['characters'] = filtered_chars

    # Fix: aggiungi locations di default se non trovate
    if not lore_data['entities']['locations']:
        lore_data['entities']['locations'] = ["MainHall", "SecretRoom", "Laboratory", "Entrance", "Storage"]
        print("⚠️ No locations found in lore, using defaults")

    # Fix: aggiungi characters di default se insufficienti (senza duplicati)
    existing_chars = set([c.lower() for c in lore_data['entities']['characters']])
    if len(lore_data['entities']['characters']) < 2:
        defaults = ["Hero", "Villain", "Guide", "Mentor", "Rival"]
        for char in defaults:
            if char.lower() not in existing_chars:
                lore_data['entities']['characters'].append(char)
                existing_chars.add(char.lower())
                if len(lore_data['entities']['characters']) >= 3:
                    break

    # Fix: aggiungi objects di default se insufficienti (senza duplicati)
    existing_objs = set([o.lower() for o in lore_data['entities']['objects']])
    if len(lore_data['entities']['objects']) < 2:
        defaults = ["key", "artifact", "device", "scroll", "tool"]
        for obj in defaults:
            if obj.lower() not in existing_objs:
                lore_data['entities']['objects'].append(obj)
                existing_objs.add(obj.lower())
                if len(lore_data['entities']['objects']) >= 3:
                    break

    print(f"✅ Parsed data:")
    print(f"   - Branching: {lore_data['branching_min']}-{lore_data['branching_max']}")
    print(f"   - Depth: {lore_data['depth_min']}-{lore_data['depth_max']}")
    print(f"   - Characters: {len(lore_data['entities']['characters'])}")
    print(f"   - Locations: {len(lore_data['entities']['locations'])}")
    print(f"   - Objects: {len(lore_data['entities']['objects'])}")

    # ========== GENERAZIONE DOMAIN CON TEMPLATE ==========
    print("\n🔧 Generating PDDL domain...")

    domain_system_prompt = """You are an expert in PDDL (Planning Domain Definition Language).
You MUST generate ONLY the PDDL code, with NO explanations, NO markdown, NO extra text.
Follow the EXACT structure of the template provided.
CRITICAL: When using predicates in actions, you MUST use the EXACT same number of parameters as defined in :predicates section.
Example: if (at ?c - character ?l - location) is defined, you MUST use (at ?c ?l) with BOTH parameters, never (at ?c) alone."""

    domain_template = """(define (domain narrative-domain)
  (:requirements :strips :typing)

  (:types 
    character location object - thing
  )

  (:predicates 
    (at ?c - character ?l - location)
    (has ?c - character ?o - object)
    (connected ?l1 - location ?l2 - location)
    (accessible ?o - object ?l - location)
    (visited ?l - location)
    (unlocked ?l - location)
  )

  (:action move
    :parameters (?c - character ?from - location ?to - location)
    :precondition (and 
      (at ?c ?from) 
      (connected ?from ?to)
      (unlocked ?to)
    )
    :effect (and 
      (not (at ?c ?from)) 
      (at ?c ?to)
      (visited ?to)
    )
  )

  (:action take
    :parameters (?c - character ?o - object ?l - location)
    :precondition (and 
      (at ?c ?l) 
      (accessible ?o ?l)
    )
    :effect (and 
      (has ?c ?o) 
      (not (accessible ?o ?l))
    )
  )
)"""

    domain_prompt = f"""Use this EXACT PDDL template structure and add 2-3 more actions based on the lore context:

{domain_template}

Based on this lore information, add actions like:
- 'use' (use an object at a location to unlock it)
- 'interact' (two characters interact at same location)
- 'combine' (combine two objects)

CRITICAL RULES FOR PREDICATES:
- (at ?c ?l) ALWAYS needs 2 parameters: character AND location
- (has ?c ?o) ALWAYS needs 2 parameters: character AND object
- (connected ?l1 ?l2) ALWAYS needs 2 parameters: two locations
- (accessible ?o ?l) ALWAYS needs 2 parameters: object AND location
- (visited ?l) needs 1 parameter: location
- (unlocked ?l) needs 1 parameter: location

NEVER write (at ?c) or (has ?o) - these are WRONG!

Example of CORRECT new action:
(:action use
  :parameters (?c - character ?o - object ?l - location)
  :precondition (and 
    (at ?c ?l)           <- CORRECT: 2 parameters
    (has ?c ?o)          <- CORRECT: 2 parameters
  )
  :effect (unlocked ?l)  <- CORRECT: 1 parameter
)

Generate the complete domain now with 2-3 additional actions:"""

    try:
        domain_content = call_ollama(domain_prompt, domain_system_prompt, temperature=0.3, num_predict=1200)

        # Pulizia aggressiva
        domain_content = re.sub(r'```[a-z]*\n?', '', domain_content)
        domain_content = re.sub(r'^[^(]*', '', domain_content)
        domain_content = domain_content.strip()

        # Se l'LLM ha fallito, usa il template
        if not domain_content.startswith('(define'):
            print("⚠️ LLM output invalid, using template")
            domain_content = domain_template

        # VALIDAZIONE E FIX AUTOMATICO
        domain_content = validate_and_fix_pddl(domain_content, "domain")

        # Fix parentesi
        open_count = domain_content.count('(')
        close_count = domain_content.count(')')

        if open_count != close_count:
            print(f"⚠️ Fixing parentheses: {open_count} open, {close_count} close")
            if close_count > open_count:
                while close_count > open_count and domain_content.endswith(')'):
                    domain_content = domain_content[:-1].rstrip()
                    close_count -= 1
            else:
                domain_content += ')' * (open_count - close_count)
            print(f"✓ Fixed: {domain_content.count('(')} open, {domain_content.count(')')} close")

        domain_path = OUTPUT_DIR / "domain.pddl"
        with open(domain_path, "w", encoding="utf-8") as f:
            f.write(domain_content)
        print(f"✅ Domain saved to {domain_path}")

    except Exception as e:
        print(f"❌ Error generating domain: {e}")
        return None, None

    # ========== GENERAZIONE PROBLEM CON TEMPLATE ==========
    print("\n🎯 Generating PDDL problem...")

    problem_system_prompt = """You are an expert in PDDL (Planning Domain Definition Language).
You MUST generate ONLY the PDDL code, with NO explanations, NO markdown, NO extra text.
Follow the EXACT structure of the template provided.
Use EXACTLY the entity names provided - do not split them or use only parts of them."""

    # Normalizza nomi in modo SICURO e RIMUOVI DUPLICATI
    def normalize_name(name):
        # Mantieni solo caratteri alfanumerici, sostituisci spazi/simboli con underscore
        name = re.sub(r'[^a-zA-Z0-9]+', '_', str(name))
        name = name.strip('_').lower()
        # Assicurati che inizi con una lettera
        if name and not name[0].isalpha():
            name = 'e_' + name
        # Minimo 2 caratteri
        return name if len(name) >= 2 else None

    # Usa set per evitare duplicati durante la normalizzazione
    chars_set = set()
    for c in lore_data['entities']['characters'][:20]:  # Prendi più candidati
        normalized = normalize_name(c)
        if normalized:
            chars_set.add(normalized)
        if len(chars_set) >= 3:
            break
    chars = list(chars_set)[:3]
    if len(chars) < 2:
        chars = ['hero', 'villain', 'guide'][:max(2, len(chars) + 2)]

    locs_set = set()
    for l in lore_data['entities']['locations'][:20]:
        normalized = normalize_name(l)
        if normalized:
            locs_set.add(normalized)
        if len(locs_set) >= 5:
            break
    locs = list(locs_set)[:5]
    if len(locs) < 3:
        locs = ['start', 'middle', 'goal', 'room_a', 'room_b'][:max(3, len(locs) + 3)]

    objs_set = set()
    for o in lore_data['entities']['objects'][:20]:
        normalized = normalize_name(o)
        if normalized:
            objs_set.add(normalized)
        if len(objs_set) >= 4:
            break
    objs = list(objs_set)[:4]
    if len(objs) < 2:
        objs = ['key', 'artifact', 'tool'][:max(2, len(objs) + 2)]

    print(f"   Using entities (validated, no duplicates):")
    print(f"   - Characters: {', '.join(chars)}")
    print(f"   - Locations: {', '.join(locs)}")
    print(f"   - Objects: {', '.join(objs)}")

    # Crea template con entità valide
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
    (connected {locs[1]} {locs[0]})
    (accessible {objs[0]} {locs[1]})
    (unlocked {locs[0]})
    (visited {locs[0]})
  )

  (:goal (and
    (at {chars[0]} {locs[-1]})
    (has {chars[0]} {objs[0]})
  ))
)"""

    problem_prompt = f"""Use this EXACT PDDL template and expand ONLY the (:init) and (:goal) sections:

{problem_template}

Expand this problem:
1. Add more (connected loc1 loc2) - use bidirectional connections between ALL locations
2. Place more objects: (accessible obj loc)
3. Position characters: (at char loc) - but keep at least {chars[0]} at {locs[0]}
4. Add (unlocked loc) and (visited loc) for some locations
5. Goal: make {chars[0]} reach {locs[-1]} with {objs[0]}, requiring {lore_data['depth_min']}-{lore_data['depth_max']} steps

CRITICAL - Use EXACTLY these entity names:
Characters: {', '.join(chars)}
Locations: {', '.join(locs)}
Objects: {', '.join(objs)}

DO NOT modify the (:objects) section!
DO NOT use partial names (e.g., if entity is 'hero_one', use 'hero_one' not 'hero')!

Generate:"""

    try:
        problem_content = call_ollama(problem_prompt, problem_system_prompt, temperature=0.4, num_predict=1000)

        # Pulizia
        problem_content = re.sub(r'```[a-z]*\n?', '', problem_content)
        problem_content = re.sub(r'^[^(]*', '', problem_content)
        problem_content = problem_content.strip()

        # Fallback al template
        if not problem_content.startswith('(define'):
            print("⚠️ LLM output invalid, using template")
            problem_content = problem_template

        # VALIDAZIONE
        problem_content = validate_and_fix_pddl(problem_content, "problem")

        # Fix parentesi
        open_count = problem_content.count('(')
        close_count = problem_content.count(')')

        if open_count != close_count:
            print(f"⚠️ Fixing parentheses: {open_count} open, {close_count} close")
            if close_count > open_count:
                while close_count > open_count and problem_content.endswith(')'):
                    problem_content = problem_content[:-1].rstrip()
                    close_count -= 1
            else:
                problem_content += ')' * (open_count - close_count)
            print(f"✓ Fixed: {problem_content.count('(')} open, {problem_content.count(')')} close")

        problem_path = OUTPUT_DIR / "problem.pddl"
        with open(problem_path, "w", encoding="utf-8") as f:
            f.write(problem_content)
        print(f"✅ Problem saved to {problem_path}")

        return domain_path, problem_path

    except Exception as e:
        print(f"❌ Error generating problem: {e}")
        return domain_path, None


# ========== VALIDAZIONE FAST DOWNWARD ==========
def validate_with_fastdownward(domain_path, problem_path):
    fast_downward_path = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"
    if not os.path.exists(fast_downward_path):
        print("❌ Fast Downward not found.")
        return

    cmd = ["python", fast_downward_path, str(domain_path), str(problem_path), "--search", "astar(lmcut())"]

    try:
        print("▶️ Running Fast Downward...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Validation completed.\n", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Fast Downward error:\n{e.stdout}\n{e.stderr}")


# ========== MAIN ==========
if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent
    lore_path = BASE_DIR / "Lore" / "Generated_Lore" / "Lore.txt"

    with open(lore_path, "r", encoding="utf-8") as f:
        lore_text = f.read()

    domain_path, problem_path = generate_pddl_from_lore(lore_text)
    if domain_path and problem_path:
        validate_with_fastdownward(domain_path, problem_path)
