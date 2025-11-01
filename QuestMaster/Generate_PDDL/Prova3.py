import os
import sys
import re
import json
import requests
import subprocess
import logging
from pathlib import Path
from typing import Tuple, List, Set, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


# =============================================================================
# NUOVA STRATEGIA: TEMPLATE-BASED CON ESTRAZIONE INCREMENTALE
# =============================================================================

class DomainTemplate(Enum):
    """Template di domini PDDL pre-validati"""
    LOGISTICS = "logistics"
    BLOCKSWORLD = "blocksworld"
    GRID = "grid"
    KEYS_DOORS = "keys_doors"


@dataclass
class PDDLTemplate:
    """Template PDDL con slot da riempire"""
    domain_name: str
    types: List[str]
    predicates: List[str]
    actions: List[Dict]

    def to_domain_pddl(self) -> str:
        """Genera domain.pddl dal template"""
        types_str = " ".join(self.types)
        preds_str = "\n    ".join(self.predicates)

        actions_str = ""
        for action in self.actions:
            actions_str += f"""
  (:action {action['name']}
   :parameters ({action['parameters']})
   :precondition {action['precondition']}
   :effect {action['effect']}
  )
"""

        return f"""(define (domain {self.domain_name})
  (:requirements :strips :typing)
  (:types {types_str})
  (:predicates
    {preds_str}
  )
{actions_str}
)"""


# =============================================================================
# TEMPLATE LIBRARY - Domini pre-validati
# =============================================================================

TEMPLATE_LIBRARY = {
    DomainTemplate.LOGISTICS: PDDLTemplate(
        domain_name="logistics",
        types=["location", "movable", "vehicle - movable", "package - movable"],
        predicates=[
            "(at ?obj - movable ?loc - location)",
            "(in ?pkg - package ?veh - vehicle)",
            "(connected ?from ?to - location)"
        ],
        actions=[
            {
                "name": "move",
                "parameters": "?v - vehicle ?from ?to - location",
                "precondition": "(and (at ?v ?from) (connected ?from ?to))",
                "effect": "(and (not (at ?v ?from)) (at ?v ?to))"
            },
            {
                "name": "load",
                "parameters": "?p - package ?v - vehicle ?loc - location",
                "precondition": "(and (at ?p ?loc) (at ?v ?loc))",
                "effect": "(and (not (at ?p ?loc)) (in ?p ?v))"
            },
            {
                "name": "unload",
                "parameters": "?p - package ?v - vehicle ?loc - location",
                "precondition": "(and (in ?p ?v) (at ?v ?loc))",
                "effect": "(and (not (in ?p ?v)) (at ?p ?loc))"
            }
        ]
    ),

    DomainTemplate.GRID: PDDLTemplate(
        domain_name="grid-navigation",
        types=["position", "agent"],
        predicates=[
            "(at ?a - agent ?p - position)",
            "(adjacent ?p1 ?p2 - position)",
            "(clear ?p - position)",
            "(goal-pos ?p - position)"
        ],
        actions=[
            {
                "name": "move",
                "parameters": "?a - agent ?from ?to - position",
                "precondition": "(and (at ?a ?from) (adjacent ?from ?to) (clear ?to))",
                "effect": "(and (not (at ?a ?from)) (not (clear ?to)) (at ?a ?to) (clear ?from))"
            }
        ]
    ),

    DomainTemplate.KEYS_DOORS: PDDLTemplate(
        domain_name="keys-doors",
        types=["location", "key", "door", "agent"],
        predicates=[
            "(at ?a - agent ?l - location)",
            "(key-at ?k - key ?l - location)",
            "(has-key ?a - agent ?k - key)",
            "(door-between ?d - door ?l1 ?l2 - location)",
            "(locked ?d - door)",
            "(unlocks ?k - key ?d - door)"
        ],
        actions=[
            {
                "name": "move",
                "parameters": "?a - agent ?from ?to - location ?d - door",
                "precondition": "(and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d)))",
                "effect": "(and (not (at ?a ?from)) (at ?a ?to))"
            },
            {
                "name": "pick-key",
                "parameters": "?a - agent ?k - key ?l - location",
                "precondition": "(and (at ?a ?l) (key-at ?k ?l))",
                "effect": "(and (not (key-at ?k ?l)) (has-key ?a ?k))"
            },
            {
                "name": "unlock",
                "parameters": "?a - agent ?k - key ?d - door ?l - location",
                "precondition": "(and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d))",
                "effect": "(not (locked ?d))"
            }
        ]
    )
}


