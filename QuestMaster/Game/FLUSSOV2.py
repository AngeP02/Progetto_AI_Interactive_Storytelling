from dotenv import load_dotenv
from openai import OpenAI
import logging
import os
import re
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

class StoryGraphGenerator:
    def __init__(self, api_key=None, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        logger.info(f"StoryGraphGenerator inizializzato con modello OpenAI: {self.model_name}")

    def call_openai(self, prompt, system_prompt=""):
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                top_p=0.9,
                max_tokens=1024
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Errore OpenAI API: {e}")
            return None

    def _read_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Errore lettura {file_path}: {e}")
            return ""

    def _parse_sas_plan(self, plan_content):
        actions = []
        for line in plan_content.split('\n'):
            line = line.strip()
            if line.startswith('(') and not line.startswith(';'):
                actions.append(line)
        return actions

    def _extract_parameters(self, lore_content):
        depth_min, depth_max = 3, 5
        branching_min, branching_max = 2, 3

        depth_match = re.search(r'depth[:\s]+(\d+)\s*[-–]\s*(\d+)', lore_content, re.IGNORECASE)
        branching_match = re.search(r'branching[:\s]+(\d+)\s*[-–]\s*(\d+)', lore_content, re.IGNORECASE)

        if depth_match:
            depth_min, depth_max = int(depth_match.group(1)), int(depth_match.group(2))
        if branching_match:
            branching_min, branching_max = int(branching_match.group(1)), int(branching_match.group(2))

        depth = (depth_min + depth_max) // 2
        branching = (branching_min + branching_max) // 2

        logger.info(f"Parametri estratti - Depth: {depth}, Branching: {branching}")
        return depth, branching

    def _generate_scene_description(self, context, lore_snippet, previous_choices=None):
        system_prompt = """Sei un narratore cyberpunk. Descrivi una scena in 2-3 FRASI.

REGOLE:
1. MAX 3 frasi (20-40 parole totali)
2. Descrivi la situazione attuale
3. Crea atmosfera e tensione
4. Introduce elementi per le prossime scelte
5. USA ITALIANO
6. NO markdown, NO formattazione"""

        user_prompt = f"""CONTESTO: {context}
LORE: {lore_snippet[:400]}

Descrivi la scena attuale in cui si trova il protagonista."""

        response = self.call_openai(user_prompt, system_prompt)
        if not response:
            return "[Scena da definire]"

        cleaned = response.replace('*', '').replace('#', '').replace('"', '').strip()
        sentences = [s.strip() for s in cleaned.split('.') if s.strip()][:3]
        return '. '.join(sentences) + '.' if sentences else "[Scena da definire]"

    def _generate_choice(self, context, lore_snippet, choice_number, previous_choices):
        """Genera una singola scelta d'azione"""
        system_prompt = """Sei un narratore cyberpunk. Genera UNA scelta d'azione in 1 FRASE.

REGOLE:
1. MAX 1 frase (6-12 parole)
2. Deve essere un'AZIONE che il protagonista può compiere
3. Deve essere COMPLETAMENTE DIVERSA dalle altre scelte
4. Deve essere coerente con il contesto
5. USA ITALIANO
6. NO markdown, NO formattazione
7. Inizia con un verbo d'azione"""

        user_prompt = f"""CONTESTO: {context}
LORE: {lore_snippet[:300]}
SCELTA #{choice_number}"""

        if previous_choices:
            user_prompt += f"\n\nSCELTE GIÀ GENERATE (NON RIPETERE CONCETTI SIMILI):\n"
            for i, choice in enumerate(previous_choices, 1):
                user_prompt += f"  {i}. {choice}\n"

        user_prompt += f"\n\nGenera la scelta #{choice_number} COMPLETAMENTE DIVERSA dalle precedenti:"

        response = self.call_openai(user_prompt, system_prompt)
        if not response:
            return f"[Scelta {choice_number} da definire]"

        cleaned = response.replace('*', '').replace('#', '').replace('"', '').strip()
        sentences = [s.strip() for s in cleaned.split('.') if s.strip()][:1]
        return sentences[0] + '.' if sentences else f"[Scelta {choice_number} da definire]"

    def _generate_consequence(self, choice, context, lore_snippet):
        """Genera la conseguenza di una scelta"""
        system_prompt = """Sei un narratore cyberpunk. Descrivi la CONSEGUENZA di un'azione in 2-3 FRASI.

REGOLE:
1. MAX 3 frasi (20-35 parole)
2. Descrivi cosa succede dopo la scelta
3. Può introdurre nuovi personaggi, ostacoli, rivelazioni
4. Crea tensione per le prossime scelte
5. USA ITALIANO
6. NO markdown, NO formattazione"""

        user_prompt = f"""CONTESTO: {context}
LORE: {lore_snippet[:400]}
SCELTA EFFETTUATA: {choice}

Descrivi cosa succede come conseguenza diretta di questa scelta."""

        response = self.call_openai(user_prompt, system_prompt)
        if not response:
            return "[Conseguenza da definire]"

        cleaned = response.replace('*', '').replace('#', '').replace('"', '').strip()
        sentences = [s.strip() for s in cleaned.split('.') if s.strip()][:3]
        return '. '.join(sentences) + '.' if sentences else "[Conseguenza da definire]"

    def _build_node_id(self, parts):
        """Costruisce l'ID del nodo"""
        return ".".join(map(str, parts))

    def _generate_tree_recursive(self, node_path, current_depth, max_depth, branching,
                                 parent_context, lore_snippet, nodes, action_num):

        if current_depth > max_depth:
            return

        node_id = self._build_node_id(node_path)
        indent_level = len(node_path) - 1

        is_choice_level = (current_depth % 2 == 1)

        if is_choice_level:
            previous_choices = []

            for choice_num in range(1, branching + 1):
                new_path = node_path + [choice_num]
                choice_id = self._build_node_id(new_path)
                choice_text = self._generate_choice(
                    parent_context,
                    lore_snippet,
                    choice_num,
                    previous_choices
                )
                previous_choices.append(choice_text)

                nodes.append({
                    "id": choice_id,
                    "type": "choice",
                    "depth": current_depth,
                    "indent": indent_level + 1,
                    "text": choice_text,
                    "parent_context": parent_context
                })

                if current_depth < max_depth:
                    consequence_path = new_path + [1]
                    consequence_id = self._build_node_id(consequence_path)

                    consequence_text = self._generate_consequence(
                        choice_text,
                        f"{parent_context} -> {choice_text}",
                        lore_snippet
                    )

                    nodes.append({
                        "id": consequence_id,
                        "type": "consequence",
                        "depth": current_depth + 1,
                        "indent": indent_level + 2,
                        "text": consequence_text,
                        "parent_context": f"{parent_context} -> {choice_text}"
                    })

                    self._generate_tree_recursive(
                        consequence_path,
                        current_depth + 2,  # Salta direttamente al prossimo livello di scelta
                        max_depth,
                        branching,
                        f"{parent_context} -> {choice_text} -> {consequence_text}",
                        lore_snippet,
                        nodes,
                        action_num
                    )

    def generate_story_graph(self, lore_path, plan_path, output_file):
        lore = self._read_file(lore_path)
        plan_content = self._read_file(plan_path)
        actions = self._parse_sas_plan(plan_content)

        if not actions:
            logger.error("Piano SAS vuoto")
            return {"error": "Piano vuoto"}

        depth, branching = self._extract_parameters(lore)
        lore_snippet = lore[:1500]

        graph_data = {
            "metadata": {
                "depth": depth,
                "branching": branching,
                "num_actions": len(actions),
                "model": self.model_name
            },
            "actions": []
        }

        logger.info(f"Generazione grafo per {len(actions)} azioni...")
        logger.info(f"Depth: {depth}, Branching: {branching}")

        for action_idx, action in enumerate(actions):
            action_num = action_idx + 1
            logger.info(f"  Processando azione {action_num}/{len(actions)}: {action[:60]}...")

            next_action = actions[action_idx + 1] if action_idx + 1 < len(actions) else "COMPLETARE LA MISSIONE"
            root_context = f"Azione PDDL: {action} | Prossima: {next_action}"

            scene_text = self._generate_scene_description(root_context, lore_snippet)

            nodes = [{
                "id": str(action_num),
                "type": "scene",
                "depth": 0,
                "indent": 0,
                "text": scene_text,
                "parent_context": root_context
            }]

            self._generate_tree_recursive(
                [action_num],
                1,
                depth,
                branching,
                scene_text,
                lore_snippet,
                nodes,
                action_num
            )

            graph_data["actions"].append({
                "action_number": action_num,
                "pddl_action": action,
                "nodes": nodes,
                "total_nodes": len(nodes)
            })

        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # Salva JSON completo
            json_file = output_file.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)

            # Genera anche versione testuale per visualizzazione
            text_output = self._format_text_output(graph_data)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text_output)

            logger.info(f"✅ Grafo JSON salvato: {json_file}")
            logger.info(f"✅ Grafo TXT salvato: {output_file}")

            total_nodes = sum(a['total_nodes'] for a in graph_data['actions'])
            logger.info(f"✅ Totale nodi generati: {total_nodes}")

        except Exception as e:
            logger.error(f"Errore salvataggio: {e}")

        return graph_data

    def _format_text_output(self, graph_data):
        """Formatta il grafo in formato testuale leggibile"""
        lines = []

        for action in graph_data['actions']:
            action_num = action['action_number']

            for node in action['nodes']:
                node_id = node['id']
                indent = '\t' * node['indent']
                node_type = node['type'].upper()[0]  # S=Scene, C=Choice, C=Consequence
                text = node['text']

                # Formatta: ID [tipo] testo
                lines.append(f"{node_id}\t{indent}[{node_type}] {text}")

            lines.append("")  # Separatore tra azioni

        return "\n".join(lines)


