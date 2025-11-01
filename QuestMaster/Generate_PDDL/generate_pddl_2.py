import os
import re
import requests
import subprocess
import logging
from pathlib import Path
from typing import Tuple, List, Set, Dict
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


# =============================================================================
# 1. VALIDATORI E AUTO-FIX DETERMINISTICI
# =============================================================================

class PDDLValidator:
    """Validatore completo con auto-fix intelligente"""

    def __init__(self, domain_path: Path, problem_path: Path):
        self.domain_path = domain_path
        self.problem_path = problem_path
        self.domain_content = ""
        self.problem_content = ""
        self.errors = []

    def load_files(self):
        """Carica i file PDDL"""
        with open(self.domain_path, 'r', encoding='utf-8') as f:
            self.domain_content = f.read()
        with open(self.problem_path, 'r', encoding='utf-8') as f:
            self.problem_content = f.read()

    def save_files(self):
        """Salva i file corretti"""
        with open(self.domain_path, 'w', encoding='utf-8') as f:
            f.write(self.domain_content)
        with open(self.problem_path, 'w', encoding='utf-8') as f:
            f.write(self.problem_content)

    # =========================================================================
    # FIX 1: PARENTESI
    # =========================================================================

    def fix_parentheses(self, content: str) -> str:
        """Bilancia automaticamente le parentesi"""
        open_count = content.count('(')
        close_count = content.count(')')

        if open_count > close_count:
            content = content.rstrip() + ')' * (open_count - close_count)
            logger.info(f"Aggiunte {open_count - close_count} parentesi chiuse")
        elif close_count > open_count:
            for _ in range(close_count - open_count):
                idx = content.rfind(')')
                if idx != -1:
                    content = content[:idx] + content[idx + 1:]
            logger.info(f"Rimosse {close_count - open_count} parentesi in eccesso")

        return content

    # =========================================================================
    # FIX 2: DOMAIN NAME MISMATCH
    # =========================================================================

    def fix_domain_names(self):
        """Sincronizza i nomi del domain"""
        domain_match = re.search(r'\(domain\s+([\w-]+)\)', self.domain_content)
        problem_match = re.search(r'\(:domain\s+([\w-]+)\)', self.problem_content)

        if domain_match and problem_match:
            domain_name = domain_match.group(1)
            problem_domain = problem_match.group(1)

            if domain_name != problem_domain:
                self.problem_content = self.problem_content.replace(
                    f'(:domain {problem_domain})',
                    f'(:domain {domain_name})'
                )
                logger.info(f"Domain name corretto: {problem_domain} → {domain_name}")

    # =========================================================================
    # FIX 3: PREDICATI MANCANTI
    # =========================================================================

    def extract_predicates(self) -> Set[str]:
        """Estrae predicati definiti nel domain"""
        pred_match = re.search(
            r'\(:predicates\s+(.*?)\n\s*\)\s*\n',
            self.domain_content,
            re.DOTALL
        )
        if not pred_match:
            return set()

        predicates = set()
        for match in re.finditer(r'\((\w+)(?:\s+\?[\w-]+(?:\s+-\s+\w+)?)*\)', pred_match.group(1)):
            predicates.add(match.group(1))

        return predicates

    def find_used_predicates(self) -> Set[str]:
        """Trova tutti i predicati usati in init, goal e actions"""
        used = set()

        # Da :init
        init_match = re.search(r'\(:init\s+(.*?)\n\s*\)', self.problem_content, re.DOTALL)
        if init_match:
            for match in re.finditer(r'\((\w+)', init_match.group(1)):
                pred = match.group(1)
                if pred not in {'and', 'or', 'not'}:
                    used.add(pred)

        # Da :goal
        goal_match = re.search(r'\(:goal\s+(.*?)\n\s*\)', self.problem_content, re.DOTALL)
        if goal_match:
            for match in re.finditer(r'\((\w+)', goal_match.group(1)):
                pred = match.group(1)
                if pred not in {'and', 'or', 'not'}:
                    used.add(pred)

        # Da actions (preconditions + effects)
        for action_match in re.finditer(
                r'\(:action\s+\w+.*?:effect\s+(.*?)\n\s*\)',
                self.domain_content,
                re.DOTALL
        ):
            for match in re.finditer(r'\((\w+)', action_match.group(1)):
                pred = match.group(1)
                if pred not in {'and', 'or', 'not'}:
                    used.add(pred)

        return used

    def add_missing_predicates(self):
        """Aggiunge predicati mancanti nella sezione :predicates"""
        defined = self.extract_predicates()
        used = self.find_used_predicates()
        missing = used - defined

        if not missing:
            return

        # Trova la sezione predicates
        pred_match = re.search(
            r'(\(:predicates\s+)(.*?)(\n\s*\)\s*\n)',
            self.domain_content,
            re.DOTALL
        )

        if not pred_match:
            logger.error("Sezione :predicates non trovata")
            return

        # Aggiungi predicati mancanti
        new_preds = '\n    '.join(f'({pred})' for pred in sorted(missing))

        self.domain_content = (
                self.domain_content[:pred_match.end(2)] +
                f'\n    {new_preds}' +
                self.domain_content[pred_match.end(2):]
        )

        logger.info(f"Aggiunti {len(missing)} predicati: {missing}")

    # =========================================================================
    # FIX 4: TYPES MANCANTI
    # =========================================================================

    def ensure_types_section(self):
        """Assicura che ci sia una sezione :types"""
        if ':types' not in self.domain_content:
            # Inserisci dopo :requirements
            req_match = re.search(r'(\(:requirements[^\)]*\)\s*\n)', self.domain_content)
            if req_match:
                self.domain_content = (
                        self.domain_content[:req_match.end()] +
                        '  (:types object)\n' +
                        self.domain_content[req_match.end():]
                )
                logger.info("Aggiunta sezione :types")

    # =========================================================================
    # FIX 5: OGGETTI NON TIPIZZATI
    # =========================================================================

    def fix_untyped_objects(self):
        """Aggiunge typing agli oggetti se mancante"""
        obj_match = re.search(r'\(:objects\s+(.*?)\)', self.problem_content, re.DOTALL)
        if not obj_match:
            return

        obj_content = obj_match.group(1)

        # Se non ci sono "- type", aggiungi "- object"
        if ' - ' not in obj_content:
            objects = re.findall(r'(\w+)', obj_content)
            if objects:
                typed_objects = ' '.join(objects) + ' - object'
                self.problem_content = self.problem_content.replace(
                    f'(:objects {obj_content})',
                    f'(:objects {typed_objects})'
                )
                logger.info("Aggiunto typing agli oggetti")

    # =========================================================================
    # VALIDAZIONE COMPLETA
    # =========================================================================

    def validate_and_fix(self) -> Tuple[bool, List[str]]:
        """Esegue tutti i fix automatici"""
        self.load_files()
        self.errors = []

        # Fix 1: Parentesi
        self.domain_content = self.fix_parentheses(self.domain_content)
        self.problem_content = self.fix_parentheses(self.problem_content)

        # Fix 2: Domain names
        self.fix_domain_names()

        # Fix 3: Types
        self.ensure_types_section()

        # Fix 4: Predicati mancanti
        self.add_missing_predicates()

        # Fix 5: Oggetti non tipizzati
        self.fix_untyped_objects()

        # Salva modifiche
        self.save_files()

        # Validazione strutturale
        if not self._validate_structure():
            return False, self.errors

        return True, []

    def _validate_structure(self) -> bool:
        """Valida la struttura base dei file PDDL"""
        valid = True

        # Controlla domain
        if not re.search(r'\(define\s+\(domain\s+[\w-]+\)', self.domain_content):
            self.errors.append("Domain: Definizione mancante")
            valid = False

        if not re.search(r'\(:requirements', self.domain_content):
            self.errors.append("Domain: Sezione :requirements mancante")
            valid = False

        if not re.search(r'\(:predicates', self.domain_content):
            self.errors.append("Domain: Sezione :predicates mancante")
            valid = False

        if not re.search(r'\(:action', self.domain_content):
            self.errors.append("Domain: Nessuna action definita")
            valid = False

        # Controlla problem
        if not re.search(r'\(define\s+\(problem\s+[\w-]+\)', self.problem_content):
            self.errors.append("Problem: Definizione mancante")
            valid = False

        if not re.search(r'\(:domain', self.problem_content):
            self.errors.append("Problem: Riferimento :domain mancante")
            valid = False

        if not re.search(r'\(:init', self.problem_content):
            self.errors.append("Problem: Sezione :init mancante")
            valid = False

        if not re.search(r'\(:goal', self.problem_content):
            self.errors.append("Problem: Sezione :goal mancante")
            valid = False

        return valid


