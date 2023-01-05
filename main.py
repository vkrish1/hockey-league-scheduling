import pandas as pd
import pulp
import itertools


# ======================================
# ====== Start of Inputs ===============
# See README for how these should be formatted (and how to format CSVs if you want)

teams_divisions = [  # team name and division
    ['A', 'A'],
    ['B', 'A'],
    ['C', 'A'],
    ['D', 'B'],
    ['E', 'B'],
    ['F', 'B']
]
num_games_per_team = 2  # NOTE this should be set independent of how many teams there are. 24 I think.
teams_divisions = pd.DataFrame(teams_divisions, columns=['Name', 'Division'])
num_teams = teams_divisions.shape[0]
team_names = teams_divisions.Name.tolist() 
divisions = teams_divisions.Division.tolist()

# Rinks and hardcoded rink times
rink_descriptions = [
    ['R1', '01/01/2023', 800, 120],
    ['R1', '01/02/2023', 800, 120],
    ['R1', '01/03/2023', 800, 120],
    ['R1', '01/01/2023', 1200, 120],
    ['R1', '01/01/2023', 1400, 120],
    ['R2', '01/01/2023', 1400, 120],
    ['R2', '01/02/2023', 1400, 120],
    ['R2', '01/01/2023', 1800, 120],
    ['R2', '01/02/2023', 1800, 120],
    ['R3', '01/01/2023', 10000, 0], # give it a large time for toy example to rank poorly so it never picks this
    ['R4', '01/01/2023', 10000, 0], # 
    ['R5', '01/01/2023', 10000, 0], # 
    ['R6', '01/01/2023', 10000, 0] # Just so we have 6 rinks
]
rink_descriptions = pd.DataFrame(rink_descriptions, columns=['Name', 'Date', 'StartTime', 'Duration'])
rink_names = rink_descriptions.Name.unique().tolist()
num_rink_times = rink_descriptions.shape[0]


# Preferences. Okay so each team ranks each rink and each time as ordinal preferences
# I know it's oppposite, but easier to be doing 1 as "most preferred" and arbitrarilly large number for least preferred
# Toy example only wants us to use Rink1 and Rink2, so setting most preferences here to 10
rink_preferences = [
    # Team-is-the-index, then: Rink1, Rink2,    Rink6
    [1, 2, 10, 10, 10, 10],  # Team A
    [2, 1, 10, 10, 10, 10],  # Team B
    [2, 1, 10, 10, 10, 10],  # Team C
    [1, 1, 10, 10, 10, 10],
    [2, 1, 10, 10, 10, 10],
    [2, 1, 10, 10, 10, 10],
]
rink_preferences = pd.DataFrame(rink_preferences, index=team_names, columns=rink_names)

# The colunns here are probably radial choices on a google form? Something like 8am-10am, 12pm-2pm, etc
# So the queried choices may not align exactly with the rink available times. 
# Encode them like this:
time_preference_choices = [ 
    [0, 800], # midnight to 8am  # NOTE: Players should think of this as 0 to 7:59
    [800, 1200],  # 8am to noon  # And this as 8am to 11:59am 
    [1200, 1600], # noon to 4pm  # (this is important)
    [1600, 2000],  # 4pm to 8pm
    [2000, 20000]  # 8pm to rest of the universe (should be 2400)
    ]
time_preferences = [
    # Team, **time_preference_choices as the rest of the (5) columns
    # NOTE: it's important that the range doesn't go to 0. Can fix it if it does, but annoying
    [1, 2, 10, 10, 10],  # associated with Team A
    [2, 1, 10, 10, 10],  # associated with B
    [2, 1, 10, 10, 10],
    [1, 1, 2, 10, 10],
    [2, 1, 3, 10, 10],
    [3, 2, 1, 10, 10],   # .. with team n
]
time_preferences = pd.DataFrame(time_preferences, index=team_names, columns=[str(t) for t in time_preference_choices])


# ========== End of Inputs ==============





# ========== Start of helper functions ==========

def print_solution(var_name):
    ' Helper - print a solution of the form (i, j, k)'
    team_ix_a, team_ix_b, rinktime_ix = int(var_name[3]), int(var_name[6]), int(var_name[6])
    team_name_a = team_names[team_ix_a]
    team_name_b = team_names[team_ix_b]
    rink_name = rink_descriptions.iloc[rinktime_ix].Name
    rink_time = rink_descriptions.iloc[rinktime_ix].StartTime
    queried_rink_range = [a for a in time_preference_choices if rink_time in range(*a)][0]

    rinkpreference_a = rink_preferences.loc[team_name_a][rink_name].item()
    rinkpreference_b = rink_preferences.loc[team_name_b][rink_name].item()
    
    timepreference_a = time_preferences.loc[team_name_a][str(queried_rink_range)].item()
    timepreference_b = time_preferences.loc[team_name_b][str(queried_rink_range)].item()

    print(f"({team_ix_a},{team_ix_b},{rinktime_ix})\t{team_name_a} x {team_name_b} x {rink_name} x {rink_time}\t|| Prefs: {team_name_a} ranked rink:{rinkpreference_a}, time:{timepreference_a}    {team_name_b} ranked rink:{rinkpreference_b}, time:{timepreference_b}")
    

