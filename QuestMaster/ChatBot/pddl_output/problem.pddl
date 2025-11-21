(define (problem delivery-medium)
  (:domain logistics-simple)
  (:objects
    warehouse depot shop home - location
    truck - vehicle
    package1 package2 - package
  )
  (:init
    (at-vehicle truck warehouse)
    (at-package package1 warehouse)
    (at-package package2 depot)

    (connected warehouse depot)
    (connected depot warehouse)
    (connected depot shop)
    (connected shop depot)
    (connected shop home)
    (connected home shop)
  )
  (:goal
    (and
      (at-package package1 home)
      (at-package package2 shop)
    )
  )
)