Here is the annotated PDDL file:

(define (domain logistics-simple)
  (:requirements ; specifies the necessary features for the domain, in this case, STRIPS and TYING
    :strips :typing)
  (:types ; defines the types of objects in the domain
    location vehicle package)
  (:predicates ; declares the predicates or facts that are true in the domain
    (at-vehicle ?v - vehicle ?l - location) ; describes an object at a specific location
    (at-package ?p - package ?l - location) ; describes a package at a specific location
    (in-vehicle ?p - package ?v - vehicle) ; describes a package inside a vehicle
    (connected ?from ?to - location) ; describes two locations being connected
  )

(:action move ; defines an action that can be performed in the domain
  :parameters (?v - vehicle ?from ?to - location) ; specifies the parameters for this action
  :precondition (and ; specifies the conditions that must be true before this action can be executed
    (at-vehicle ?v ?from) ; the vehicle is at the from location
    (connected ?from ?to)) ; the from and to locations are connected
  :effect (and ; specifies the effects of this action when it is executed
    (not (at-vehicle ?v ?from)) ; the vehicle is no longer at the from location
    (at-vehicle ?v ?to)) ; the vehicle is now at the to location
)

(:action load ; defines an action that can be performed in the domain
  :parameters (?p - package ?v - vehicle ?l - location) ; specifies the parameters for this action
  :precondition (and ; specifies the conditions that must be true before this action can be executed
    (at-package ?p ?l) ; the package is at the location
    (at-vehicle ?v ?l)) ; the vehicle is also at the location
  :effect (and ; specifies the effects of this action when it is executed
    (not (at-package ?p ?l)) ; the package is no longer at the location
    (in-vehicle ?p ?v)) ; the package is now inside the vehicle
)

(:action unload ; defines an action that can be performed in the domain
  :parameters (?p - package ?v - vehicle ?