def difference_time(team_ix_a, team_ix_b, rinktime_ix):
    ''' Return the positive integer associated with how perferred the rink time is.
        Gets preferences from dataframe `time_preferences`
        Smaller is better (doing a minimization)
    '''
    # First get the team_names from the indices:
    team_name_a = team_names[team_ix_a]
    team_name_b = team_names[team_ix_b]

    # Get the time associated with rinktime_ix
    time_allotted = rink_descriptions.iloc[rinktime_ix].StartTime

    # Get the time range that we queried people for.
    queried_time_range = [a for a in time_preference_choices if time_allotted in range(*a)][0]

    # Then we can access by index into time_preferences to get each teams time preference for
    # the slot that rinktime_ix is in
    time_preference_a = time_preferences.loc[team_name_a, str(queried_time_range)]
    time_preference_b = time_preferences.loc[team_name_b, str(queried_time_range)]

    return time_preference_a + time_preference_b

def difference_rink(team_ix_a, team_ix_b, rinktime_ix):
    ' Return the positive integer associated with how perferred the rink is. '

    # First get the team_names from the indices:
    team_name_a = team_names[team_ix_a]
    team_name_b = team_names[team_ix_b]

    # Get the rink associated with rinktime_ix
    rink_name = rink_descriptions.iloc[rinktime_ix].Name

    # The two teams rink preferences:
    rink_preference_a = rink_preferences.loc[team_name_a, str(rink_name)]
    rink_preference_b = rink_preferences.loc[team_name_b, str(rink_name)]

    return rink_preference_a + rink_preference_b


# ========== End of helper functions ==========







# ========== Start of optimiation ==========
# Okay define variables of the optimization:
# Solve for X_ijk. Each X_ijk is a game where team i plays team j at rink-time k
# (rink-time k is a row in the rink_descriptions table). 
# If x ==1 , game goes into the schedule. If x==0 it doesnt

prob = pulp.LpProblem('Scheduling', pulp.LpMinimize)

dim_i = num_teams
dim_j = num_teams
dim_k = num_rink_times

# Define the binary variable solutions
x = pulp.LpVariable.dicts(
                    'x', 
                    itertools.product(range(dim_i), range(dim_j), range(dim_k)),
                    cat='Binary')

# Constraint 1: each rink-time can only be used at most once (note: it doesn't have to be used)
for rinktime in range(dim_k):
    constraint = pulp.lpSum(x[(i, j, rinktime)] for i in range(dim_i) for j in range(dim_j)) <= 1
    prob += constraint

# Constraints 2-4
for i in range(dim_i):
    for j in range(dim_j):

        # Constraint 2: a team cant play itself
        if i == j:  
            constraint = pulp.lpSum(x[i, j, k] for k in range(dim_k)) == 0 
        
        # Constraint 3: a team can only play same division
        elif divisions[i] != divisions[j]:  
            constraint = pulp.lpSum(x[i, j, k] for k in range(dim_k)) == 0 

        # Constraint 4: a pair can only play a game once (TODO: might not be true)
        else:
            constraint = pulp.lpSum([v for k, v in x.items()
                            if ((i == k[0] and j == k[1]) or (i == k[1] and j == k[0]))]) == 1

        prob += constraint


# Contraint 5: each team should play num_games_per_team
for teami in range(dim_i):
    constraint = pulp.lpSum([v for k, v in x.items()
                            if (teami == k[0] or teami == k[1])]) == num_games_per_team
    prob += constraint


# Minimize objective (maximize preferences)
alpha = 1  # how much to weight time difference
beta = 1   # how much to weight rink distance

consts_difference_time = {(i, j, k): difference_time(i, j, k) for i in range(dim_i) for j in range(dim_j) for k in range(dim_k)}
consts_difference_rink = {(i, j, k): difference_rink(i, j, k) for i in range(dim_i) for j in range(dim_j) for k in range(dim_k)}
objective = pulp.lpSum( 
    [alpha * v * consts_difference_time[k] + 
    beta * v * consts_difference_rink[k] for k, v in x.items()] 
    )
prob += objective


# ========== Solve optimization =================
prob.writeLP("Scheduling.lp")
prob.solve()


# ========== Print out solution ================
num_games = 0
for v in prob.variables():
    if v.varValue == 1:
        print_solution(v.name)
        num_games += 1

print('Total num games: ', num_games)