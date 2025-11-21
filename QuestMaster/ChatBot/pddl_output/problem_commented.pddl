```pddl
(define (problem delivery-medium) ; Defines the problem named 'delivery-medium'
  (:domain logistics-simple) ; Specifies the domain 'logistics-simple' to use
  (:objects ; Declares the objects used in the problem
    warehouse depot Negozio home - location ; Defines locations: warehouse, depot, Negozio, home
    truck - vehicle ; Defines a vehicle: truck
    package1 package2 - package ; Defines packages: package1, package2
  )
  (:init ; Specifies the initial state of the problem
    (at-vehicle truck warehouse) ; The truck is initially at the warehouse
    (at-package package1 warehouse) ; Package1 is initially at the warehouse
    (at-package package2 depot) ; Package2 is initially at the depot

    (connected warehouse depot) ; Warehouse and depot are connected
    (connected depot warehouse) ; Depot and warehouse are connected
    (connected depot Negozio) ; Depot and Negozio are connected
    (connected Negozio depot) ; Shop and depot are connected
    (connected Negozio home) ; Shop and home are connected
    (connected home Negozio) ; Home and Negozio are connected
  )
  (:goal ; Defines the goal state to be achieved
    (and ; Specifies that both conditions must be true
      (at-package package1 home) ; Package1 must be at home
      (at-package package2 Negozio) ; Package2 must be at Negozio
    )
  )
)
```