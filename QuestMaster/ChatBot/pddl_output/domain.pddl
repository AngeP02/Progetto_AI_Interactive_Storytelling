(define (domain elarion)
  (:requirements :strips :typing)
  
  (:types
    hero character location object faction
  )
  
  (:predicates
    (at ?c - character ?l - location)
    (possession ?h - hero ?o - object)
    (aligned ?c - character ?f - faction)
    (clear_path ?l1 - location ?l2 - location)
    (sigil_intact)
  )
  
  (:action move
    :parameters (?c - character ?from - location ?to - location)
    :precondition (and (at ?c ?from) (clear_path ?from ?to))
    :effect (and (not (at ?c ?from)) (at ?c ?to))
  )
  
  (:action acquire_key
    :parameters (?h - hero ?o - object ?l - location)
    :precondition (and (at ?h ?l) (not (possession ?h ?o)))
    :effect (possession ?h ?o)
  )
  
  (:action restore_sigil
    :parameters (?h - hero ?o - object ?l - location)
    :precondition (and (at ?h ?l) (possession ?h ?o) (not (sigil_intact)))
    :effect (sigil_intact)
  )
)