# =============================================================================
# ESTRATTORE DI ENTITÀ DAL LORE
# =============================================================================

class LoreAnalyzer:
    """Estrae entità e relazioni dal lore per mappare sui template"""

    def __init__(self, lore_content: str):
        self.lore = lore_content

    def extract_entities(self) -> Dict:
        """Usa LLM per estrarre entità strutturate"""

        system_prompt = """You are a domain analyzer. Extract structured entities from narrative text.
Output ONLY valid JSON, no explanations."""

        prompt = f"""Analyze this narrative and extract:

LORE:
{self.lore}

Extract as JSON:
{{
  "agents": ["list of characters/robots/entities that can act"],
  "locations": ["list of places"],
  "objects": ["list of items/objects"],
  "connections": [["loc1", "loc2"], ...],
  "initial_facts": ["entity is at location", ...],
  "goal_facts": ["desired final state", ...]
}}

IMPORTANT: Be concrete and specific. Extract actual names from the lore.
OUTPUT ONLY JSON:"""

        response = call_ollama(prompt, system_prompt)

        if not response:
            logger.warning("LLM non ha risposto, uso fallback")
            return self._fallback_extraction()

        try:
            # Pulisci response da markdown
            response = re.sub(r'```json\n?', '', response)
            response = re.sub(r'```\n?', '', response)

            data = json.loads(response)

            # Valida struttura
            if not isinstance(data, dict):
                logger.warning(f"LLM ha ritornato tipo non valido: {type(data)}")
                return self._fallback_extraction()

            # Log per debug
            logger.info(f"Entità estratte dall'LLM: {json.dumps(data, indent=2)}")

            return data

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing fallito: {e}")
            logger.warning(f"Response LLM: {response[:200]}...")
            return self._fallback_extraction()
        except Exception as e:
            logger.error(f"Errore inaspettato: {e}")
            return self._fallback_extraction()

    def _fallback_extraction(self) -> Dict:
        """Estrazione regex-based se LLM fallisce"""
        logger.warning("⚠️ Fallback: estrazione regex-based")

        # Estrai nomi propri (maiuscoli)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', self.lore)

        # Rimuovi duplicati mantenendo ordine
        seen = set()
        unique_entities = []
        for e in entities:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique_entities.append(e)

        # Estrai location keywords
        location_keywords = ['room', 'hall', 'chamber', 'cave', 'forest', 'castle', 'town', 'village']
        locations = []
        for keyword in location_keywords:
            matches = re.findall(rf'\b(\w+\s+{keyword}|{keyword}\s+\w+)\b', self.lore, re.IGNORECASE)
            locations.extend(matches[:2])

        if not locations:
            locations = ['location1', 'location2', 'location3', 'location4']

        agents = unique_entities[:2] if unique_entities else ['hero', 'character']

        return {
            "agents": agents,
            "locations": locations[:4],
            "objects": ["item1", "item2"],
            "connections": [[locations[i], locations[i + 1]] for i in range(min(3, len(locations) - 1))],
            "initial_facts": [],
            "goal_facts": []
        }

    def match_template(self) -> DomainTemplate:
        """Seleziona il template più adatto al lore"""

        lore_lower = self.lore.lower()

        # Euristica semplice
        if any(word in lore_lower for word in ['key', 'door', 'lock', 'unlock', 'room']):
            return DomainTemplate.KEYS_DOORS
        elif any(word in lore_lower for word in ['package', 'deliver', 'transport', 'cargo']):
            return DomainTemplate.LOGISTICS
        elif any(word in lore_lower for word in ['grid', 'maze', 'path', 'navigate']):
            return DomainTemplate.GRID
        else:
            # Default: LOGISTICS è il più versatile
            return DomainTemplate.LOGISTICS


