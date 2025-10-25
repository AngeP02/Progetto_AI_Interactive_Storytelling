(define (problem narrative-problem)
  (:domain narrative-domain)

  (:objects
    the_lost_code minimum you - character
    secretroom entrance laboratory storage mainhall - location
    system key code - object
  )

  (:init
    (at the_lost_code secretroom)
    (connected secretroom entrance)
    (connected entrance secretroom)
    (accessible system entrance)
    (unlocked secretroom)
    (visited secretroom)
    (connected entrance laboratory)
    (connected laboratory storage)
    (connected storage mainhall)
    (connected mainhall entrance)
    (at minimum laboratory)
    (at you mainhall)
    (unlocked laboratory)
    (visited mainhall)
    (accessible key secretroom)
    (accessible code storage)
  )

  (:goal (and
    (at the_lost_code mainhall)
    (has the_lost_code system)
  ))
)