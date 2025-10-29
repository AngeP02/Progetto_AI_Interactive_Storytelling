(define (domain narrative-domain)
  (:requirements :strips :typing)
  (:types character location object - thing)
  (:predicates 
    (at ?c - character ?l - location)
    (has ?c - character ?o - object)
    (connected ?l1 - location ?l2 - location)
    (at-obj ?o - object ?l - location)
    (visited ?l - location)
    (locked ?l - location)
    (key-for ?o - object ?l - location)
  )
  (:action move
    :parameters (?c - character ?from - location ?to - location)
    :precondition (and (at ?c ?from) (connected ?from ?to) (not (locked ?to)))
    :effect (and (not (at ?c ?from)) (at ?c ?to) (visited ?to))
  )
  (:action take
    :parameters (?c - character ?o - object ?l - location)
    :precondition (and (at ?c ?l) (at-obj ?o ?l))
    :effect (and (has ?c ?o) (not (at-obj ?o ?l)))
  )
  (:action unlock
    :parameters (?c - character ?l - location ?k - object)
    :precondition (and (at ?c ?l) (key-for ?k ?l) (locked ?l))
    :effect (and (not (locked ?l)) (has ?c ?k))
  )
  (:action interact
    :parameters (?c1 - character ?c2 - character)
    :precondition (and (at ?c1 ?l) (at ?c2 ?l))
    :effect ()
  )
  (:action use
    :parameters (?c - character ?o - object ?l - location)
    :precondition (and (at ?c ?l) (has ?c ?o) (at-obj ?o ?l))
    :effect (and (not (at-obj ?o ?l)) (visited ?l))
  )
)

(:action hack
    :parameters (?c - character ?l - location)
    :precondition (and (at ?c ?l) (connected ?l objective))
    :effect (and (visited ?l) (has ?c artifact))
  )

(:action puzzle
    :parameters (?c - character ?o - object ?l - location)
    :precondition (and (at ?c ?l) (at-obj ?o ?l))
    :effect (and (not (at-obj ?o ?l)) (visited ?l))
  )

(:action illustrated
    :parameters (?c - character ?l - location)
    :precondition (and (at ?c ?l) (connected ?l summary))
    :effect (and (visited ?l) (has ?c key-for artifact summary))
  )