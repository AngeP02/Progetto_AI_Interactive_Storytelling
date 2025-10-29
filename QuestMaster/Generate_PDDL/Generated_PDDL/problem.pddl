(define (problem narrative-problem)
  (:domain narrative-domain)
  (:objects 
    dilapidated quest characters - character
    echo description_in_a_gritty objective branching_factor - location
    key artifact tool - object
  )
    (:init
    (at dilapidated echo)
    (at-obj key description_in_a_gritty)
    (visited echo)
    (at characters echo)
    (at key echo)
    (at tool echo)
    (at-obj key branching_factor)
    (locked description_in_a_gritty)
    (locked objective)
    (at-obj key echo)
    (key-for key description_in_a_gritty)
    (at-obj artifact description_in_a_gritty)
    (key-for artifact objective)
    (connected description_in_a_gritty objective)
    (connected objective description_in_a_gritty)
    (connected branching_factor objective)
    (connected echo description_in_a_gritty)
    (connected description_in_a_gritty echo)
    (connected objective branching_factor)
  )
  (:goal 
    (and 
      (at dilapidated branching_factor)
      (has dilapidated key)
    )
  )
)