(define (problem narrative-problem)
  (:domain narrative-domain)
  (:objects
    hackers illustrated puzzle - character
    objective starting_point description_hackers_and_shadow_agents_compete_in_a_high summary - location
    artifact key - object
  )
    (:init
    (at hackers objective)
    (at-obj artifact starting_point)
    (visited objective)
    (at-obj key description_hackers_and_shadow_agents_compete_in_a_high)
    (at hackers objective)
    (at-obj artifact summary)
    (locked starting_point)
    (locked description_hackers_and_shadow_agents_compete_in_a_high)
    (at-obj artifact objective)
    (key-for artifact starting_point)
    (at-obj key starting_point)
    (key-for key description_hackers_and_shadow_agents_compete_in_a_high)
    (connected starting_point description_hackers_and_shadow_agents_compete_in_a_high)
    (connected starting_point objective)
    (connected description_hackers_and_shadow_agents_compete_in_a_high summary)
    (connected objective starting_point)
    (connected summary description_hackers_and_shadow_agents_compete_in_a_high)
    (connected description_hackers_and_shadow_agents_compete_in_a_high starting_point)
  )
  (:goal (and
    (at hackers summary)
    (has hackers artifact)
  ))
)