(define (domain narrative-domain)
  (:requirements :strips :typing)

  (:types 
    character location object - thing
  )

  (:predicates 
    (at ?c - character ?l - location)
    (has ?c - character ?o - object)
    (connected ?l1 - location ?l2 - location)
    (accessible ?o - object ?l - location)
    (visited ?l - location)
    (unlocked ?l - location)
  )

  (:action move
    :parameters (?c - character ?from - location ?to - location)
    :precondition (and 
      (at ?c ?from) 
      (connected ?from ?to)
      (unlocked ?to)
    )
    :effect (and 
      (not (at ?c ?from)) 
      (at ?c ?to)
      (visited ?to)
    )
  )

  (:action take
    :parameters (?c - character ?o - object ?l - location)
    :precondition (and 
      (at ?c ?l) 
      (accessible ?o ?l)
    )
    :effect (and 
      (has ?c ?o) 
      (not (accessible ?o ?l))
    )
  )

  (:action use
    :parameters (?c - character ?o - object ?l - location)
    :precondition (and 
      (at ?c ?l) 
      (has ?c ?o)
    )
    :effect (unlocked ?l)
  )

  (:action interact
    :parameters (?c1 - character ?c2 - character ?l - location)
    :precondition (and 
      (at ?c1 ?l) 
      (at ?c2 ?l)
    )
    :effect ()
  )

  (:action combine
    :parameters (?c - character ?o1 - object ?o2 - object ?l - location)
    :precondition (and 
      (at ?c ?l) 
      (has ?c ?o1) 
      (has ?c ?o2)
    )
    :effect (not (accessible ?o1 ?l)) 
  )
)