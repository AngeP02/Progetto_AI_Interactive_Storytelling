
import os
import sys
import re
import json
import requests
import subprocess
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"



def call_ollama(prompt, system_prompt=""):
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 500
            }
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=500)
        response.raise_for_status()

        result = response.json()
        return result.get('response', '').strip()

    except requests.exceptions.RequestException as e:
        logger.error(f"Errore chiamata Ollama: {e}")
        return "Mi dispiace, sto avendo problemi tecnici. Riprova tra un momento."
    except Exception as e:
        logger.error(f"Errore generico: {e}")
        return "Si è verificato un errore imprevisto."

# =============================================================================
# STRATEGIA: TEMPLATE FISSI PRE-TESTATI + SCALING PARAMETRICO
# =============================================================================

class DifficultyLevel(Enum):
    """Livelli di difficoltà basati su depth"""
    EASY = "easy"  # 3-6 azioni
    MEDIUM = "medium"  # 7-12 azioni
    HARD = "hard"  # 13-25 azioni


@dataclass
class ValidatedPDDL:
    """PDDL pre-validato e testato"""
    domain: str
    problem: str
    expected_plan_length: int
    description: str


# =============================================================================
# LIBRERIA DI PDDL PRE-VALIDATI
# =============================================================================

class PDDLLibrary:
    """Libreria di PDDL garantiti validi e risolvibili"""

    @staticmethod
    def get_keys_doors_easy() -> ValidatedPDDL:
        """Quest breve: 2 location, 1 chiave"""
        domain = """(define (domain keys-doors-simple)
  (:requirements :strips :typing)
  (:types location key door agent)
  (:predicates
    (at ?a - agent ?l - location)
    (key-at ?k - key ?l - location)
    (has-key ?a - agent ?k - key)
    (door-between ?d - door ?l1 ?l2 - location)
    (locked ?d - door)
    (unlocks ?k - key ?d - door)
  )

  (:action move
   :parameters (?a - agent ?from ?to - location ?d - door)
   :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d)))
   :effect (and (not (at ?a ?from)) (at ?a ?to))
  )

  (:action pick-key
   :parameters (?a - agent ?k - key ?l - location)
   :precondition (and (at ?a ?l) (key-at ?k ?l))
   :effect (and (not (key-at ?k ?l)) (has-key ?a ?k))
  )

  (:action unlock
   :parameters (?a - agent ?k - key ?d - door ?l - location)
   :precondition (and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d))
   :effect (not (locked ?d))
  )
)"""

        problem = """(define (problem quest-easy)
  (:domain keys-doors-simple)
  (:objects
    room1 room2 - location
    hero - agent
    silver_key - key
    main_door - door
  )
  (:init
    (at hero room1)
    (key-at silver_key room1)
    (door-between main_door room1 room2)
    (locked main_door)
    (unlocks silver_key main_door)
  )
  (:goal
    (at hero room2)
  )
)"""
        return ValidatedPDDL(domain, problem, 3, "Easy: 2 rooms, 1 key")

    @staticmethod
    def get_keys_doors_medium() -> ValidatedPDDL:
        """Quest media: 4 location, 2 chiavi"""
        domain = """(define (domain keys-doors-simple)
  (:requirements :strips :typing)
  (:types location key door agent)
  (:predicates
    (at ?a - agent ?l - location)
    (key-at ?k - key ?l - location)
    (has-key ?a - agent ?k - key)
    (door-between ?d - door ?l1 ?l2 - location)
    (locked ?d - door)
    (unlocks ?k - key ?d - door)
  )

  (:action move
   :parameters (?a - agent ?from ?to - location ?d - door)
   :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d)))
   :effect (and (not (at ?a ?from)) (at ?a ?to))
  )

  (:action pick-key
   :parameters (?a - agent ?k - key ?l - location)
   :precondition (and (at ?a ?l) (key-at ?k ?l))
   :effect (and (not (key-at ?k ?l)) (has-key ?a ?k))
  )

  (:action unlock
   :parameters (?a - agent ?k - key ?d - door ?l - location)
   :precondition (and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d))
   :effect (not (locked ?d))
  )
)"""

        problem = """(define (problem quest-medium)
  (:domain keys-doors-simple)
  (:objects
    entrance hall treasure_room secret_chamber - location
    hero - agent
    bronze_key golden_key - key
    main_door treasure_door - door
  )
  (:init
    (at hero entrance)
    (key-at bronze_key entrance)
    (key-at golden_key hall)

    (door-between main_door entrance hall)
    (door-between treasure_door hall treasure_room)

    (locked main_door)
    (locked treasure_door)

    (unlocks bronze_key main_door)
    (unlocks golden_key treasure_door)
  )
  (:goal
    (at hero treasure_room)
  )
)"""
        return ValidatedPDDL(domain, problem, 7, "Medium: 4 rooms, 2 keys")

    @staticmethod
    def get_keys_doors_hard() -> ValidatedPDDL:
        """Quest lunga: 6 location, 4 chiavi"""
        domain = """(define (domain keys-doors-simple)
  (:requirements :strips :typing)
  (:types location key door agent)
  (:predicates
    (at ?a - agent ?l - location)
    (key-at ?k - key ?l - location)
    (has-key ?a - agent ?k - key)
    (door-between ?d - door ?l1 ?l2 - location)
    (locked ?d - door)
    (unlocks ?k - key ?d - door)
  )

  (:action move
   :parameters (?a - agent ?from ?to - location ?d - door)
   :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d)))
   :effect (and (not (at ?a ?from)) (at ?a ?to))
  )

  (:action pick-key
   :parameters (?a - agent ?k - key ?l - location)
   :precondition (and (at ?a ?l) (key-at ?k ?l))
   :effect (and (not (key-at ?k ?l)) (has-key ?a ?k))
  )

  (:action unlock
   :parameters (?a - agent ?k - key ?d - door ?l - location)
   :precondition (and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d))
   :effect (not (locked ?d))
  )
)"""

        problem = """(define (problem quest-hard)
  (:domain keys-doors-simple)
  (:objects
    entrance courtyard armory library vault throne_room - location
    hero - agent
    copper_key silver_key golden_key master_key - key
    gate1 gate2 gate3 gate4 - door
  )
  (:init
    (at hero entrance)

    (key-at copper_key entrance)
    (key-at silver_key courtyard)
    (key-at golden_key armory)
    (key-at master_key library)

    (door-between gate1 entrance courtyard)
    (door-between gate2 courtyard armory)
    (door-between gate3 armory library)
    (door-between gate4 library throne_room)

    (locked gate1)
    (locked gate2)
    (locked gate3)
    (locked gate4)

    (unlocks copper_key gate1)
    (unlocks silver_key gate2)
    (unlocks golden_key gate3)
    (unlocks master_key gate4)
  )
  (:goal
    (at hero throne_room)
  )
)"""
        return ValidatedPDDL(domain, problem, 16, "Hard: 6 rooms, 4 keys")

    @staticmethod
    def get_logistics_easy() -> ValidatedPDDL:
        """Logistics semplice: 3 location, 1 package"""
        domain = """(define (domain logistics-simple)
  (:requirements :strips :typing)
  (:types location vehicle package)
  (:predicates
    (at-vehicle ?v - vehicle ?l - location)
    (at-package ?p - package ?l - location)
    (in-vehicle ?p - package ?v - vehicle)
    (connected ?from ?to - location)
  )

  (:action move
   :parameters (?v - vehicle ?from ?to - location)
   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to))
   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to))
  )

  (:action load
   :parameters (?p - package ?v - vehicle ?l - location)
   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l))
   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v))
  )

  (:action unload
   :parameters (?p - package ?v - vehicle ?l - location)
   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l))
   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l))
  )
)"""

        problem = """(define (problem delivery-easy)
  (:domain logistics-simple)
  (:objects
    warehouse shop home - location
    truck - vehicle
    parcel - package
  )
  (:init
    (at-vehicle truck warehouse)
    (at-package parcel warehouse)

    (connected warehouse shop)
    (connected shop warehouse)
    (connected shop home)
    (connected home shop)
  )
  (:goal
    (at-package parcel home)
  )
)"""
        return ValidatedPDDL(domain, problem, 5, "Easy logistics: deliver 1 package")

    @staticmethod
    def get_logistics_medium() -> ValidatedPDDL:
        """Logistics medio: 4 location, 2 packages"""
        domain = """(define (domain logistics-simple)
  (:requirements :strips :typing)
  (:types location vehicle package)
  (:predicates
    (at-vehicle ?v - vehicle ?l - location)
    (at-package ?p - package ?l - location)
    (in-vehicle ?p - package ?v - vehicle)
    (connected ?from ?to - location)
  )

  (:action move
   :parameters (?v - vehicle ?from ?to - location)
   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to))
   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to))
  )

  (:action load
   :parameters (?p - package ?v - vehicle ?l - location)
   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l))
   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v))
  )

  (:action unload
   :parameters (?p - package ?v - vehicle ?l - location)
   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l))
   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l))
  )
)"""

        problem = """(define (problem delivery-medium)
  (:domain logistics-simple)
  (:objects
    warehouse depot shop home - location
    truck - vehicle
    package1 package2 - package
  )
  (:init
    (at-vehicle truck warehouse)
    (at-package package1 warehouse)
    (at-package package2 depot)

    (connected warehouse depot)
    (connected depot warehouse)
    (connected depot shop)
    (connected shop depot)
    (connected shop home)
    (connected home shop)
  )
  (:goal
    (and
      (at-package package1 home)
      (at-package package2 shop)
    )
  )
)"""
        return ValidatedPDDL(domain, problem, 11, "Medium logistics: deliver 2 packages")


