(define (problem grid-navigation-problem)
  (:domain grid-navigation)
  (:objects
    new_eden_city_center the_undercity omicron_tower raven_s_peak - position
    nova - agent
  )
  (:init
    (at nova new_eden_city_center)
    (clear the_undercity)
    (clear omicron_tower)
    (clear raven_s_peak)
    (goal-pos raven_s_peak)
    (adjacent new_eden_city_center the_undercity)
    (adjacent the_undercity new_eden_city_center)
    (adjacent the_undercity omicron_tower)
    (adjacent omicron_tower the_undercity)
    (adjacent omicron_tower raven_s_peak)
    (adjacent raven_s_peak omicron_tower)
  )
  (:goal
    (at nova raven_s_peak)
  )
)