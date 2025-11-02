# File: QuestMaster/Game/GamePipeline.py

from pathlib import Path
import logging
from typing import Tuple
from .PDDLParser import PDDLGameGraph
from .NarrativeGenerator import NarrativeGenerator
from .HTMLGenerator import InteractiveGameGenerator

logger = logging.getLogger(__name__)


def generate_interactive_game(
        domain_path: Path,
        problem_path: Path,
        plan_path: Path,
        lore_path: Path,
        output_html: Path,
        config: dict
) -> Tuple[bool, str]:
    """
    Pipeline completa per generare il gioco interattivo

    Args:
        domain_path: Path al domain.pddl
        problem_path: Path al problem.pddl
        plan_path: Path al plan_readable.txt
        lore_path: Path al file Lore.md
        output_html: Path dove salvare l'HTML del gioco
        config: Configurazione della quest (dict)

    Returns:
        Tuple[bool, str]: (successo, messaggio)
    """

    try:
        logger.info("=" * 70)
        logger.info("🎮 GENERAZIONE GIOCO INTERATTIVO")
        logger.info("=" * 70)

        # Verifica che i file esistano
        if not domain_path.exists():
            return False, f"Domain PDDL non trovato: {domain_path}"
        if not problem_path.exists():
            return False, f"Problem PDDL non trovato: {problem_path}"
        if not plan_path.exists():
            return False, f"Piano non trovato: {plan_path}"
        if not lore_path.exists():
            return False, f"Lore non trovato: {lore_path}"

        # ==================== STEP 1: Parsing PDDL ====================
        logger.info("\n📋 STEP 1/3: Parsing PDDL e costruzione grafo...")

        parser = PDDLGameGraph(domain_path, problem_path, plan_path)
        states = parser.build_graph()

        logger.info(f"✓ Grafo costruito con successo")
        logger.info(f"  • {len(states)} stati totali")
        logger.info(f"  • {len(parser.graph)} transizioni")

        # Esporta grafo per debug (opzionale)
        debug_dir = output_html.parent / "debug"
        debug_dir.mkdir(exist_ok=True)
        parser.export_to_json(debug_dir / "graph.json")

        # ==================== STEP 2: Generazione Narrativa ====================
        logger.info("\n📖 STEP 2/3: Generazione narrativa con LLM...")
        logger.info("  ⚠️  Questo potrebbe richiedere diversi minuti...")

        narrator = NarrativeGenerator(lore_path, states, parser.graph)
        narratives = narrator.generate_all_narratives()

        logger.info(f"✓ Narrativa generata con successo")
        logger.info(f"  • {len(narratives)} stati narrati")

        # Esporta narrative per debug
        narrator.export_narratives(debug_dir / "narratives.json", narratives)

        # ==================== STEP 3: Generazione HTML ====================
        logger.info("\n🌐 STEP 3/3: Generazione HTML interattivo...")

        generator = InteractiveGameGenerator(
            states=states,
            graph=parser.graph,
            narratives=narratives,
            config=config
        )

        generator.generate_game_html(output_html)

        logger.info(f"✓ HTML generato con successo: {output_html}")

        # ==================== RIEPILOGO ====================
        logger.info("\n" + "=" * 70)
        logger.info("🎉 GIOCO INTERATTIVO GENERATO CON SUCCESSO!")
        logger.info("=" * 70)
        logger.info(f"📂 File generati:")
        logger.info(f"   • Gioco HTML: {output_html}")
        logger.info(f"   • Debug Grafo: {debug_dir / 'graph.json'}")
        logger.info(f"   • Debug Narrativa: {debug_dir / 'narratives.json'}")
        logger.info("=" * 70)

        return True, "Gioco generato con successo!"

    except Exception as e:
        logger.exception("Errore durante la generazione del gioco")
        return False, f"Errore: {str(e)}"


def generate_game_quick_test(output_dir: Path) -> Tuple[bool, str]:
    """
    Funzione di test rapido per verificare la pipeline
    Usa file PDDL di esempio
    """

    try:
        # Percorsi di esempio
        script_dir = Path(__file__).resolve().parent
        pddl_dir = script_dir.parent / "Generate_PDDL" / "pddl_output_guaranteed"
        lore_file = script_dir.parent / "Lore" / "Generated_Lore" / "Lore.md"

        # Configurazione mock
        test_config = {
            'theme': 'Test Quest',
            'genre': 'Fantasy',
            'tone': 'Adventurous',
            'graphics': 'Text Only',
            'length': 'Medium'
        }

        output_html = output_dir / "test_game.html"

        return generate_interactive_game(
            domain_path=pddl_dir / "domain.pddl",
            problem_path=pddl_dir / "problem.pddl",
            plan_path=pddl_dir / "plan_readable.txt",
            lore_path=lore_file,
            output_html=output_html,
            config=test_config
        )

    except Exception as e:
        return False, f"Test fallito: {str(e)}"


if __name__ == '__main__':
    # Configurazione logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Test della pipeline
    script_dir = Path(__file__).resolve().parent
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)

    print("\n🧪 Test della pipeline completa...\n")

    success, message = generate_game_quick_test(output_dir)

    if success:
        print(f"\n✅ {message}")
        print(f"📂 Controlla: {output_dir}/test_game.html")
    else:
        print(f"\n❌ {message}")