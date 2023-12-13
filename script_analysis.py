from simulate_functions import auslegung_erzeuger

import cProfile
import pstats

# Profiling starten
cProfile.run('auslegung_erzeuger()', 'output_filename.prof')

# Profiling-Ergebnisse lesen und ausgeben
p = pstats.Stats('output_filename.prof')
p.sort_stats('cumulative').print_stats(10)  # Top 10 Funktionen nach Gesamtzeit sortiert