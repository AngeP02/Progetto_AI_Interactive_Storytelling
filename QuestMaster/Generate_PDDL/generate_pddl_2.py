# File: PDDL_Generation_Script.py
import os
import requests
import json
import logging
import subprocess
from pathlib import Path
import re  # Aggiungo re per l'analisi dell'errore

# Configurazione del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurazione standard Ollama
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


# --- 1. LLM Helper ---

def call_ollama(prompt, system_prompt):
    """
    Funzione riutilizzabile per chiamare l'API di generazione di Ollama.
    """
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.5,
                "top_p": 0.9,
                "num_predict": 2048
            }
        }

        logger.info("Chiamata ad Ollama per la generazione PDDL...")
        response = requests.post(OLLAMA_URL, json=payload, timeout=500)
        response.raise_for_status()

        result = response.json()
        return result.get('response', '').strip()

    except requests.exceptions.RequestException as e:
        logger.error(f"Errore chiamata Ollama: {e}")
        return None
    except Exception as e:
        logger.error(f"Errore generico: {e}")
        return None


# --- 2. Classe Principale Modificata ---

class PDDLGeneratorValidator:
    def __init__(self, pddl_guide_path, lore_file_path, output_dir_path):
        self.pddl_guide_path = Path(pddl_guide_path)
        self.lore_file_path = Path(lore_file_path)
        self.output_dir = Path(output_dir_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.domain_path = self.output_dir / "domain.pddl"
        self.problem_path = self.output_dir / "problem.pddl"

        if not self.pddl_guide_path.exists() or not self.lore_file_path.exists():
            raise FileNotFoundError("Assicurati che i file della guida PDDL e della Lore esistano.")

    def _read_files(self):
        """Legge il contenuto dei file di guida e lore."""
        with open(self.pddl_guide_path, 'r', encoding='utf-8') as f:
            pddl_guide = f.read()
        with open(self.lore_file_path, 'r', encoding='utf-8') as f:
            lore_content = f.read()
        return pddl_guide, lore_content

    # Aggiungo il parametro reflection_feedback
    def generate_pddl_from_llm(self, reflection_feedback=""):
        """
        Chiama l'LLM per generare i file domain.pddl e problem.pddl.
        Aggiunge un feedback per la correzione.
        """
        pddl_guide, lore_content = self._read_files()

        system_prompt = (
            "You are an expert in AI Action Planning and are tasked with creating syntactically and semantically correct PDDL files"
            "for an interactive story. "
            "Meticulously follow the rules provided in the 'Advanced PDDL Guide' below. "
            "The generated PDDL must reflect the logic and goals described in the 'Lore Document' file. "
            "Focus on creating a 'domain.pddl' with up to 5 actions and a 'problem.pddl' "
            "that defines a plausible and solvable initial challenge."
            "\n\n--- Advanced PDDL Guide ---\n"
            f"{pddl_guide}"
        )

        prompt = (
            "Using the provided guide, generate the two valid PDDL files for the following scenario."
            "Your output must begin *EXACTLY* with a code block for domain.pddl"
            "and *immediately* followed by a code block for problem.pddl."
            "Do not add ANY descriptive text or introductions outside the code blocks."
            "Make sure the domain name in the problem matches the domain name."

            # --- ADD FEEDBACK ---
            f"\n\n--- Corrective Feedback ---\n{reflection_feedback}\n"
            "CRITICAL: Carefully correct PDDL syntax errors such as unbalanced parentheses."
            "Your output must be flawless and solvable by Fast Downward."
            # ---------------------------

            "\n\n--- Lore Document ---\n"
            f"{lore_content}"
        )

        response = call_ollama(prompt, system_prompt)

        if response is None:
            return False, "Errore nella chiamata Ollama."

        # Estrazione dei blocchi di codice
        try:
            domain_start = response.find('(define (domain')
            problem_start = response.find('(define (problem')

            if domain_start == -1 or problem_start == -1:
                return False, "Impossibile trovare le definizioni PDDL nell'output dell'LLM."

            # Estraggo il dominio
            domain_end_index = self._find_matching_paren(response, domain_start)
            domain_pddl = response[domain_start: domain_end_index + 1]

            # Estraggo il problema
            problem_end_index = self._find_matching_paren(response, problem_start)
            problem_pddl = response[problem_start: problem_end_index + 1]

            # Salva i file
            with open(self.domain_path, 'w', encoding='utf-8') as f:
                f.write(domain_pddl.strip())
            with open(self.problem_path, 'w', encoding='utf-8') as f:
                f.write(problem_pddl.strip())

            logger.info(f"File PDDL salvati in: {self.output_dir}")
            return True, "Generazione PDDL riuscita."

        except Exception as e:
            logger.error(f"Errore nell'analisi o nel salvataggio dell'output dell'LLM: {e}")
            return False, f"Errore di parsing/salvataggio: {e}"

    def _find_matching_paren(self, text, start_index):
        """Trova l'indice della parentesi chiusa corrispondente."""
        count = 1
        i = start_index + 1
        while i < len(text):
            if text[i] == '(':
                count += 1
            elif text[i] == ')':
                count -= 1
                if count == 0:
                    return i
            i += 1
        return len(text) - 1  # Fallback: se non bilanciata, prendo fino alla fine

    def validate_and_solve(self):
        """
        Valida e risolve con Fast Downward.
        Ritorna (risolto, messaggio, output_completo)
        """
        logger.info(f"Avvio la validazione e la risoluzione con Fast Downward...")
        domain_path = self.domain_path.resolve()
        problem_path = self.problem_path.resolve()

        # DEVI CONFIGURARE QUESTO PERCORSO CORRETTAMENTE
        fast_downward_path = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"
        if not os.path.exists(fast_downward_path):
            print("⚠️ Fast Downward non trovato al percorso specificato.")
            return False, "Fast Downward non trovato.", ""

        cmd = ["python", fast_downward_path, str(domain_path), str(problem_path),
               "--search", "astar(lmcut())"]

        try:
            print("▶️ Running Fast Downward...")
            # Uso la shell per evitare problemi di path su Windows
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, shell=True)
            full_output = result.stdout + "\n" + result.stderr

            if result.returncode == 0:
                plan_path = self.output_dir / "sas_plan"  # Fast Downward salva come sas_plan di default
                if plan_path.exists():
                    with open(plan_path, 'r', encoding='utf-8') as f:
                        plan = f.read()
                    # Ritorna TRUE solo se un piano è stato trovato e salvato
                    return True, "Successo: PDDL valido e piano trovato.", plan
                else:
                    return False, "Errore: PDDL valido, ma Fast Downward non ha prodotto il file sas_plan.", full_output

            elif "Search stopped without finding a solution" in full_output or "Search stopped" in full_output:
                return False, "PDDL Sintatticamente Corretto, ma non è stata trovata una soluzione (Problema Insolvibile o troppo complesso).", full_output

            # Cerca errori di parsing
            elif "parser error" in full_output.lower() or "error" in full_output.lower() or result.returncode != 0:
                return False, f"Errore di Validazione PDDL: I file contengono errori sintattici o semantici. Dettagli nel log completo.", full_output

            else:
                return False, f"Fallimento del Planner. Codice di uscita: {result.returncode}.", full_output

        except FileNotFoundError:
            return False, "Errore: 'fast-downward.py' non trovato. Assicurati che sia installato e nel tuo PATH.", ""
        except subprocess.TimeoutExpired:
            return False, "Errore: Fast Downward ha superato il timeout. Il problema è troppo complesso.", ""
        except Exception as e:
            return False, f"Errore imprevisto durante l'esecuzione di Fast Downward: {e}", ""