# =============================================================================
# 2. GENERATORE PDDL
# =============================================================================

def call_ollama(prompt: str, system_prompt: str) -> str:
    """Chiama Ollama con gestione errori"""
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Più deterministico
                "top_p": 0.9,
                "num_predict": 4000
            }
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=600)
        response.raise_for_status()
        return response.json().get('response', '').strip()
    except requests.exceptions.ConnectionError:
        logger.error("❌ OLLAMA NON È IN ESECUZIONE!")
        logger.error("   Avvia Ollama con: ollama serve")
        logger.error(f"   Verifica che sia raggiungibile su {OLLAMA_URL}")
        return ""
    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout - Ollama impiega troppo tempo")
        return ""
    except Exception as e:
        logger.error(f"Errore Ollama: {e}")
        return ""


def check_ollama_available() -> bool:
    """Verifica che Ollama sia disponibile"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


class PDDLGenerator:
    """Generatore PDDL con validazione integrata"""

    def __init__(self, guide_path: Path, lore_path: Path, output_dir: Path):
        self.guide_path = guide_path
        self.lore_path = lore_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.domain_path = output_dir / "domain.pddl"
        self.problem_path = output_dir / "problem.pddl"

        # Carica contenuti
        with open(guide_path, 'r', encoding='utf-8') as f:
            self.guide = f.read()
        with open(lore_path, 'r', encoding='utf-8') as f:
            self.lore = f.read()

    def generate_initial_pddl(self) -> bool:
        """Genera PDDL iniziale dall'LLM"""
        system_prompt = f"""You are an expert PDDL planner. Generate VALID PDDL files.

CRITICAL RULES:
1. PERFECT parentheses balance
2. ALL predicates MUST be in :predicates section
3. Use :types and type all objects
4. Create 3-5 meaningful actions
5. Make goal reachable in 5-12 steps
6. NO explanations, ONLY code

PDDL GUIDE:
{self.guide}"""

        prompt = f"""Generate TWO complete PDDL files:

1. domain.pddl - Complete domain definition
2. problem.pddl - Problem instance

LORE:
{self.lore}

OUTPUT FORMAT (no markdown, just PDDL):
(define (domain ...)
  ...
)

(define (problem ...)
  ...
)"""

        logger.info("Generazione PDDL con LLM...")
        response = call_ollama(prompt, system_prompt)

        if not response:
            logger.error("LLM non ha risposto")
            return False

        return self._parse_and_save(response)

    def regenerate_with_feedback(self, fd_errors: str) -> bool:
        """Rigenera PDDL con feedback da Fast Downward"""
        system_prompt = f"""You are an expert PDDL planner. FIX the errors.

PDDL GUIDE:
{self.guide}"""

        # Leggi versioni correnti
        with open(self.domain_path, 'r', encoding='utf-8') as f:
            current_domain = f.read()
        with open(self.problem_path, 'r', encoding='utf-8') as f:
            current_problem = f.read()

        prompt = f"""The following PDDL files have ERRORS from Fast Downward validator:

ERRORS:
{fd_errors}

CURRENT DOMAIN:
{current_domain}

CURRENT PROBLEM:
{current_problem}

Generate CORRECTED versions addressing ALL errors.
Output format (no markdown):
(define (domain ...)
  ...
)

(define (problem ...)
  ...
)"""

        logger.info("Rigenerazione con feedback Fast Downward...")
        response = call_ollama(prompt, system_prompt)

        if not response:
            return False

        return self._parse_and_save(response)

    def _parse_and_save(self, response: str) -> bool:
        """Estrae e salva domain e problem dalla risposta LLM"""
        try:
            # Rimuovi markdown se presente
            response = re.sub(r'```(?:pddl)?\n?', '', response)

            # Trova domain
            domain_start = response.find('(define (domain')
            if domain_start == -1:
                logger.error("Domain non trovato nella risposta")
                return False

            domain_end = self._find_matching_paren(response, domain_start)
            domain_content = response[domain_start:domain_end + 1]

            # Trova problem
            problem_start = response.find('(define (problem', domain_end)
            if problem_start == -1:
                logger.error("Problem non trovato nella risposta")
                return False

            problem_end = self._find_matching_paren(response, problem_start)
            problem_content = response[problem_start:problem_end + 1]

            # Salva file
            with open(self.domain_path, 'w', encoding='utf-8') as f:
                f.write(domain_content.strip() + '\n')
            with open(self.problem_path, 'w', encoding='utf-8') as f:
                f.write(problem_content.strip() + '\n')

            logger.info("File PDDL salvati")
            return True

        except Exception as e:
            logger.error(f"Errore parsing: {e}")
            return False

    def _find_matching_paren(self, text: str, start: int) -> int:
        """Trova parentesi chiusa corrispondente"""
        count = 1
        i = start + 1
        while i < len(text) and count > 0:
            if text[i] == '(':
                count += 1
            elif text[i] == ')':
                count -= 1
            i += 1
        return i - 1


