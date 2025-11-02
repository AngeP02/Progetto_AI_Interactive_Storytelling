(define (problem keys-doors-problem)
  (:domain keys-doors)
  (:objects
    helios_station celestial_horizon_initiative_s_chi_headquarters the_dreamscape - location
    dr_sophia_patel - agent
    key0 - key
    door0 door1 - door
  )
  (:init
    (at dr_sophia_patel helios_station)
    (door-between door0 helios_station celestial_horizon_initiative_s_chi_headquarters)
    (door-between door1 celestial_horizon_initiative_s_chi_headquarters helios_station)
    (locked door1)
    (unlocks key0 door1)
    (key-at key0 celestial_horizon_initiative_s_chi_headquarters)
    (door-between door2 the_dreamscape celestial_horizon_initiative_s_chi_headquarters)
    (locked door2)
    (unlocks key1 door2)
    (key-at key1 the_dreamscape)
    (door-between door3 celestial_horizon_initiative_s_chi_headquarters the_dreamscape)
    (locked door3)
    (unlocks key2 door3)
    (key-at key2 celestial_horizon_initiative_s_chi_headquarters)
  )
  (:goal
    (at dr_sophia_patel the_dreamscape)
  )
)