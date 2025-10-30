# File: PDDL_Generation_Script.py
import os

import requests
import json
import logging
import subprocess
from pathlib import Path

# Configurazione del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurazione standard Ollama (assumendo sia lo stesso setup del tuo codice Flask)
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
                "temperature": 0.5,  # Temperatura più bassa per codice stabile
                "top_p": 0.9,
                "num_predict": 2048  # Aumento della predizione per file lunghi
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


# --- 2. Classe Principale ---

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

    def generate_pddl_from_llm(self):
        """
        Chiama l'LLM per generare i file domain.pddl e problem.pddl.
        """
        pddl_guide, lore_content = self._read_files()

        system_prompt = (
            "Sei un esperto nell'Action Planning AI e hai il compito di creare file PDDL "
            "sintatticamente e semanticamente corretti per una storia interattiva. "
            "Segui meticolosamente le regole fornite nella 'Guida Avanzata al PDDL' qui sotto. "
            "Il PDDL generato deve riflettere la logica e gli obiettivi descritti nel file 'Lore Document'. "
            "Concentrati sulla creazione di un 'domain.pddl' con un massimo di 5 azioni e un 'problem.pddl' "
            "che definisce una sfida iniziale plausibile e risolvibile."
            "\n\n--- Guida Avanzata al PDDL ---\n"
            f"{pddl_guide}"
        )

        prompt = (
            "Utilizzando la guida fornita, genera i due file PDDL validi per il seguente scenario. "
            "Il tuo output deve iniziare *ESATTAMENTE* con un blocco di codice per domain.pddl "
            "e *immediatamente* seguito da un blocco di codice per problem.pddl. "
            "Non aggiungere NESSUN testo descrittivo o introduzione all'esterno dei blocchi di codice. "
            "Assicurati che il nome del dominio nel problema corrisponda a quello nel dominio."
            "\n\n--- Lore Document ---\n"
            f"{lore_content}"
        )

        response = call_ollama(prompt, system_prompt)

        if response is None:
            return False, "Errore nella chiamata Ollama."

        # Estrazione dei blocchi di codice (ricerca dei blocchi LISP)
        try:
            domain_start = response.find('(define (domain')
            problem_start = response.find('(define (problem')

            if domain_start == -1 or problem_start == -1:
                return False, "Impossibile trovare le definizioni PDDL nell'output dell'LLM."

            # Assumendo che il dominio sia il primo e il problema il secondo,
            # cerco la chiusura bilanciata per ciascuno. Questa è una semplificazione.

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
        return len(text) - 1  # Fallback, non bilanciata

    def validate_and_solve(self):
        """
        Valida i file PDDL generati e tenta di risolverli con Fast Downward.
        """
        logger.info(f"Avvio la validazione e la risoluzione con Fast Downward...")
        domain_path = self.domain_path.resolve()
        problem_path = self.problem_path.resolve()

        fast_downward_path = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"
        if not os.path.exists(fast_downward_path):
            print("⚠️ Fast Downward not found")
            return False

        cmd = ["python", fast_downward_path, str(domain_path), str(problem_path),
               "--search", "astar(lmcut())"]

        try:
            print("▶️ Running Fast Downward...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            # Analisi dell'output
            if result.returncode == 0:
                plan_path = self.output_dir / "plan.out"
                if plan_path.exists():
                    with open(plan_path, 'r', encoding='utf-8') as f:
                        plan = f.read()
                    return True, "Successo: PDDL valido e piano trovato.", plan
                else:
                    return False, "Errore: PDDL valido, ma Fast Downward non ha prodotto il file plan.out."

            elif "Search stopped without finding a solution" in result.stdout or "Search stopped" in result.stdout:
                return False, "PDDL Sintatticamente Corretto, ma non è stata trovata una soluzione (Problema Insolvibile o troppo complesso).", result.stdout

            elif "parser error" in result.stdout.lower() or "error" in result.stdout.lower():
                return False, f"Errore di Validazione PDDL: I file contengono errori sintattici o semantici. Dettagli: {result.stdout}", result.stdout

            else:
                return False, f"Fallimento del Planner. Codice di uscita: {result.returncode}. Output: {result.stdout}", result.stdout

        except FileNotFoundError:
            return False, "Errore: 'fast-downward.py' non trovato. Assicurati che sia installato e nel tuo PATH.", ""
        except subprocess.TimeoutExpired:
            return False, "Errore: Fast Downward ha superato il timeout. Il problema è troppo complesso.", ""
        except Exception as e:
            return False, f"Errore imprevisto durante l'esecuzione di Fast Downward: {e}", ""


# --- Esecuzione Principale ---

if __name__ == '__main__':

    # 1. Definizione della base: Trova la directory dello script in esecuzione
    # SCRIPT_DIR sarà: '.../QuestMaster/Generate_PDDL'
    SCRIPT_DIR = Path(__file__).resolve().parent

    # ⚠️ PARAMETRI DA MODIFICARE CON I NOMI ESATTI DEI FILE ⚠️

    # 2. Percorso della Guida PDDL: Risali a QuestMaster (SCRIPT_DIR.parent) e scendi in static/file
    # DEVI INCLUDERE L'ESTENSIONE CORRETTA (es. .txt, .md o nulla se non ha estensione)
    GUIDE_FILE = SCRIPT_DIR.parent / "static" / "file" / "Guida_pddl.txt"  # Modifica qui se hai un'estensione!

    # 3. Percorso del File Lore: Risali a QuestMaster (SCRIPT_DIR.parent) e scendi in Lore/Generated_Lore
    # SOSTITUISCI IL NOME DEL FILE COMPLETO QUI SOTTO!
    LORE_FILENAME = "Lore.md"  # ⬅️ INSERISCI QUI IL NOME COMPLETO!
    LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / LORE_FILENAME

    # 4. Directory dove salvare i file PDDL e il piano. Verrà creata dentro Generate_PDDL.
    OUTPUT_FOLDER = SCRIPT_DIR / "pddl_generation_output"

    # --- Esecuzione Principalle ---

    # Converto i percorsi in stringhe assolute
    GUIDE_FILE_STR = str(GUIDE_FILE)
    LORE_FILE_STR = str(LORE_FILE)
    OUTPUT_FOLDER_STR = str(OUTPUT_FOLDER)

    print(f"DEBUG: Tenterò di caricare la Guida da: {GUIDE_FILE_STR}")
    print(f"DEBUG: Tenterò di caricare la Lore da: {LORE_FILE_STR}")

    # Inizializzazione e Processo
    try:
        # Passiamo i percorsi in formato stringa
        generator = PDDLGeneratorValidator(GUIDE_FILE_STR, LORE_FILE_STR, OUTPUT_FOLDER_STR)

        # 1. Generazione
        success, message = generator.generate_pddl_from_llm()
        print("\n--- Risultato Generazione LLM ---")
        print(message)

        if success:
            # 2. Validazione e Soluzione
            solved, status_msg, full_output = generator.validate_and_solve()
            print("\n--- Risultato Validazione Fast Downward ---")
            print(status_msg)

            if solved:
                print("\n✅ PIANO RISOLUTIVO TROVATO:")
                print(full_output)
            elif "Errore di Validazione PDDL" in status_msg:
                print("\n❌ ERRORE NEL CODICE PDDL. Output completo di FD:")
                print(full_output)

    except FileNotFoundError as e:
        print(f"\nFATAL ERROR: Assicurati che i file della guida PDDL e della Lore esistano. Dettaglio: {e}")
    except Exception as e:
        print(f"\nERRORE CRITICO: {e}")