# --- 3. Reflection Agent ---

def reflection_generate_pddl(generator: PDDLGeneratorValidator, max_attempts=3):
    """
    Mini reflection agent: tenta più volte di generare un PDDL risolvibile.
    Se FastDownward fallisce, rigenera aggiungendo feedback al prompt.
    """
    for attempt in range(1, max_attempts + 1):
        print(f"\n🧠 Agente di Riflessione: Tentativo {attempt}/{max_attempts}")

        # Genera un feedback iniziale vuoto o basato sull'errore precedente
        feedback = ""
        if attempt > 1:
            # Qui si potrebbe analizzare l'output per un feedback più mirato
            feedback = (
                f"Il tentativo {attempt - 1} ha fallito la validazione. L'errore principale "
                f"riscontrato è stato: {generator.last_error_detail}. "
                "Correggi in particolare le parentesi non bilanciate e le firme dei predicati."
            )

        # 1. Generazione
        success, message = generator.generate_pddl_from_llm(reflection_feedback=feedback)
        print(f"\n--- Risultato Generazione LLM (Tentativo {attempt}) ---")
        print(message)

        if not success:
            print("⚠️ Generazione fallita. Non posso continuare il tentativo.")
            continue

        # 2. Validazione e Soluzione
        solved, status_msg, full_output = generator.validate_and_solve()
        print(f"\n--- Risultato Validazione Fast Downward (Tentativo {attempt}) ---")
        print(status_msg)

        if solved:
            print("\n✅ PIANO RISOLUTIVO TROVATO:")
            print(full_output)
            return True, status_msg, full_output

        # Estrai dettagli per il prossimo feedback
        # Assumiamo di memorizzare l'errore per il prossimo ciclo
        match_missing_paren = re.search(r"Reason:\s*(Missing '[()]')", full_output)
        if match_missing_paren:
            generator.last_error_detail = match_missing_paren.group(1)
        else:
            # Default per altri errori come predicati sconosciuti o stato irraggiungibile
            generator.last_error_detail = "Errore generico di sintassi PDDL o problema irrisolvibile"

        print(f"❌ Errore riscontrato: {generator.last_error_detail}. Rigenero con feedback.")

    print("\n❌ Agente di Riflessione: Fallimento dopo tutti i tentativi.")
    return False, "Fallimento finale del Reflection Agent.", ""


