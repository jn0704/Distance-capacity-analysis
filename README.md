# Distance-capacity-analysis

The distance-capacity analysis (DCA) assumes the standard evacuation route planning that pre-calculates and informs evacuation routes to citizens before disasters. DCA calculates the shortest path from populations to shelters as evacuation routes. In addition, DCA pre-calculates which shelters will be occupied and assigns populations to unoccupied shelters. The difference with the unassigned shelter analysis is that individuals are guaranteed to have a spot available at their assigned shelter, avoiding visits to multiple shelters and reducing overall distance traveled. USA assigns pedestrians while they evacuate in earthquake situations, but DCA simulates this assignment before earthquakes and informs the final calculated evacuation routes to pedestrians. 

* Step 1: Identify the shortest path from population node i to shelter node j, where P_i > 0 and C_j > 0
* Step 2: If C_j ≥ P_i, assign P_i to the path. Next, C_j = C_j - P_i and P_i = 0
* Step 3: If C_j < P_i, assign P_i - C_j to the path. Next, C_j = 0 and P_i = P_i - C_j
* Step 4: If the sum of populations or shelter capacities is zero, end the process. If not, we return to step 1