# === ESECUZIONE ===
if __name__ == "__main__":
    BASE_PATH = r"C:\Users\ANGELICA\Desktop\ANGELICA\UNICAL\MAGISTRALE\I ANNO\SECONDO SEMESTRE\INTELLIGENZA ARTIFICIALE\PROGETTO\CODICE\QuestMaster"
    LORE_FILE = os.path.join(BASE_PATH, "Lore", "Generated_Lore", "Lore.md")
    PLAN_FILE = os.path.join(BASE_PATH, "ChatBot", "pddl_output", "sas_plan")
    OUTPUT_FILE = os.path.join(BASE_PATH, "Game", "story_graph_interactive.txt")

    generator = StoryGraphGenerator(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model_name="gpt-4o-mini"
    )

    print("=" * 80)
    print("🎮 GENERAZIONE GRAFO INTERATTIVO PER GIOCO WEB")
    print("=" * 80)
    print(f"\n📖 Lore: {os.path.basename(LORE_FILE)}")
    print(f"📋 Piano: {os.path.basename(PLAN_FILE)}")
    print(f"💾 Output: {os.path.basename(OUTPUT_FILE)}")
    print(f"🤖 Modello: gpt-4o-mini")
    print("\n⏳ Avvio generazione...\n")

    graph_data = generator.generate_story_graph(
        lore_path=LORE_FILE,
        plan_path=PLAN_FILE,
        output_file=OUTPUT_FILE
    )

    print("\n" + "=" * 80)
    print("✅ GENERAZIONE COMPLETATA!")
    print("=" * 80)
    print(f"\n📁 File generati:")
    print(f"  • {OUTPUT_FILE} (formato testuale)")
    print(f"  • {OUTPUT_FILE.replace('.txt', '.json')} (formato JSON strutturato)")
    print("\n💡 Struttura del grafo:")
    print("  Livello 0: [S] Scena iniziale")
    print("  Livello 1: [C] Scelte alternative (N opzioni)")
    print("  Livello 2: [C] Conseguenze di ogni scelta")
    print("  Livello 3: [C] Nuove scelte dalle conseguenze")
    print("  Livello 4: [C] Conseguenze...")
    print("  ... fino al livello massimo (depth)")
    print(f"\n🎯 Il file JSON è pronto per essere dato all'LLM per generare l'HTML!")