# --- Esecuzione Principale Modificata ---

if __name__ == '__main__':

    # 1. Definizione della base: Trova la directory dello script in esecuzione
    SCRIPT_DIR = Path(__file__).resolve().parent

    # ⚠️ PARAMETRI DA MODIFICARE CON I NOMI ESATTI DEI FILE ⚠️
    GUIDE_FILE = SCRIPT_DIR.parent / "static" / "file" / "Guide_pddl.txt"
    LORE_FILENAME = "Lore.md"  # ⬅️ INSERISCI QUI IL NOME COMPLETO!
    LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / LORE_FILENAME
    OUTPUT_FOLDER = SCRIPT_DIR / "pddl_generation_output"
    MAX_ATTEMPTS = 4  # Numero massimo di tentativi di riflessione

    # Converto i percorsi in stringhe assolute
    GUIDE_FILE_STR = str(GUIDE_FILE)
    LORE_FILE_STR = str(LORE_FILE)
    OUTPUT_FOLDER_STR = str(OUTPUT_FOLDER)

    print(f"DEBUG: Tenterò di caricare la Guida da: {GUIDE_FILE_STR}")
    print(f"DEBUG: Tenterò di caricare la Lore da: {LORE_FILE_STR}")

    # Inizializzazione e Processo
    try:
        generator = PDDLGeneratorValidator(GUIDE_FILE_STR, LORE_FILE_STR, OUTPUT_FOLDER_STR)
        # Inizializza un campo per memorizzare l'ultimo errore per il feedback
        generator.last_error_detail = "Nessun errore precedente."

        # Avvia il processo con l'Agente di Riflessione
        solved, status_msg, full_output = reflection_generate_pddl(generator, MAX_ATTEMPTS)

    except FileNotFoundError as e:
        print(f"\nFATAL ERROR: Assicurati che i file della guida PDDL e della Lore esistano. Dettaglio: {e}")
    except Exception as e:
        print(f"\nERRORE CRITICO: {e}")