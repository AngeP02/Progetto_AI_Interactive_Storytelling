(define (problem keys-doors-problem)
  (:domain keys-doors)
  (:objects
    the_last_rays_tavern cloudhaven wandering_isles - location
    the_lost_one - agent
    key1 - key
    door0 door1 - door
  )
  (:init
    (at the_lost_one the_last_rays_tavern)
    (key-at key1 the_last_rays_tavern)
    (door-between door0 the_last_rays_tavern cloudhaven)
    (locked door0)
    (unlocks key1 door0)
    (door-between door1 cloudhaven wandering_isles)
    (locked door1)
  )
  (:goal
    (at the_lost_one wandering_isles)
  )
)