# =============================================================================
# 3. VALIDATORE FAST DOWNWARD
# =============================================================================

class FastDownwardValidator:
    """Wrapper per Fast Downward"""

    def __init__(self, fd_path: str):
        self.fd_path = Path(fd_path)
        if not self.fd_path.exists():
            raise FileNotFoundError(f"Fast Downward non trovato: {fd_path}")

    def validate(self, domain_path: Path, problem_path: Path) -> Tuple[bool, str, str]:
        """
        Valida con Fast Downward
        Returns: (success, message, output)
        """
        cmd = [
            "python",
            str(self.fd_path),
            str(domain_path.resolve()),
            str(problem_path.resolve()),
            "--search", "astar(lmcut())"
        ]

        try:
            logger.info("Esecuzione Fast Downward...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                shell=True
            )

            output = result.stdout + "\n" + result.stderr

            # Controlla se ha trovato un piano
            if result.returncode == 0:
                plan_path = domain_path.parent / "sas_plan"
                if plan_path.exists():
                    with open(plan_path, 'r', encoding='utf-8') as f:
                        plan = f.read()
                    return True, "Piano trovato!", plan

            # Estrai errori significativi
            errors = self._extract_errors(output)
            return False, errors, output

        except subprocess.TimeoutExpired:
            return False, "Timeout (300s)", ""
        except Exception as e:
            return False, f"Errore esecuzione: {e}", ""

    def _extract_errors(self, output: str) -> str:
        """Estrae messaggi di errore rilevanti"""
        error_lines = []

        for line in output.split('\n'):
            line = line.strip()
            if any(keyword in line.lower() for keyword in [
                'error', 'warning', 'undefined', 'parsing', 'syntax',
                'not defined', 'unknown', 'invalid'
            ]):
                error_lines.append(line)

        return '\n'.join(error_lines[:20])  # Primi 20 errori


