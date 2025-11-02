Here is the annotated PDDL file:

(define (domain logistics-simple)
; defines a domain named "logistics-simple"
(:requirements :strips :typing)
; specifies requirements for this domain: STRIPS and typing

(:types location vehicle package)
; defines three types: location, vehicle, and package

(:predicates
  ; defines four predicates:
  (at-vehicle ?v - vehicle ?l - location)
  ; "car is at location"
  ; : comment explains the predicate in plain English
  (at-package ?p - package ?l - location)
  ; "package is at location"
  (in-vehicle ?p - package ?v - vehicle)
  ; "package is inside vehicle"
  (connected ?from ?to - location)
  ; "location A is connected to location B"
  )

(:action move
  ; defines an action named "move"
  :parameters (?v - vehicle ?from ?to - location)
  ; takes two parameters: a vehicle and two locations
  :precondition (and (at-vehicle ?v ?from) (connected ?from ?to))
  ; the preconditions for this action:
  ;   the vehicle is at the from location
  ;   and there's a connection between the from and to locations
  :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to))
  ; the effects of this action:
  ;   the vehicle moves from the from location to the to location
)

(:action load
  ; defines an action named "load"
  :parameters (?p - package ?v - vehicle ?l - location)
  ; takes three parameters: a package, a vehicle, and a location
  :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l))
  ; the preconditions for this action:
  ;   the package is at the location
  ;   and the vehicle is also at the same location
  :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v))
  ; the effects of this action:
  ;   the package moves from the location into the vehicle
)

(:action unload
  ; defines an action named "unload"
  :parameters (?p - package ?v - vehicle ?l - location)
  ; takes three parameters: a package,