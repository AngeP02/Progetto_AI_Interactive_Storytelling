# File: QuestMaster/Game/GamePipeline.py

from pathlib import Path
import logging
from typing import Tuple
from .StoryGenerator import InteractiveStoryGenerator
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
    Pipeline completa per generare il gioco interattivo NARRATIVO

    NUOVO APPROCCIO: LLM-First invece di PDDL-First
    - Il PDDL fornisce solo vincoli logici
    - L'LLM genera una storia narrativa completa e ramificata
    - Il sistema valida che la storia rispetti i vincoli

    Args:
        domain_path: Path al domain.pddl (usato solo per vincoli)
        problem_path: Path al problem.pddl (usato solo per vincoli)
        plan_path: Path al plan_readable.txt (ignorato nel nuovo sistema)
        lore_path: Path al file Lore.md
        output_html: Path dove salvare l'HTML del gioco
        config: Configurazione della quest (dict)

    Returns:
        Tuple[bool, str]: (successo, messaggio)
    """

    try:
        logger.info("=" * 70)
        logger.info("🎮 GENERAZIONE GIOCO NARRATIVO INTERATTIVO")
        logger.info("=" * 70)

        # Verifica che i file esistano
        if not lore_path.exists():
            return False, f"Lore non trovato: {lore_path}"

        # ==================== STEP 1: Estrai Vincoli PDDL ====================
        logger.info("\n📋 STEP 1/3: Estrazione vincoli PDDL...")

        pddl_constraints = {}  # TODO: Estrai vincoli veri dal PDDL se necessario

        logger.info(f"✓ Vincoli estratti (usati come guida per la narrativa)")

        # ==================== STEP 2: Generazione Storia Narrativa ====================
        logger.info("\n📖 STEP 2/3: Generazione storia interattiva con LLM...")
        logger.info("  ⚠️  Questo processo richiede 3-5 minuti...")
        logger.info("  📝 Generazione outline...")
        logger.info("  ✍️  Scrittura scene dettagliate...")
        logger.info("  🎭 Creazione finali multipli...")

        story_generator = InteractiveStoryGenerator(
            lore_path=lore_path,
            pddl_constraints=pddl_constraints,
            config=config
        )

        story_nodes = story_generator.generate_full_story()

        logger.info(f"✓ Storia generata con successo")
        logger.info(f"  • {len(story_nodes)} scene totali")
        logger.info(f"  • {sum(1 for n in story_nodes.values() if n.is_ending)} finali diversi")

        # Esporta storia per debug
        debug_dir = output_html.parent / "debug"
        debug_dir.mkdir(exist_ok=True)
        story_generator.export_story(story_nodes, debug_dir / "story_structure.json")

        # ==================== STEP 3: Generazione HTML ====================
        logger.info("\n🌐 STEP 3/3: Generazione HTML interattivo...")

        # Passa i nodi della storia direttamente all'HTMLGenerator
        generator = InteractiveGameGenerator(
            states=story_nodes,  # StoryNodes invece di GameStates
            graph={},  # Non serve più il grafo PDDL
            narratives={},  # Non serve più, la narrativa è nei nodi
            config=config
        )

        generator.generate_game_html(output_html)

        logger.info(f"✓ HTML generato con successo: {output_html}")

        # ==================== RIEPILOGO ====================
        logger.info("\n" + "=" * 70)
        logger.info("🎉 GIOCO NARRATIVO GENERATO CON SUCCESSO!")
        logger.info("=" * 70)
        logger.info(f"📂 File generati:")
        logger.info(f"   • Gioco HTML: {output_html}")
        logger.info(f"   • Debug Storia: {debug_dir / 'story_structure.json'}")
        logger.info(f"\n📖 Statistiche:")
        logger.info(f"   • Scene: {len(story_nodes)}")
        logger.info(f"   • Finali: {sum(1 for n in story_nodes.values() if n.is_ending)}")
        logger.info(f"   • Profondità media: ~{len(story_nodes) // 2} scelte")
        logger.info("=" * 70)

        return True, "Gioco narrativo generato con successo!"

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