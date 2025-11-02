# File: QuestMaster/Game/__init__.py

"""
QuestMaster Game Module
Genera giochi narrativi interattivi da PDDL
"""

from .GamePipeline import generate_interactive_game, generate_game_quick_test
from .PDDLParser import PDDLGameGraph, GameState, GameAction
from .NarrativeGenerator import NarrativeGenerator
from .HTMLGenerator import InteractiveGameGenerator

__all__ = [
    'generate_interactive_game',
    'generate_game_quick_test',
    'PDDLGameGraph',
    'GameState',
    'GameAction',
    'NarrativeGenerator',
    'InteractiveGameGenerator'
]

__version__ = '1.0.0'