# =============================================================================
# SELETTORE INTELLIGENTE
# =============================================================================

class SmartPDDLSelector:
    """Seleziona il PDDL pre-validato più adatto al lore"""

    def __init__(self, lore_content: str):
        self.lore = lore_content
        self.library = PDDLLibrary()

    def select_best_pddl(self) -> ValidatedPDDL:
        """Seleziona il PDDL migliore analizzando lore e constraint"""

        # Estrai informazioni chiave
        analysis = self._analyze_lore()

        logger.info(f"📊 Analisi Lore:")
        logger.info(f"   - Genere rilevato: {analysis['genre']}")
        logger.info(f"   - Depth target: {analysis['depth_min']}-{analysis['depth_max']}")
        logger.info(f"   - Difficoltà: {analysis['difficulty']}")

        # Seleziona template basato su genere
        if analysis['genre'] in ['fantasy', 'adventure', 'mystery']:
            template_type = 'keys_doors'
        else:
            template_type = 'logistics'

        # Seleziona difficoltà
        if analysis['difficulty'] == DifficultyLevel.EASY:
            if template_type == 'keys_doors':
                pddl = self.library.get_keys_doors_easy()
            else:
                pddl = self.library.get_logistics_easy()
        elif analysis['difficulty'] == DifficultyLevel.MEDIUM:
            if template_type == 'keys_doors':
                pddl = self.library.get_keys_doors_medium()
            else:
                pddl = self.library.get_logistics_medium()
        else:  # HARD
            if template_type == 'keys_doors':
                pddl = self.library.get_keys_doors_hard()
            else:
                pddl = self.library.get_logistics_medium()  # Fallback

        logger.info(f"✅ Selezionato: {pddl.description}")
        logger.info(f"   Piano atteso: ~{pddl.expected_plan_length} azioni")

        return pddl

    def _analyze_lore(self) -> Dict:
        """Analizza il lore per estrarre constraint"""
        lore_lower = self.lore.lower()

        match = re.search(r'genere[:\s]*([^\n|]+)', self.lore, re.IGNORECASE)
        if match:
            genre = match.group(1).strip()
            logger.info(f"🎭 Genere rilevato dal testo: {genre}")
        else:
            # === 2️⃣ Fallback: uso LLM per classificarlo ===
            prompt = f"""
            Read the following story and identify its genre.
            Choose exactly one from this list:
            ["Fantasy", "Romance", "Drama", "Horror", "Comedy", "Science Fiction", "Mystery", "Historical", "Adventure"].
            Respond only with the single word of the genre.
        
            STORY:
            {self.lore}
            """
            system_prompt = "You are a text classification model that identifies the literary genre of a given story."
            result = call_ollama(prompt, system_prompt)

            if result:
                genre = result.strip().lower()
                logger.info(f"🎭 Genere rilevato da LLM: {genre}")
            else:
                genre = "generic"
                logger.warning("⚠️ Nessuna risposta valida da Ollama, uso 'generic'.")

        # Estrai depth constraint
        depth_min, depth_max = 5, 10  # Default

        # Cerca pattern "depth" o "azioni"
        depth_patterns = [
            r'depth[:\s]+(\d+)\s*-\s*(\d+)',
            r'(\d+)\s*-\s*(\d+)\s+azioni',
            r'min[:\s]+(\d+).*max[:\s]+(\d+)',
        ]

        for pattern in depth_patterns:
            match = re.search(pattern, lore_lower)
            if match:
                depth_min = int(match.group(1))
                depth_max = int(match.group(2))
                break

        # Cerca sezioni specifiche nel lore
        depth_section = re.search(r'depth constraints.*?(\d+)\s*-\s*(\d+)', lore_lower, re.DOTALL)
        if depth_section:
            depth_min = int(depth_section.group(1))
            depth_max = int(depth_section.group(2))

        # Determina difficoltà
        if depth_max <= 3:
            difficulty = DifficultyLevel.EASY
        elif depth_max <= 5:
            difficulty = DifficultyLevel.MEDIUM
        else:
            difficulty = DifficultyLevel.HARD

        return {
            'genre': genre,
            'depth_min': depth_min,
            'depth_max': depth_max,
            'difficulty': difficulty
        }


