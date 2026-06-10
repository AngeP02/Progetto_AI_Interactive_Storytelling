(define (problem elarion-rescue)
  (:domain elarion)
  
  (:objects
    arin - hero
    queen_elara elder_morghen lord_kael - character
    castle_elarion forest_luminara catacombs_morvaan - location
    key_arcane - object
    guardiani_delle_rune clan_dei_forgiatori seguaci_dell_ombra - faction
  )
  
  (:init
    (at arin castle_elarion)
    (at queen_elara castle_elarion)
    (at elder_morghen castle_elarion)
    (at lord_kael castle_elarion)
    (clear_path castle_elarion forest_luminara)
    (clear_path forest_luminara catacombs_morvaan)
    (aligned arin clan_dei_forgiatori)
    (aligned queen_elara guardiani_delle_rune)
    (aligned lord_kael seguaci_dell_ombra)
    (not (sigil_intact))
    (at key_arcane castle_elarion) ; Aggiunto per permettere ad arin di acquisire la chiave
  )
  
  (:goal
    (sigil_intact)
  )
)