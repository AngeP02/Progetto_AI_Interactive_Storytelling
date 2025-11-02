Here is the annotated PDDL file:

(define (domain keys-doors-simple)
; defines a domain named "keys-doors-simple"
(:requirements :strips :typing)
; specifies that this domain uses STRIPS and typing

(:types location key door agent)
; declares four types: location, key, door, and agent

(:predicates
  (at ?a - agent ?l - location)
; defines a predicate "at" that says an agent is at a location
  (key-at ?k - key ?l - location)
; defines a predicate "key-at" that says a key is at a location
  (has-key ?a - agent ?k - key)
; defines a predicate "has-key" that says an agent has a key
  (door-between ?d - door ?l1 ?l2 - location)
; defines a predicate "door-between" that says a door connects two locations
  (locked ?d - door)
; defines a predicate "locked" that says a door is locked
  (unlocks ?k - key ?d - door)
; defines a predicate "unlocks" that says a key unlocks a door
)

(:action move
 ; defines an action named "move"
 :parameters (?a - agent ?from ?to - location ?d - door)
 ; parameters: an agent, from and to locations, and a door
 :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d)))
 ; preconditions: the agent is at the from location, the door connects the from and to locations, and the door is not locked
 :effect (and (not (at ?a ?from)) (at ?a ?to))
 ; effects: the agent is no longer at the from location, and the agent is now at the to location
)

(:action pick-key
 ; defines an action named "pick-key"
 :parameters (?a - agent ?k - key ?l - location)
 ; parameters: an agent, a key, and a location
 :precondition (and (at ?a ?l) (key-at ?k ?l))
 ; preconditions: the agent is at the location, and the key is at the location
 :effect (and (not (key-at ?k ?l)) (has-key ?a ?k))
 ; effects: the key is no longer at