# =============================================================================
# PERSONALIZZATORE (OPZIONALE - RINOMINA ENTITÀ)
# =============================================================================

class PDDLPersonalizer:
    """Personalizza i nomi nel PDDL mantenendo la struttura valida"""

    def __init__(self, lore_content: str):
        self.lore = lore_content

    def personalize(self, pddl: ValidatedPDDL) -> ValidatedPDDL:
        """Sostituisce nomi generici con nomi dal lore"""

        # Estrai nomi dal lore
        names = self._extract_names()

        if not names['locations'] or not names['characters']:
            logger.info("ℹ️  Nomi insufficienti nel lore, uso template originale")
            return pddl

        logger.info(f"🎨 Personalizzo PDDL con nomi dal lore...")

        # Crea mapping
        domain_personalized = pddl.domain
        problem_personalized = pddl.problem

        # Sostituisci nomi location (solo nel problem)
        if 'keys-doors' in pddl.problem:
            location_mapping = self._create_location_mapping_keys_doors(names['locations'])
            for old, new in location_mapping.items():
                problem_personalized = problem_personalized.replace(old, new)

        # Sostituisci nome agente
        if names['characters']:
            hero_name = self._sanitize_name(names['characters'][0])
            problem_personalized = problem_personalized.replace('hero', hero_name)

        logger.info(
            f"✓ PDDL personalizzato con {len(names['locations'])} location e {len(names['characters'])} personaggi")

        return ValidatedPDDL(
            domain_personalized,
            problem_personalized,
            pddl.expected_plan_length,
            pddl.description + " (personalizzato)"
        )

    def _extract_names(self) -> Dict[str, List[str]]:
        """Estrae nomi dal lore usando regex"""

        # Cerca nomi propri (maiuscoli)
        all_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', self.lore)

        # Filtra comuni
        common_words = {'The', 'A', 'An', 'I', 'You', 'He', 'She', 'They', 'We'}
        all_names = [n for n in all_names if n not in common_words]

        # Separa location da personaggi (euristico)
        locations = []
        characters = []

        for name in all_names[:10]:  # Max 10
            if any(kw in name.lower() for kw in ['room', 'hall', 'tower', 'cave', 'forest', 'lab', 'district']):
                locations.append(name)
            else:
                characters.append(name)

        return {
            'locations': locations[:6],  # Max 6 location
            'characters': characters[:3]  # Max 3 personaggi
        }

    def _create_location_mapping_keys_doors(self, lore_locations: List[str]) -> Dict[str, str]:
        """Crea mapping location generiche -> location dal lore"""

        generic = ['entrance', 'courtyard', 'armory', 'library', 'vault', 'throne_room',
                   'room1', 'room2', 'hall', 'treasure_room', 'secret_chamber']

        mapping = {}
        for i, gen in enumerate(generic):
            if i < len(lore_locations):
                new_name = self._sanitize_name(lore_locations[i])
                mapping[gen] = new_name

        return mapping

    def _sanitize_name(self, name: str) -> str:
        """Pulisce nome per PDDL"""
        name = name.lower().strip()
        name = re.sub(r'[^a-z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name)
        return name.strip('_')


# =============================================================================
# VALIDATORE FAST DOWNWARD
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

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.fd_path.parent,
                env=env
            )

            output = result.stdout + "\n" + result.stderr

            if "Solution found!" in output or "Plan found!" in output:
                possible_locations = [
                    self.fd_path.parent / "sas_plan",
                    Path.cwd() / "sas_plan",
                    domain_path.parent / "sas_plan"
                ]

                plan_content = None

                for plan_path in possible_locations:
                    if plan_path.exists():
                        with open(plan_path, 'r') as f:
                            plan_content = f.read()
                        break

                if plan_content:
                    if save_plan_to:
                        output_plan_path = save_plan_to / "sas_plan"
                        with open(output_plan_path, 'w') as f:
                            f.write(plan_content)

                        readable_plan_path = save_plan_to / "plan_readable.txt"
                        readable_plan = self._make_plan_readable(plan_content)
                        with open(readable_plan_path, 'w') as f:
                            f.write(readable_plan)

                        logger.info(f"✓ Piano salvato in: {readable_plan_path}")

                    return True, plan_content, output
                else:
                    return True, "Soluzione trovata", output