# =============================================================================
# GENERATORE TEMPLATE-BASED
# =============================================================================

class TemplatePDDLGenerator:
    """Genera PDDL istanziando template validati"""

    def __init__(self, lore_path: Path, output_dir: Path):
        self.lore_path = lore_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        with open(lore_path, 'r', encoding='utf-8') as f:
            self.lore = f.read()

        self.analyzer = LoreAnalyzer(self.lore)
        self.entities = None
        self.template = None

    def generate(self) -> Tuple[bool, str]:
        """Pipeline di generazione template-based"""

        logger.info("📖 Analisi lore...")
        self.entities = self.analyzer.extract_entities()
        logger.info(f"✓ Entità estratte: {len(self.entities.get('agents', []))} agenti, "
                    f"{len(self.entities.get('locations', []))} locations")

        logger.info("🎯 Selezione template...")
        template_type = self.analyzer.match_template()
        self.template = TEMPLATE_LIBRARY[template_type]
        logger.info(f"✓ Template selezionato: {template_type.value}")

        logger.info("🔨 Generazione PDDL...")
        domain_pddl = self.template.to_domain_pddl()
        problem_pddl = self._generate_problem()

        # Salva
        domain_path = self.output_dir / "domain.pddl"
        problem_path = self.output_dir / "problem.pddl"

        with open(domain_path, 'w') as f:
            f.write(domain_pddl)
        with open(problem_path, 'w') as f:
            f.write(problem_pddl)

        logger.info(f"✓ File salvati in {self.output_dir}")
        return True, "PDDL generato da template"

    def _generate_problem(self) -> str:
        """Genera problem.pddl dalle entità estratte"""

        agents = self.entities.get('agents', ['agent1'])
        locations = self.entities.get('locations', ['loc1', 'loc2'])
        objects = self.entities.get('objects', [])

        # Normalizza a liste di stringhe (in caso l'LLM ritorni dict/altro)
        agents = self._normalize_to_strings(agents)
        locations = self._normalize_to_strings(locations)
        objects = self._normalize_to_strings(objects)

        # Sanitizza nomi (rimuovi spazi, lowercase)
        agents = [self._sanitize_name(a) for a in agents]
        locations = [self._sanitize_name(l) for l in locations]
        objects = [self._sanitize_name(o) for o in objects]

        # Costruisci :objects basato sul template
        objects_section = self._build_objects_section(agents, locations, objects)

        # Costruisci :init basato sul template
        init_section = self._build_init_section(agents, locations, objects)

        # Costruisci :goal dal lore o default
        goal_section = self._build_goal_section(agents, locations, objects)

        return f"""(define (problem {self.template.domain_name}-problem)
  (:domain {self.template.domain_name})
  {objects_section}
  (:init
{init_section}
  )
  (:goal
{goal_section}
  )
)"""

    def _sanitize_name(self, name: str) -> str:
        """Pulisce nomi per PDDL"""
        # Converti a stringa se non lo è già
        if not isinstance(name, str):
            name = str(name)

        name = name.lower().strip()
        name = re.sub(r'[^a-z0-9_-]', '_', name)
        name = re.sub(r'_+', '_', name)
        return name

    def _normalize_to_strings(self, items) -> List[str]:
        """Converte qualsiasi struttura a lista di stringhe"""
        if not items:
            return []

        result = []

        # Se è una lista
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    # Prendi il primo valore o chiave
                    if 'name' in item:
                        result.append(str(item['name']))
                    elif item:
                        result.append(str(next(iter(item.values()))))
                elif isinstance(item, str):
                    result.append(item)
                else:
                    result.append(str(item))

        # Se è un dict (non dovrebbe essere)
        elif isinstance(items, dict):
            result = [str(v) for v in items.values()]

        # Se è una stringa singola
        elif isinstance(items, str):
            result = [items]

        return result

    def _build_objects_section(self, agents, locations, objects) -> str:
        """Costruisce sezione :objects specifica per template"""

        if self.template.domain_name == "logistics":
            # Primi agenti sono veicoli, resto packages
            vehicles = agents[:2] if len(agents) >= 2 else agents
            packages = objects[:3] if objects else ["package1"]

            return f"""(:objects
    {' '.join(locations)} - location
    {' '.join(vehicles)} - vehicle
    {' '.join(packages)} - package
  )"""

        elif self.template.domain_name == "grid-navigation":
            return f"""(:objects
    {' '.join(locations)} - position
    {' '.join(agents[:1])} - agent
  )"""

        elif self.template.domain_name == "keys-doors":
            keys = objects[:2] if objects else ["key1"]
            doors = [f"door{i}" for i in range(len(locations) - 1)]

            return f"""(:objects
    {' '.join(locations)} - location
    {' '.join(agents[:1])} - agent
    {' '.join(keys)} - key
    {' '.join(doors)} - door
  )"""

        return "(:objects )"

    def _build_init_section(self, agents, locations, objects) -> str:
        """Costruisce stato iniziale"""

        init_facts = []

        if self.template.domain_name == "logistics":
            vehicles = agents[:2] if len(agents) >= 2 else agents
            packages = objects[:3] if objects else ["package1"]

            # Veicoli alle prime locations
            for i, v in enumerate(vehicles):
                init_facts.append(f"    (at {v} {locations[i % len(locations)]})")

            # Packages all'ultima location
            for p in packages:
                init_facts.append(f"    (at {p} {locations[-1]})")

            # Connessioni
            for i in range(len(locations) - 1):
                init_facts.append(f"    (connected {locations[i]} {locations[i + 1]})")
                init_facts.append(f"    (connected {locations[i + 1]} {locations[i]})")

        elif self.template.domain_name == "grid-navigation":
            # Agente alla prima posizione
            init_facts.append(f"    (at {agents[0]} {locations[0]})")

            # Tutte le posizioni clear tranne la prima
            for loc in locations[1:]:
                init_facts.append(f"    (clear {loc})")

            # Goal position
            init_facts.append(f"    (goal-pos {locations[-1]})")

            # Adiacenze
            for i in range(len(locations) - 1):
                init_facts.append(f"    (adjacent {locations[i]} {locations[i + 1]})")
                init_facts.append(f"    (adjacent {locations[i + 1]} {locations[i]})")

        elif self.template.domain_name == "keys-doors":
            keys = objects[:2] if objects else ["key1"]
            doors = [f"door{i}" for i in range(len(locations) - 1)]

            # Agente alla prima location
            init_facts.append(f"    (at {agents[0]} {locations[0]})")

            # Chiavi sparse
            for i, k in enumerate(keys):
                init_facts.append(f"    (key-at {k} {locations[i % len(locations)]})")

            # Porte tra locations
            for i, d in enumerate(doors):
                init_facts.append(f"    (door-between {d} {locations[i]} {locations[i + 1]})")
                init_facts.append(f"    (locked {d})")
                # Ogni chiave sblocca la porta corrispondente
                if i < len(keys):
                    init_facts.append(f"    (unlocks {keys[i]} {d})")

        return "\n".join(init_facts)

    def _build_goal_section(self, agents, locations, objects) -> str:
        """Costruisce goal"""

        if self.template.domain_name == "logistics":
            packages = objects[:3] if objects else ["package1"]
            # Goal: tutti i package alla prima location
            goals = [f"(at {p} {locations[0]})" for p in packages]
            return f"    (and {' '.join(goals)})"

        elif self.template.domain_name == "grid-navigation":
            # Goal: agente alla goal-pos
            return f"    (at {agents[0]} {locations[-1]})"

        elif self.template.domain_name == "keys-doors":
            # Goal: agente all'ultima location
            return f"    (at {agents[0]} {locations[-1]})"

        return "    (and )"


