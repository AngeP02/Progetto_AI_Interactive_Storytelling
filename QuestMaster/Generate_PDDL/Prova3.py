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
Output ONLY valid JSON, no explanations.
IMPORTANT: Use double quotes for strings, not single quotes. Escape any quotes inside strings."""

        prompt = f"""Analyze this narrative and extract:

LORE:
{self.lore}

Extract as JSON (use double quotes, escape internal quotes):
{{
  "agents": ["list of characters/robots/entities that can act"],
  "locations": ["list of places"],
  "objects": ["list of items/objects"],
  "connections": [["loc1", "loc2"], ...],
  "initial_facts": ["entity is at location", ...],
  "goal_facts": ["desired final state", ...]
}}

IMPORTANT: 
- Be concrete and specific. Extract actual names from the lore.
- Use ONLY double quotes in JSON
- Replace single quotes with double quotes if needed
OUTPUT ONLY JSON:"""

        response = call_ollama(prompt, system_prompt)

        if not response:
            logger.warning("LLM non ha risposto, uso fallback")
            return self._fallback_extraction()

        try:
            # Pulisci response da markdown
            response = re.sub(r'```json\n?', '', response)
            response = re.sub(r'```\n?', '', response)

            # FIX: Gestisci apostrofi e quote problematiche
            # Sostituisci apostrofi singoli con escaped se dentro stringhe JSON
            response = response.replace("\\'", "'")  # Rimuovi escape già presenti
            response = response.replace("'", "\\'")  # Re-escape per JSON

            # Prova parsing
            data = json.loads(response)

            # Valida struttura
            if not isinstance(data, dict):
                logger.warning(f"LLM ha ritornato tipo non valido: {type(data)}")
                return self._fallback_extraction()

            # Log per debug
            logger.info(f"✓ JSON parsato correttamente")
            logger.debug(f"Entità estratte: {json.dumps(data, indent=2)}")

            return data

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing fallito: {e}")
            logger.warning(f"Response LLM: {response[:200]}...")

            # Prova fix automatico per JSON malformato
            try:
                fixed_json = self._try_fix_json(response)
                if fixed_json:
                    logger.info("✓ JSON riparato con successo")
                    return fixed_json
            except:
                pass

            return self._fallback_extraction()
        except Exception as e:
            logger.error(f"Errore inaspettato: {e}")
            return self._fallback_extraction()

    def _try_fix_json(self, broken_json: str) -> Optional[Dict]:
        """Tenta di riparare JSON malformato"""
        import ast

        # Rimuovi trailing comma
        broken_json = re.sub(r',\s*([}\]])', r'\1', broken_json)

        # Sostituisci apostrofi singoli con doppi (ma non quelli dentro stringhe)
        # Questo è un fix aggressivo ma spesso funziona
        broken_json = broken_json.replace("'", '"')

        try:
            return json.loads(broken_json)
        except:
            # Ultimo tentativo: eval Python (pericoloso ma controllato)
            try:
                # Rimuovi possibili problemi
                broken_json = broken_json.strip()
                if broken_json.startswith('{') and broken_json.endswith('}'):
                    # Usa ast.literal_eval che è più sicuro di eval
                    data = ast.literal_eval(broken_json)
                    if isinstance(data, dict):
                        return data
            except:
                pass

        return None

    def _fallback_extraction(self) -> Dict:
        """Estrazione regex-based se LLM fallisce"""
        logger.warning("⚠️ Fallback: estrazione regex-based")

        # Estrai nomi propri (maiuscoli)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', self.lore)

        # Rimuovi duplicati mantenendo ordine
        seen = set()
        unique_entities = []
        for e in entities:
            e_lower = e.lower()
            # Ignora parole comuni
            if e_lower not in seen and e_lower not in {'the', 'a', 'an', 'i', 'you', 'he', 'she'}:
                seen.add(e_lower)
                unique_entities.append(e)

        # Estrai location keywords
        location_keywords = ['tower', 'room', 'hall', 'chamber', 'cave', 'forest',
                             'castle', 'town', 'village', 'lab', 'laboratory', 'shop',
                             'square', 'market', 'street', 'avenue', 'plaza']
        locations = []

        for keyword in location_keywords:
            # Cerca pattern "Nome + keyword" o "keyword + Nome"
            pattern = rf'\b([A-Z][\w\s]*{keyword}|{keyword}[\w\s]*[A-Z]\w*)\b'
            matches = re.findall(pattern, self.lore, re.IGNORECASE)
            for match in matches[:2]:  # Max 2 per keyword
                cleaned = match.strip()
                if len(cleaned) > 3 and cleaned not in locations:
                    locations.append(cleaned)

        # Se non troviamo location con pattern, usa entità come location
        if not locations and unique_entities:
            locations = unique_entities[:4]

        # Fallback assoluto
        if not locations:
            locations = ['start_location', 'middle_location', 'destination', 'secret_place']

        # Agenti: primi 2-3 nomi propri non usati come location
        agents = [e for e in unique_entities if e not in locations][:3]
        if not agents:
            agents = ['hero', 'protagonist']

        # Connessioni: crea grafo lineare
        connections = []
        if len(locations) > 1:
            connections = [[locations[i], locations[i + 1]] for i in range(min(3, len(locations) - 1))]

        result = {
            "agents": agents,
            "locations": locations[:4],  # Max 4 location
            "objects": ["key", "map"],  # Default objects
            "connections": connections,
            "initial_facts": [],
            "goal_facts": []
        }

        logger.info(f"✓ Fallback extraction: {len(result['agents'])} agents, "
                    f"{len(result['locations'])} locations, {len(result['connections'])} connections")

        return result

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

        # Assicura almeno 2 location
        if len(locations) < 2:
            logger.warning(f"⚠️ Solo {len(locations)} location trovate, aggiungo default")
            locations.extend([f'location{i}' for i in range(2 - len(locations))])

        # Sanitizza nomi (rimuovi spazi, lowercase)
        agents = [self._sanitize_name(a) for a in agents]
        locations = [self._sanitize_name(l) for l in locations]
        objects = [self._sanitize_name(o) for o in objects]

        # CRITICAL: Pre-calcola connessioni (necessario per objects section)
        self._cached_connections = self._get_connections(locations)

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
            # CRITICAL FIX: genera chiavi e porte in modo intelligente
            connections = self._get_connections(locations)

            # Numero di chiavi = numero connessioni - 1 (una connessione libera)
            keys_needed = max(1, len(set(connections)) // 2 - 1)  # Diviso 2 perché bidirezionali
            keys = objects[:keys_needed] if len(objects) >= keys_needed else [f"key{i}" for i in range(keys_needed)]

            # Numero porte = numero connessioni uniche
            num_doors = len(set(connections)) // 2
            doors = [f"door{i}" for i in range(num_doors)]

            logger.info(f"✓ Objects: {len(locations)} locations, 1 agent, {len(keys)} keys, {len(doors)} doors")

            return f"""(:objects
    {' '.join(locations)} - location
    {agents[0]} - agent
    {' '.join(keys)} - key
    {' '.join(doors)} - door
  )"""

        return "(:objects )"

    def _build_init_section(self, agents, locations, objects) -> str:
        """Costruisce stato iniziale usando i fatti estratti dall'LLM"""

        init_facts = []

        if self.template.domain_name == "logistics":
            vehicles = agents[:2] if len(agents) >= 2 else agents
            packages = objects[:3] if objects else ["package1"]

            # Usa initial_facts se disponibili
            agent_positions = self._extract_agent_positions()

            # Veicoli alle posizioni estratte o default
            for i, v in enumerate(vehicles):
                pos = agent_positions.get(v, locations[i % len(locations)])
                init_facts.append(f"    (at {v} {pos})")

            # Packages all'ultima location
            for p in packages:
                init_facts.append(f"    (at {p} {locations[-1]})")

            # Usa connessioni estratte dall'LLM
            connections = self._get_connections(locations)
            for from_loc, to_loc in connections:
                init_facts.append(f"    (connected {from_loc} {to_loc})")

        elif self.template.domain_name == "grid-navigation":
            agent_positions = self._extract_agent_positions()
            start_pos = agent_positions.get(agents[0], locations[0])

            # Agente alla posizione estratta
            init_facts.append(f"    (at {agents[0]} {start_pos})")

            # Tutte le altre posizioni clear
            for loc in locations:
                if loc != start_pos:
                    init_facts.append(f"    (clear {loc})")

            # Goal position dall'LLM o default
            goal_pos = self._extract_goal_location() or locations[-1]
            init_facts.append(f"    (goal-pos {goal_pos})")

            # Usa connessioni estratte
            connections = self._get_connections(locations)
            for from_loc, to_loc in connections:
                init_facts.append(f"    (adjacent {from_loc} {to_loc})")

        elif self.template.domain_name == "keys-doors":
            # CRITICAL FIX: Rendi il problema SEMPRE risolvibile

            # 1. Posizione iniziale agente
            agent_positions = self._extract_agent_positions()
            start_pos = agent_positions.get(agents[0], locations[0])
            init_facts.append(f"    (at {agents[0]} {start_pos})")

            # 2. Ottieni connessioni reali dall'LLM
            connections = self._get_connections(locations)

            # Se non ci sono connessioni, crea una topologia semplice
            if not connections:
                logger.warning("⚠️ Nessuna connessione estratta, creo topologia lineare")
                connections = [(locations[i], locations[i + 1]) for i in range(len(locations) - 1)]

            # 3. Genera chiavi e porte SOLO per connessioni che ne hanno bisogno
            # Strategia: lascia almeno UN percorso senza porte (per garantire risolvibilità)
            keys_needed = max(1, len(connections) - 1)  # -1 per lasciare un percorso libero
            keys = objects[:keys_needed] if objects else [f"key{i}" for i in range(keys_needed)]

            # 4. Crea porte solo per ALCUNE connessioni (non tutte)
            doors_created = 0
            free_connection_created = False

            for i, (from_loc, to_loc) in enumerate(connections):
                door_name = f"door{i}"

                # Prima connessione SEMPRE libera (senza porta) per garantire movimento iniziale
                if not free_connection_created:
                    init_facts.append(f"    (door-between {door_name} {from_loc} {to_loc})")
                    # Porta NON locked (o non crearla proprio)
                    free_connection_created = True
                elif doors_created < keys_needed:
                    # Aggiungi porta locked solo se abbiamo chiavi
                    init_facts.append(f"    (door-between {door_name} {from_loc} {to_loc})")
                    init_facts.append(f"    (locked {door_name})")

                    # Associa chiave a porta
                    key = keys[doors_created]
                    init_facts.append(f"    (unlocks {key} {door_name})")

                    # Posiziona chiave in una location accessibile
                    # CRITICAL: la chiave deve essere raggiungibile PRIMA della porta
                    key_location = from_loc if from_loc != start_pos else locations[0]
                    init_facts.append(f"    (key-at {key} {key_location})")

                    doors_created += 1
                else:
                    # Altre porte senza lock
                    init_facts.append(f"    (door-between {door_name} {from_loc} {to_loc})")

            logger.info(f"✓ Template keys-doors: {len(keys)} chiavi, {doors_created} porte locked, "
                        f"percorso iniziale libero da {start_pos}")

        return "\n".join(init_facts)

    def _extract_agent_positions(self) -> Dict[str, str]:
        """Estrae posizioni iniziali agenti dai fatti LLM"""
        positions = {}

        initial_facts = self.entities.get('initial_facts', [])
        for fact in initial_facts:
            if isinstance(fact, dict):
                agent = fact.get('agent', '')
                location = fact.get('location', '')
                if agent and location:
                    agent_clean = self._sanitize_name(agent)
                    loc_clean = self._sanitize_name(location)
                    positions[agent_clean] = loc_clean

        return positions

    def _extract_goal_location(self) -> Optional[str]:
        """Estrae location goal dai fatti LLM"""
        goal_facts = self.entities.get('goal_facts', [])

        for fact in goal_facts:
            if isinstance(fact, dict):
                # Cerca keyword di location nei goal
                fact_text = str(fact).lower()
                for loc in self.entities.get('locations', []):
                    loc_name = loc if isinstance(loc, str) else loc.get('name', '')
                    if loc_name.lower() in fact_text:
                        return self._sanitize_name(loc_name)

        return None

    def _get_connections(self, locations: List[str]) -> List[Tuple[str, str]]:
        """Estrae connessioni reali dall'LLM o genera fallback intelligente"""
        connections_list = []

        # Prova a usare connessioni estratte
        connections_raw = self.entities.get('connections', [])

        for conn in connections_raw:
            if isinstance(conn, list) and len(conn) >= 2:
                from_loc = conn[0] if isinstance(conn[0], str) else conn[0].get('name', '')
                to_loc = conn[1] if isinstance(conn[1], str) else conn[1].get('name', '')

                if from_loc and to_loc:
                    from_clean = self._sanitize_name(from_loc)
                    to_clean = self._sanitize_name(to_loc)

                    # Aggiungi connessione bidirezionale
                    connections_list.append((from_clean, to_clean))
                    connections_list.append((to_clean, from_clean))

        # Se non ci sono connessioni estratte, crea grafo connesso minimo
        if not connections_list and len(locations) > 1:
            logger.warning("⚠️ Creando connessioni fallback")
            # Crea un percorso che connette tutte le location
            for i in range(len(locations) - 1):
                connections_list.append((locations[i], locations[i + 1]))
                connections_list.append((locations[i + 1], locations[i]))

        # Rimuovi duplicati
        connections_list = list(set(connections_list))

        logger.info(f"✓ Connessioni: {len(connections_list) // 2} bidirezionali")
        return connections_list

    def _build_goal_section(self, agents, locations, objects) -> str:
        """Costruisce goal usando fatti estratti dall'LLM"""

        if self.template.domain_name == "logistics":
            packages = objects[:3] if objects else ["package1"]

            # Cerca goal location nei fatti LLM
            goal_location = self._extract_goal_location()
            if not goal_location:
                # Fallback: prima location (delivery)
                goal_location = locations[0]

            # Goal: tutti i package alla location di destinazione
            goals = [f"(at {p} {goal_location})" for p in packages]
            return f"    (and {' '.join(goals)})"

        elif self.template.domain_name == "grid-navigation":
            # Goal: agente alla goal-pos (già definita in init)
            goal_location = self._extract_goal_location() or locations[-1]
            return f"    (at {agents[0]} {goal_location})"

        elif self.template.domain_name == "keys-doors":
            # Goal: agente raggiunge location di destinazione
            goal_location = self._extract_goal_location()

            if not goal_location:
                # Fallback intelligente: location più lontana dalla start
                agent_positions = self._extract_agent_positions()
                start_pos = agent_positions.get(agents[0], locations[0])

                # Prendi una location diversa dalla start
                goal_location = locations[-1] if locations[-1] != start_pos else locations[0]

            logger.info(f"✓ Goal: {agents[0]} deve raggiungere {goal_location}")
            return f"    (at {agents[0]} {goal_location})"

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

    def validate(self, domain_path: Path, problem_path: Path, save_plan_to: Optional[Path] = None) -> Tuple[
        bool, str, str]:
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
            logger.debug(f"   Comando: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.fd_path.parent,
                env=env
            )

            output = result.stdout + "\n" + result.stderr

            # Log completo per debug
            logger.debug("=" * 60)
            logger.debug("OUTPUT FAST DOWNWARD:")
            logger.debug(output)
            logger.debug("=" * 60)

            # Controlla se ha trovato soluzione
            if "Solution found!" in output or "Plan found!" in output:
                # Cerca il piano in diverse posizioni possibili
                possible_locations = [
                    self.fd_path.parent / "sas_plan",
                    Path.cwd() / "sas_plan",
                    domain_path.parent / "sas_plan"
                ]

                plan_content = None
                plan_found_at = None

                for plan_path in possible_locations:
                    logger.debug(f"Cercando piano in: {plan_path}")
                    if plan_path.exists():
                        with open(plan_path, 'r') as f:
                            plan_content = f.read()
                        plan_found_at = plan_path
                        logger.debug(f"✓ Piano trovato in: {plan_found_at}")
                        break

                if plan_content:
                    # Copia il piano nella directory output se richiesto
                    if save_plan_to:
                        output_plan_path = save_plan_to / "sas_plan"
                        with open(output_plan_path, 'w') as f:
                            f.write(plan_content)
                        logger.info(f"✓ Piano salvato in: {output_plan_path}")

                        # Crea anche una versione human-readable
                        readable_plan_path = save_plan_to / "plan_readable.txt"
                        readable_plan = self._make_plan_readable(plan_content)
                        with open(readable_plan_path, 'w') as f:
                            f.write(readable_plan)
                        logger.info(f"✓ Piano leggibile salvato in: {readable_plan_path}")

                    return True, plan_content, output
                else:
                    logger.warning("⚠️ Soluzione trovata ma file sas_plan non trovato")
                    logger.warning(f"   Cercato in: {[str(p) for p in possible_locations]}")
                    return True, "Soluzione trovata (file piano non disponibile)", output

            # Non ha trovato soluzione - estrai errori
            error_msg = self._extract_errors(output)

            # Se non abbiamo estratto nulla di utile, ritorna l'output completo troncato
            if error_msg == "Errore sconosciuto":
                # Prendi le ultime 50 righe dell'output per avere il contesto
                output_lines = output.split('\n')
                relevant_output = '\n'.join(output_lines[-50:])
                error_msg = f"Fast Downward fallito. Ultime righe output:\n{relevant_output}"

                # Log completo per debug
                logger.error("OUTPUT COMPLETO FAST DOWNWARD:")
                logger.error(output)

            return False, error_msg, output

        except subprocess.TimeoutExpired:
            return False, "Timeout (120s) - problema troppo complesso", ""
        except FileNotFoundError as e:
            return False, f"Fast Downward non trovato: {e}", ""
        except Exception as e:
            logger.exception("Errore durante validazione Fast Downward")
            return False, f"Errore esecuzione: {e}", ""

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

    def _make_plan_readable(self, plan_content: str) -> str:
        """Converte il piano in formato leggibile"""
        lines = plan_content.strip().split('\n')
        readable = ["=" * 60, "PIANO DI AZIONI", "=" * 60, ""]

        step = 1
        for line in lines:
            line = line.strip()
            if line and not line.startswith(';'):
                # Rimuovi parentesi e formatta
                action = line.strip('()')
                readable.append(f"Step {step}: {action}")
                step += 1

        readable.append("")
        readable.append("=" * 60)
        readable.append(f"Piano completato in {step - 1} passi")
        readable.append("=" * 60)

        return '\n'.join(readable)


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

    success, message, output = validator.validate(domain_path, problem_path, save_plan_to=output_dir)

    if success:
        logger.info("\n✅ SUCCESSO! PDDL valido generato")
        logger.info(f"📂 File salvati in: {output_dir}")
        logger.info(f"📋 Piano trovato - vedi: {output_dir / 'plan_readable.txt'}")
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
        print(f"📂 File generati:")
        print(f"   - Domain: {OUTPUT_FOLDER / 'domain.pddl'}")
        print(f"   - Problem: {OUTPUT_FOLDER / 'problem.pddl'}")
        print(f"   - Piano originale: {OUTPUT_FOLDER / 'sas_plan'}")
        print(f"   - Piano leggibile: {OUTPUT_FOLDER / 'plan_readable.txt'}")
    else:
        print(f"\n😞 {message}")