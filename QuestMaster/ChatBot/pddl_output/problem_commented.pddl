```pddl
(define (problem quest-medium) ; Definisce il problema chiamato "quest-medium"
  (:domain keys-doors-simple) ; Specifica il dominio di appartenenza, "keys-doors-simple"
  (:objects
    ingresso_eldersgloom studio_collezionista collezione_quadri camera_segreta - location ; Definisce le location
    detective - agent ; Definisce l'agente "detective"
    chiave_di_bronzo chiave_dorata - key ; Definisce le chiavi
    porta_principale porta_quadro_scomparso - door ; Definisce le porte
  )
  (:init
    (at detective ingresso_eldersgloom) ; Il detective si trova all'ingresso di Eldersgloom
    (key-at chiave_di_bronzo ingresso_eldersgloom) ; La chiave di bronzo è all'ingresso di Eldersgloom
    (key-at chiave_dorata studio_collezionista) ; La chiave dorata è nello studio del collezionista
    (door-between porta_principale ingresso_eldersgloom studio_collezionista) ; La porta principale collega l'ingresso di Eldersgloom e lo studio del collezionista
    (door-between porta_quadro_scomparso studio_collezionista collezione_quadri) ; La porta del quadro scomparso collega lo studio del collezionista e la collezione di quadri
    (locked porta_principale) ; La porta principale è chiusa a chiave
    (locked porta_quadro_scomparso) ; La porta del quadro scomparso è chiusa a chiave
    (unlocks chiave_di_bronzo porta_principale) ; La chiave di bronzo apre la porta principale
    (unlocks chiave_dorata porta_quadro_scomparso) ; La chiave dorata apre la porta del quadro scomparso
  )
  (:goal
    (at detective collezione_quadri) ; L'obiettivo è che il detective si trovi nella collezione di quadri
  )
)
```