# nessuna soluzione trovata, uso reflection agent

            logger.warning("⚠️ Nessuna soluzione trovata — avvio Reflection Agent per rigenerare il piano...")

            try:
                reflection_result = self.run_reflection_agent(domain_path, problem_path)
                if reflection_result:
                    # Dopo il reflection, riesegui Fast Downward
                    logger.info("🔁 Riprovo la validazione dopo Reflection Agent...")
                    return self.validate(domain_path, problem_path, save_plan_to)
                else:
                    logger.error("❌ Reflection Agent non ha generato un nuovo piano valido.")
                    return False, "Reflection fallita: nessuna soluzione trovata", output

            except Exception as e:
                logger.exception("Errore durante il reflection agent")
                return False, f"Errore reflection: {e}", output

        except subprocess.TimeoutExpired:
            return False, "Timeout (60s)", ""
        except Exception as e:
            logger.exception("Errore validazione")
            return False, f"Errore: {e}", ""

    def run_reflection_agent(self, domain_path: Path, problem_path: Path) -> bool:
        """
        Esegue il Reflection Agent:
        - Analizza i file PDDL esistenti
        - Usa LLM per identificare problemi di validità
        - Propone e applica correzioni
        - Restituisce True se è riuscito a rigenerare un piano plausibile
        """
        try:
            logger.info("🧠 Avvio Reflection Agent per analizzare i file PDDL...")

            # 1️⃣ Leggi i file
            with open(domain_path, "r", encoding="utf-8") as f:
                domain_content = f.read()
            with open(problem_path, "r", encoding="utf-8") as f:
                problem_content = f.read()

            # 2️⃣ Costruisci il prompt per Ollama o LLM
            system_prompt = (
                "You are a PDDL expert. Your task is to analyze a domain and problem definition "
                "that failed to produce a valid plan in Fast Downward. You must identify structural "
                "or logical issues (missing preconditions, inconsistent goals, impossible actions) "
                "and produce a corrected version that is still faithful to the original scenario."
            )

            user_prompt = f"""
            The following PDDL domain and problem did not yield any valid plan.

            === DOMAIN ===
            {domain_content}

            === PROBLEM ===
            {problem_content}

            Please:
            1. Identify the most likely issue preventing plan generation.
            2. Modify the PDDL minimally to fix the issue.
            3. Keep the syntax strictly valid and consistent with Fast Downward requirements.
            4. Return only the corrected domain and problem, formatted as:
               ---DOMAIN---
               <corrected domain>
               ---PROBLEM---
               <corrected problem>
            """

            # 3️⃣ Chiamata all’LLM locale (Ollama)
            response = call_ollama(user_prompt, system_prompt)

            # 4️⃣ Estrai le nuove sezioni
            domain_fixed, problem_fixed = None, None

            match_domain = re.search(r"---DOMAIN---(.*?)---PROBLEM---", response, re.DOTALL)
            match_problem = re.search(r"---PROBLEM---(.*)", response, re.DOTALL)

            if match_domain and match_problem:
                domain_fixed = match_domain.group(1).strip()
                problem_fixed = match_problem.group(1).strip()

            if not domain_fixed or not problem_fixed:
                logger.error("❌ Il Reflection Agent non ha restituito un PDDL valido.")
                return False

            # 5️⃣ Sovrascrivi i file
            with open(domain_path, "w", encoding="utf-8") as f:
                f.write(domain_fixed)
            with open(problem_path, "w", encoding="utf-8") as f:
                f.write(problem_fixed)

            logger.info("✨ Reflection Agent completato: file PDDL aggiornati.")
            return True

        except Exception as e:
            logger.exception("Errore nel Reflection Agent")
            return False

    def _make_plan_readable(self, plan_content: str) -> str:
        """Converte il piano in formato leggibile"""
        lines = plan_content.strip().split('\n')
        readable = ["=" * 60, "PIANO DI AZIONI", "=" * 60, ""]

        step = 1
        for line in lines:
            line = line.strip()
            if line and not line.startswith(';'):
                action = line.strip('()')
                readable.append(f"Step {step}: {action}")
                step += 1

        readable.append("")
        readable.append("=" * 60)
        readable.append(f"Piano completato in {step - 1} passi")
        readable.append("=" * 60)

        return '\n'.join(readable)

