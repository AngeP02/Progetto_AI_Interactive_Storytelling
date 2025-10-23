import os


def generate_lore_document(self, config):
    lore = f"""
=== LORE DOCUMENT ===
Titolo: {config.get('theme', 'Untitled Quest')}

Descrizione:
Questa missione appartiene al genere {config.get('genre')}, con tono {config.get('tone').lower()}.
È un'avventura {config.get('length')} e sarà rappresentata in modalità {config.get('graphics')}.

Tema:
{config.get('theme')}

Stato Iniziale:
- Il protagonista si trova nel luogo iniziale della storia.
- L'obiettivo principale deve ancora essere definito durante la generazione PDDL.

Obiettivo:
- Raggiungere lo scopo narrativo del tema descritto.

Fattore di Ramificazione:
- Min: 2, Max: 4

Vincoli di Profondità:
- Min: 4, Max: 8
"""
    # salva su file
    os.makedirs("lore_files", exist_ok=True)
    filename = f"lore_files/{config.get('genre','quest').replace(' ','_')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(lore)
    return filename