# =============================================================================
# 4. ORCHESTRATORE PRINCIPALE
# =============================================================================

def generate_valid_pddl(
        guide_path: Path,
        lore_path: Path,
        output_dir: Path,
        fd_path: str,
        max_attempts: int = 5
) -> Tuple[bool, str]:
    """
    Pipeline completa di generazione PDDL

    Returns: (success, message)
    """

    logger.info("=" * 70)
    logger.info("INIZIO GENERAZIONE PDDL VALIDATO")
    logger.info("=" * 70)

    # Inizializza componenti
    generator = PDDLGenerator(guide_path, lore_path, output_dir)
    validator = PDDLValidator(generator.domain_path, generator.problem_path)
    fd_validator = FastDownwardValidator(fd_path)

    fd_errors = ""  # Inizializza per evitare UnboundLocalError

    for attempt in range(1, max_attempts + 1):
        logger.info(f"\n{'=' * 70}")
        logger.info(f"TENTATIVO {attempt}/{max_attempts}")
        logger.info(f"{'=' * 70}\n")

        # STEP 1: Generazione LLM
        if attempt == 1:
            success = generator.generate_initial_pddl()
        else:
            # Usa feedback da Fast Downward
            success = generator.regenerate_with_feedback(fd_errors)

        if not success:
            logger.error("Generazione LLM fallita")
            continue

        # STEP 2: Auto-fix deterministico
        logger.info("\n🔧 Auto-fix deterministico...")
        valid, errors = validator.validate_and_fix()

        if not valid:
            logger.error(f"Errori strutturali non risolvibili:\n" + "\n".join(errors))
            continue

        logger.info("✓ Auto-fix completato")

        # STEP 3: Validazione Fast Downward
        logger.info("\n⚡ Validazione Fast Downward...")
        success, message, output = fd_validator.validate(
            generator.domain_path,
            generator.problem_path
        )

        if success:
            logger.info("\n" + "=" * 70)
            logger.info("✅ SUCCESS! PDDL VALIDO E RISOLVIBILE!")
            logger.info("=" * 70)
            logger.info(f"\n📋 PIANO:\n{output}")
            logger.info(f"\n📂 File salvati in: {output_dir}")
            return True, "PDDL valido generato con successo"

        # Salva errori per prossima iterazione
        fd_errors = message
        logger.warning(f"❌ Fast Downward ha rilevato errori:\n{fd_errors}\n")
        logger.info("🔄 Rigenerazione con feedback...")

    logger.error("\n" + "=" * 70)
    logger.error(f"❌ FALLIMENTO dopo {max_attempts} tentativi")
    logger.error("=" * 70)
    return False, f"Impossibile generare PDDL valido dopo {max_attempts} tentativi"