# =============================================================================
# VALIDATORE FAST DOWNWARD (uguale a prima)
# =============================================================================

class FastDownwardValidator:
    """Wrapper per Fast Downward"""

    def __init__(self, fd_path: str):
        self.fd_path = Path(fd_path)
        if not self.fd_path.exists():
            raise FileNotFoundError(f"Fast Downward non trovato: {fd_path}")

    def validate(self, domain_path: Path, problem_path: Path) -> Tuple[bool, str, str]:
        """Valida con Fast Downward"""
        python_exe = sys.executable

        cmd = [
            python_exe,
            str(self.fd_path),
            str(domain_path.resolve()),
            str(problem_path.resolve()),
            "--search", "astar(lmcut())"
        ]

        env = os.environ.copy()
        keys_to_remove = [k for k in env.keys() if 'PYCHARM' in k.upper() or 'JETBRAINS' in k.upper()]
        for key in keys_to_remove:
            del env[key]

        if 'PYTHONSTARTUP' in env:
            del env['PYTHONSTARTUP']

        try:
            logger.info("⏳ Validazione Fast Downward...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.fd_path.parent,
                env=env
            )

            output = result.stdout + "\n" + result.stderr

            if "Solution found!" in output:
                plan_path = self.fd_path.parent / "sas_plan"
                if plan_path.exists():
                    with open(plan_path, 'r') as f:
                        plan = f.read()
                    return True, "Piano trovato!", plan

            return False, self._extract_errors(output), output

        except subprocess.TimeoutExpired:
            return False, "Timeout (120s)", ""
        except Exception as e:
            return False, f"Errore: {e}", ""

    def _extract_errors(self, output: str) -> str:
        """Estrae errori rilevanti"""
        if "unsolvable" in output.lower():
            return "Problema non risolvibile - controlla che init permetta di raggiungere goal"

        error_lines = []
        for line in output.split('\n'):
            if any(kw in line.lower() for kw in ['error', 'failed', 'invalid']):
                if 'numpy' not in line.lower():
                    error_lines.append(line.strip())

        return '\n'.join(error_lines[:10]) if error_lines else "Errore sconosciuto"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def call_ollama(prompt: str, system_prompt: str) -> str:
    """Chiama Ollama"""
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 2000}
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        return response.json().get('response', '').strip()
    except Exception as e:
        logger.error(f"Errore Ollama: {e}")
        return ""