def generate_valid_pddl_guaranteed(
        lore_path: Path,
        output_dir: Path,
        fd_path: str,
        personalize: bool = True
) -> Tuple[bool, str]:
    """
    Pipeline GARANTITA per generare PDDL validi

    Strategia:
    1. Usa template pre-testati (100% validi)
    2. Seleziona in base al lore
    3. Opzionalmente personalizza i nomi
    4. Valida sempre con Fast Downward
    """

    logger.info("=" * 70)
    logger.info("GENERAZIONE PDDL - STRATEGIA GARANTITA")
    logger.info("Usa template pre-validati + personalizzazione sicura")
    logger.info("=" * 70)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Leggi lore
    with open(lore_path, 'r', encoding='utf-8') as f:
        lore_content = f.read()

    # STEP 1: Seleziona template pre-validato
    logger.info("\n📋 STEP 1: Selezione template pre-validato...")
    selector = SmartPDDLSelector(lore_content)
    pddl = selector.select_best_pddl()

    # STEP 2: Personalizza (opzionale)
    if personalize:
        logger.info("\n🎨 STEP 2: Personalizzazione nomi...")
        personalizer = PDDLPersonalizer(lore_content)
        pddl = personalizer.personalize(pddl)
    else:
        logger.info("\n⏭️  STEP 2: Skip personalizzazione")

    # STEP 3: Salva file
    logger.info("\n💾 STEP 3: Salvataggio file...")
    domain_path = output_dir / "domain.pddl"
    problem_path = output_dir / "problem.pddl"

    with open(domain_path, 'w') as f:
        f.write(pddl.domain)
    with open(problem_path, 'w') as f:
        f.write(pddl.problem)

    logger.info(f"✓ File salvati in: {output_dir}")

    # STEP 4: Validazione (sanity check)
    logger.info("\n✅ STEP 4: Validazione finale...")
    validator = FastDownwardValidator(fd_path)
    success, message, output = validator.validate(domain_path, problem_path, save_plan_to=output_dir)

    if success:
        logger.info("\n🎉 SUCCESSO GARANTITO!")
        logger.info(f"📂 File generati:")
        logger.info(f"   - Domain: {domain_path}")
        logger.info(f"   - Problem: {problem_path}")
        logger.info(f"   - Piano: {output_dir / 'plan_readable.txt'}")

        # === Nuovo step: Aggiunta commenti ===
        aggiunta_commenti_LLM(domain_path, problem_path)

        return True, "PDDL valido garantito"
    else:
        logger.error(f"\n⚠️  Validazione fallita (imprevisto): {message}")
        return False, f"Errore validazione: {message}"


