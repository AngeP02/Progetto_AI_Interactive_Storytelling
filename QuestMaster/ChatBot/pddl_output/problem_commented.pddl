```pddl
(define (problem delivery-medium) ; Define a problem named "delivery-medium"
  (:domain logistics-simple) ; The problem uses the "logistics-simple" domain
  (:objects ; Declare the objects present in the problem
    warehouse depot shop home - location ; Define locations: warehouse, depot, shop, and home
    truck - vehicle ; Define a vehicle: truck
    package1 package2 - package ; Define packages: package1 and package2
  )
  (:init ; Initial state of the problem
    (at-vehicle truck warehouse) ; The truck is initially at the warehouse
    (at-package package1 warehouse) ; Package1 is initially at the warehouse
    (at-package package2 depot) ; Package2 is initially at the depot

    (connected warehouse depot) ; Warehouse and depot are directly connected
    (connected depot warehouse) ; Depot and warehouse are directly connected
    (connected depot shop) ; Depot and shop are directly connected
    (connected shop depot) ; Shop and depot are directly connected
    (connected shop home) ; Shop and home are directly connected
    (connected home shop) ; Home and shop are directly connected
  )
  (:goal ; Define the goal state
    (and ; Both conditions must be satisfied
      (at-package package1 home) ; Package1 must be at home
      (at-package package2 shop) ; Package2 must be at the shop
    )
  )
)
```