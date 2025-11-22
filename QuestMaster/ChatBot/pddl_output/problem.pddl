(define (problem quest-medium)
                  (:domain keys-doors-simple)
                  (:objects
                    ingresso_eldersgloom studio_collezionista collezione_quadri camera_segreta - location
                    detective - agent
                    chiave_di_bronzo chiave_dorata - key
                    porta_principale porta_quadro_scomparso - door
                  )
                  (:init
                    (at detective ingresso_eldersgloom)
                    (key-at chiave_di_bronzo ingresso_eldersgloom)
                    (key-at chiave_dorata studio_collezionista)
                    (door-between porta_principale ingresso_eldersgloom studio_collezionista)
                    (door-between porta_quadro_scomparso studio_collezionista collezione_quadri)
                    (locked porta_principale)
                    (locked porta_quadro_scomparso)
                    (unlocks chiave_di_bronzo porta_principale)
                    (unlocks chiave_dorata porta_quadro_scomparso)
                  )
                  (:goal
                    (at detective collezione_quadri)
                  )
                )