# =============================================================================
# 5. MAIN
# =============================================================================

if __name__ == '__main__':
    SCRIPT_DIR = Path(__file__).resolve().parent

    # Percorsi
    GUIDE_FILE = SCRIPT_DIR.parent / "static" / "file" / "Guide_pddl.txt"
    LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"
    OUTPUT_FOLDER = SCRIPT_DIR / "pddl_generation_output"
    FAST_DOWNWARD = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"

    # Verifica Ollama
    print("🔍 Verifica prerequisiti...")
    if not check_ollama_available():
        print("\n❌ ERRORE: Ollama non è in esecuzione!")
        print("\n📝 Come risolvere:")
        print("   1. Apri un terminale")
        print("   2. Esegui: ollama serve")
        print("   3. Verifica con: curl http://localhost:11434/api/tags")
        print(f"   4. Assicurati che il modello '{MODEL}' sia installato: ollama pull {MODEL}")
        exit(1)
    print(f"✓ Ollama disponibile (modello: {MODEL})")

    # Verifica file esistenti
    if not GUIDE_FILE.exists():
        print(f"❌ File guida non trovato: {GUIDE_FILE}")
        exit(1)
    print(f"✓ Guida PDDL: {GUIDE_FILE}")

    if not LORE_FILE.exists():
        print(f"❌ File lore non trovato: {LORE_FILE}")
        exit(1)
    print(f"✓ Lore: {LORE_FILE}")

    if not Path(FAST_DOWNWARD).exists():
        print(f"❌ Fast Downward non trovato: {FAST_DOWNWARD}")
        exit(1)
    print(f"✓ Fast Downward: {FAST_DOWNWARD}")

    print("\n" + "=" * 70)
    print("🚀 Avvio generazione PDDL...")
    print("=" * 70 + "\n")

    # Esegui generazione
    try:
        success, message = generate_valid_pddl(
            guide_path=GUIDE_FILE,
            lore_path=LORE_FILE,
            output_dir=OUTPUT_FOLDER,
            fd_path=FAST_DOWNWARD,
            max_attempts=5
        )

        if success:
            print(f"\n🎉 {message}")
            print(f"📂 File PDDL: {OUTPUT_FOLDER}")
        else:
            print(f"\n😞 {message}")
            print("\n💡 Suggerimenti:")
            print("  - Verifica che la lore sia chiara e ben strutturata")
            print("  - Controlla che la guida PDDL contenga esempi validi")
            print("  - Aumenta max_attempts se necessario")
            print("  - Prova a semplificare la lore")

    except Exception as e:
        print(f"\n❌ Errore critico: {e}")
        import traceback

        traceback.print_exc()