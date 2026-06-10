```pddl
(define (domain elarion)
  (:requirements :strips :typing) ; Specifica i requisiti del dominio: STRIPS e tipizzazione

  (:types
    hero character location object faction ; Definisce i tipi di oggetti nel dominio
  )

  (:predicates
    (at ?c - character ?l - location) ; Verifica se un personaggio si trova in una location
    (possession ?h - hero ?o - object) ; Verifica se un eroe possiede un oggetto
    (aligned ?c - character ?f - faction) ; Verifica se un personaggio è allineato a una fazione
    (clear_path ?l1 - location ?l2 - location) ; Verifica se c'è un percorso libero tra due location
    (sigil_intact) ; Verifica se il sigillo è intatto
  )

  (:action move
    :parameters (?c - character ?from - location ?to - location) ; Parametri: un personaggio e due location
    :precondition (and (at ?c ?from) (clear_path ?from ?to)) ; Precondizioni: il personaggio è nella location di partenza e il percorso è libero
    :effect (and (not (at ?c ?from)) (at ?c ?to)) ; Effetti: il personaggio non è più nella location di partenza e si trova nella location di arrivo
  )

  (:action acquire_key
    :parameters (?h - hero ?o - object ?l - location) ; Parametri: un eroe, un oggetto e una location
    :precondition (and (at ?h ?l) (not (possession ?h ?o))) ; Precondizioni: l'eroe è nella location e non possiede già l'oggetto
    :effect (possession ?h ?o) ; Effetto: l'eroe acquisisce il possesso dell'oggetto
  )

  (:action restore_sigil
    :parameters (?h - hero ?o - object ?l - location) ; Parametri: un eroe, un oggetto e una location
    :precondition (and (at ?h ?l) (possession ?h ?o) (not (sigil_intact))) ; Precondizioni: l'eroe è nella location, possiede l'oggetto, e il sigillo non è intatto
    :effect (sigil_intact) ; Effetto: il sigillo viene restaurato
  )
)
```