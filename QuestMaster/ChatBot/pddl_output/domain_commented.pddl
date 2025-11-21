Here is the annotated PDDL file:

(define (domain logistics-simple)
; defines a domain named "logistics-simple"
(:requirements :strips :typing)
; specifies that this domain uses STRIPS and typing for reasoning

(:types location vehicle package)
; declares three types: location, vehicle, and package

(:predicates
  (at-vehicle ?v - vehicle ?l - location)
; defines a predicate "at-vehicle" stating that a vehicle is at a location
  (at-package ?p - package ?l - location)
; defines a predicate "at-package" stating that a package is at a location
  (in-vehicle ?p - package ?v - vehicle)
; defines a predicate "in-vehicle" stating that a package is in a vehicle
  (connected ?from ?to - location)
; defines a predicate "connected" stating that two locations are connected
)

(:action move
  :parameters (?v - vehicle ?from ?to - location)
  ; defines an action "move" with parameters: vehicle and two locations
  :precondition (and (at-vehicle ?v ?from) (connected ?from ?to))
  ; specifies the conditions required for this action to be executed (i.e., the vehicle is at the from location, and the locations are connected)
  :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to))
  ; specifies what happens when this action is executed (i.e., the vehicle moves from the from location to the to location)
)

(:action load
  :parameters (?p - package ?v - vehicle ?l - location)
  ; defines an action "load" with parameters: package, vehicle, and location
  :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l))
  ; specifies the conditions required for this action to be executed (i.e., the package is at the location, and the vehicle is also at that location)
  :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v))
  ; specifies what happens when this action is executed (i.e., the package moves from the location to the vehicle)
)

(:action unload
  :parameters (?p - package ?v - vehicle ?l - location)
  ; defines an action "unload" with parameters: package, vehicle