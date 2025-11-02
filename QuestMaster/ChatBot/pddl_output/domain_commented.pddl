Here is the annotated PDDL file:

(define (domain logistics-simple) ; defines a domain named "logistics-simple"
(:requirements :strips :typing) ; specifies the requirements for this domain
(:types location vehicle package) ; declares three types: location, vehicle, and package
(:predicates 
  (at-vehicle ?v - vehicle ?l - location) ; predicate indicating a vehicle is at a location
  (at-package ?p - package ?l - location) ; predicate indicating a package is at a location
  (in-vehicle ?p - package ?v - vehicle) ; predicate indicating a package is in a vehicle
  (connected ?from ?to - location) ; predicate indicating two locations are connected
)

(:action move ; defines an action named "move"
 :parameters (?v - vehicle ?from ?to - location) ; specifies the parameters for this action
 :precondition (and (at-vehicle ?v ?from) (connected ?from ?to)) ; specifies the conditions required before this action can be executed
 :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to)) ; specifies the effects of executing this action
)

(:action load ; defines an action named "load"
 :parameters (?p - package ?v - vehicle ?l - location) ; specifies the parameters for this action
 :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l)) ; specifies the conditions required before this action can be executed
 :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v)) ; specifies the effects of executing this action
)

(:action unload ; defines an action named "unload"
 :parameters (?p - package ?v - vehicle ?l - location) ; specifies the parameters for this action
 :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l)) ; specifies the conditions required before this action can be executed
 :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l)) ; specifies the effects of executing this action
)