# hockey-league-scheduling
league scheduling with preferences.  
Uses [pulp](https://github.com/coin-or/pulp) linear programming api to find optimal match schedule given rink and time preferences.  

## Requirements
Needs `pandas` and `pulp` (both available from pip)  

## Inputs
Need to input team names, divisions, available rinks and times, and preferences as follows:  

### 1. Team names and divisions
A dataframe, but could just be two lists. Also likely will change because some teams can play out of their division?  
Need to also define the variable `num_games_per_team`.  
Example used for toy example:  
| Team Name | Division | 
|   -----   | ------   |
|     A     |    A     |
|     B     |    A     |
|     C     |    A     |
|     D     |    B     |
|     E     |    B     |
|     F     |    B     |

### 2. Rinks and available rink times 
A data frame with all available rink times. Each row will be assigned a unique match. So if a rink has a given time available every day, that needs to be repeated for each day.   
Start time should be in miliary time, without punctuation (I'm basically using it as an integer). Date and Duration columns aren't really used yet. **Note: the order in which the rink names matters. Rink Names should be in the same order as in the following dataframe**  
Should look like this:  
  
| Rink Name | Date | Start Time | Duration | 
| --------- | ---- | ---------- | -------- |
| R1 | 01/01/23 | 1600 | 120 |
| R1 | 01/02/23 | 1600 | 120 |
| R2 | 01/01/23 | 800 | 120 |
| etc | | | |

### 3. Rink Preferences
A datarame where each row has the preferences for a team. So there should be <num\_teams> rows and <num\_rinks> columns. Integer value in each cell indicates how the team ranks that rink. **Important: 1 means _most preferred_ and the highest integer mean _least preferred_. Also, the order of the teams (as rows) should match the order they were in the previous dataframe (ignoring duplicates). **  
Example:  
|   | Rink1 | Rink2 | Rink3 | ... |
|---|-------|-------|-------|-----|
| **A** |   1   |   4   |  3    |  5  | 
| **B** |   2   |   1   |  10   |  10 |
| **C** |   2   |   5   |   1   |  6  |
| **D** |   3   |   1   |   2   | 4   |
| etc | | | | |

### 4. Time Preferences
A dataframe simliar to Rink Preferences -- rows are per team, columns are per available time. I assumed here that they way you get this is from a google form with a radio-choice section, each labeled something like "2pm - 4pm".  So that's what the columns here are, noting that they denote a range (whereas the actualy available rink times have exact start times.) Those choices also need to be hardcoded somewhere -- so in addition to this table, you need to define that list. And same as before, *1 means _most preferred_, and the order of the teams matters (should match the others)*
Example:  
```
time_preference_choices = [   # Should change these to whatever's on the form...
    [0, 800], # midnight to 8am  # NOTE: Players should think of this as 0 to 7:59am
    [800, 1200],  # 8am to noon  # And this as 8am to 11:59am 
    [1200, 1600], # noon to 4pm 
    [1600, 2000],  # 4pm to 8pm
    [2000, 2400]  # 8pm to rest of the day
    ]
```

|   | [0, 800] | [800, 1200] | [1200, 1600] | ... |
|---|-------|-------|-------|-----|
| **A** |   1   |   4   |  3    |  5  | 
| **B** |   2   |   1   |  10   |  10 |
| **C** |   2   |   5   |   1   |  6  |
| **D** |   3   |   1   |   2   | 4   |
| etc | | | | |


### 5. Weights _alpha_ and _beta_
So since there are 2 types of preferences (rink and time), it's helpful to have constants that define how to weight each of them respectively in searching for an optimal solution. Since they're both on similar scales (or at least they both start at 1...), I just add the two preference values with weights:  
**alpha** x time-preference + **beta** x rink-preference   
So a possible match that gives the players their most preferred rink (1) and most preferred time (1) will have a score of 2. (And a possible match that gives everyone their least preferred rink (5) and least preferred time (5) will have a score of 10....) At the end, the matches with the lowest scores win out. By default both alpha and beta 1 (so generally equally-weighted).   

## How this works
Solves a linear optimization problem, where binary variables indicate a unique match: 
$$ X_{ijk} $$ 
represents a potential match where team _i_ and team _j_ play eachother at rink-time _k_. If in our solution, a given X_{ijk} == 1, that match exists (and if it's 0, it doesn't. )  
So there are num\_i x num\_j x num\_k possible variables like this. We define an equation\* that uses these variables (and set some constraints on them as well). This equation formalizes an optimization -- we're aiming to find combinations of these variables that minimize an objective function (basically the preference 'score'; see the Weights alpha and beta section above). The solution to this equation assigns some of them 1 and some of them 0. We use the pulp library to solve (default solver).  
