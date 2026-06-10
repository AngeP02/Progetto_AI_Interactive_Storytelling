```pddl
(define (problem elarion-rescue)
  (:domain elarion) ; Definisce il dominio di appartenenza del problema
  
  (:objects
    arin - hero ; L'eroe del problema
    queen_elara elder_morghen lord_kael - character ; Personaggi coinvolti nel problema
    castle_elarion forest_luminara catacombs_morvaan - location ; Luoghi rilevanti per il problema
    key_arcane - object ; Oggetto chiave per la risoluzione del problema
    guardiani_delle_rune clan_dei_forgiatori seguaci_dell_ombra - faction ; Fazioni presenti nel problema
  )
  
  (:init
    (at arin castle_elarion) ; Posizione iniziale di Arin
    (at queen_elara castle_elarion) ; Posizione iniziale della regina Elara
    (at elder_morghen castle_elarion) ; Posizione iniziale di Elder Morghen
    (at lord_kael castle_elarion) ; Posizione iniziale di Lord Kael
    (clear_path castle_elarion forest_luminara) ; Percorso libero tra il castello e la foresta
    (clear_path forest_luminara catacombs_morvaan) ; Percorso libero tra la foresta e le catacombe
    (aligned arin clan_dei_forgiatori) ; Arin è allineato con il Clan dei Forgiatori
    (aligned queen_elara guardiani_delle_rune) ; La regina Elara è allineata con i Guardiani delle Rune
    (aligned lord_kael seguaci_dell_ombra) ; Lord Kael è allineato con i Seguaci dell'Ombra
    (not (sigil_intact)) ; Il sigillo non è intatto inizialmente
    (at key_arcane castle_elarion) ; La chiave arcana si trova nel castello di Elarion
  )
  
  (:goal
    (sigil_intact) ; Obiettivo: rendere il sigillo intatto
  )
)
```