def check_ollama_available() -> bool:
    """Verifica Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


# =============================================================================
# MAIN
# =============================================================================

def generate_valid_pddl_v2(
        lore_path: Path,
        output_dir: Path,
        fd_path: str
) -> Tuple[bool, str]:
    """Pipeline template-based"""

    logger.info("=" * 70)
    logger.info("GENERAZIONE PDDL TEMPLATE-BASED")
    logger.info("=" * 70)

    # Genera da template
    generator = TemplatePDDLGenerator(lore_path, output_dir)
    success, msg = generator.generate()

    if not success:
        return False, "Generazione template fallita"

    # Valida con FD
    validator = FastDownwardValidator(fd_path)
    domain_path = output_dir / "domain.pddl"
    problem_path = output_dir / "problem.pddl"

    success, message, output = validator.validate(domain_path, problem_path)

    if success:
        logger.info("\n✅ SUCCESSO! PDDL valido generato")
        logger.info(f"📋 Piano:\n{message}")
        return True, "PDDL valido"
    else:
        logger.error(f"\n❌ Validazione fallita: {message}")
        return False, f"Errore validazione: {message}"


if __name__ == '__main__':
    SCRIPT_DIR = Path(__file__).resolve().parent

    LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"
    OUTPUT_FOLDER = SCRIPT_DIR / "pddl_output_v2"
    FAST_DOWNWARD = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"

    # Verifica prerequisiti
    if not check_ollama_available():
        print("❌ Ollama non disponibile!")
        exit(1)

    if not LORE_FILE.exists():
        print(f"❌ Lore non trovato: {LORE_FILE}")
        exit(1)

    if not Path(FAST_DOWNWARD).exists():
        print(f"❌ Fast Downward non trovato: {FAST_DOWNWARD}")
        exit(1)

    # Esegui
    success, message = generate_valid_pddl_v2(
        lore_path=LORE_FILE,
        output_dir=OUTPUT_FOLDER,
        fd_path=FAST_DOWNWARD
    )

    if success:
        print(f"\n🎉 {message}")
    else:
        print(f"\n😞 {message}")