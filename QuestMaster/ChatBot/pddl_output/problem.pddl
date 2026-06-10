(define (problem quest-medium)
                  (:domain keys-doors-simple)
                  (:objects
                    ingresso_montagna_ombre sala_regia stanza_tesoro_thalorax cella_magica - location
                    eroe_prescelto - agent
                    chiave_bronzo chiave_oro - key
                    porta_principale_eldoria porta_tesoro - door
                  )
                  (:init
                    (at eroe_prescelto ingresso_montagna_ombre)
                    (key-at chiave_bronzo ingresso_montagna_ombre)
                    (key-at chiave_oro sala_regia)
                    (door-between porta_principale_eldoria ingresso_montagna_ombre sala_regia)
                    (door-between porta_tesoro sala_regia stanza_tesoro_thalorax)
                    (locked porta_principale_eldoria)
                    (locked porta_tesoro)
                    (unlocks chiave_bronzo porta_principale_eldoria)
                    (unlocks chiave_oro porta_tesoro)
                  )
                  (:goal
                    (at eroe_prescelto stanza_tesoro_thalorax)
                  )
                )