def aggiunta_commenti_LLM(domain_path: Path, problem_path: Path):
    domain_text = domain_path.read_text(encoding="utf-8")
    problem_text = problem_path.read_text(encoding="utf-8")

    # === Prompt LLM ===
    system_prompt = """You are an expert in AI planning and PDDL (Planning Domain Definition Language).
    Your task is to annotate PDDL files with clear and concise inline comments.
    Do NOT change or reorder any line, and do not remove parentheses.
    Each comment must be in the same line, preceded by a semicolon (;).
    Keep the comments short, clear, and descriptive in natural language.
    """

    prompt_template = """Below is a PDDL file. 
    Add a short inline comment to every line, explaining what that line does in plain English.
    Do NOT alter the structure, spacing, or syntax.
    Only add comments at the end of lines, using ';' as the comment marker.
    Return ONLY the annotated PDDL, nothing else.

    PDDL FILE:
    {content}

    bash
    Copia codice
    """

    # === Genera versioni commentate ===
    print("💬 Aggiunta commenti al domain...")
    domain_commented = call_ollama(
        prompt_template.format(content=domain_text),
        system_prompt
    )

    print("💬 Aggiunta commenti al problem...")
    problem_commented = call_ollama(
        prompt_template.format(content=problem_text),
        system_prompt
    )

    if not domain_commented or not problem_commented:
        print("❌ Impossibile generare i file commentati. Controlla Ollama.")
        return None

    # === Salvataggio ===
    domain_out = domain_path.parent / f"{domain_path.stem}_commented.pddl"
    problem_out = problem_path.parent / f"{problem_path.stem}_commented.pddl"

    domain_out.write_text(domain_commented, encoding="utf-8")
    problem_out.write_text(problem_commented, encoding="utf-8")

    print(f"✅ File commentati salvati in:\n   - {domain_out}\n   - {problem_out}")
    return domain_out, problem_out

if __name__ == '__main__':
    SCRIPT_DIR = Path(__file__).resolve().parent

    LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"
    OUTPUT_FOLDER = SCRIPT_DIR / "pddl_output_guaranteed"
    FAST_DOWNWARD = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"

    # Verifica prerequisiti
    if not LORE_FILE.exists():
        print(f"❌ Lore non trovato: {LORE_FILE}")
        exit(1)

    if not Path(FAST_DOWNWARD).exists():
        print(f"❌ Fast Downward non trovato: {FAST_DOWNWARD}")
        exit(1)

    # Esegui
    print("\n🚀 Generazione PDDL GARANTITA...\n")

    success, message = generate_valid_pddl_guaranteed(
        lore_path=LORE_FILE,
        output_dir=OUTPUT_FOLDER,
        fd_path=FAST_DOWNWARD,
        personalize=True  # Cambia a False per usare template puri
    )
    print(message)