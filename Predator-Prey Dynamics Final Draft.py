#A program implementing and measuring a Wa-Tor Simulation (outputs to a "temp" folder)
#Also includes a live visual display of the simulation model and simulated ocean currents

from matplotlib.pyplot import * #Library needed to plot results
from numpy import * #Library needed for some numerical functions
from random import * #Library needed to generate random numbers for movement
import sys #Library needed to read/write files/folders and other system operations
import glob #Library needed to read/write files/folders and other system operations
import shutil #Library needed to read/write files/folders and other system operations
import os #Library needed to read/write files/folders and other system operations
from pathlib import Path #Library to determine the file paths to images
import imageio.v2 as io #Library for converting a collection of image files to a gif


#Main parameters of the simulation
breed_time = 2
energy_gain = 4
breed_energy = 12

# Controls how strongly entities drift with the pcean current (0.0 = isotropic, anything >1.0 = strong drift)
current_strength = 1.5

# A shark will only eat if current energy <= satiation_energy
satiation_energy = 3.0

#Other simulation parameters
dims = [150, 200]
initial_fish = 2000
initial_sharks = 1000
steps = 500
basicSetup = True


# Create a list of the row indexes of the game array
ilist = []
for i in range(dims[0]):
    ilist.append(i)


#Create a list of the column indexes of the game array
jlist = []
for j in range(dims[1]):
    jlist.append(j)


#Function to generate a list of adjacent location indices
def generate_adjacent_indices(row_index, column_index):
    return [
        [row_index, (column_index + 1) % dims[1]],
        [row_index, (column_index - 1) % dims[1]],
        [(row_index + 1) % dims[0], column_index],
        [(row_index - 1) % dims[0], column_index]
    ]


#Function to determine available empty spaces to move into
def remove_occupied(locations):
    open_locations = []

    for k in range(4):
        if locations[k][1] == 0:
            open_locations.append(locations[k][0])

    return open_locations


#Function to determine if there are adjacent fish that a shark can feed on
def find_fish_occupied(locations):
    fish_locations = []

    for k in range(4):
        if locations[k][1] > 0:
            fish_locations.append(locations[k][0])

    return fish_locations


#Function to determine the common elements in two lists of lists
def nest_intersection(list1, list2):
    return list(map(list, set(map(tuple, list1)) & set(map(tuple, list2))))


# Function to combine all elements in two lists of lists
def nest_union(list1, list2):
    return list(map(list, set(map(tuple, list1)) | set(map(tuple, list2))))


#Ocean current logic

def get_ocean_current(row, col):
    """
    Returns velocity vector (u, v) representing ocean current at grid location (row, col).
    u: horizontal velocity (positive = right/east)
    v: vertical velocity (positive = down/south)
    """
    cy, cx = dims[0] / 2.0, dims[1] / 2.0
    dy = row - cy
    dx = col - cx
    
    #Rotational vortex centered in the grid
    u = -dy * 0.02
    v =  dx * 0.02
    
    return u, v


def choose_current_biased_location(current_pos, candidate_locations):
    """
    This chooses a target location from candidate_locations weighted by alignment
    with the local ocean current vector
    """
    if not candidate_locations:
        return None

    if current_strength == 0.0:
        return candidate_locations[randint(0, len(candidate_locations) - 1)]

    row_curr, col_curr = current_pos
    u, v = get_ocean_current(row_curr, col_curr)

    weights = []
    for cand in candidate_locations:
        row_cand, col_cand = cand

        #Wrap-around distance logic for the torus grid
        d_col = (col_cand - col_curr)
        if d_col > dims[1] / 2: d_col -= dims[1]
        elif d_col < -dims[1] / 2: d_col += dims[1]

        d_row = (row_cand - row_curr)
        if d_row > dims[0] / 2: d_row -= dims[0]
        elif d_row < -dims[0] / 2: d_row += dims[0]

        #Dot product of movement vector with vector field
        dot_prod = d_col * u + d_row * v
        
        weight = exp(current_strength * dot_prod)
        weights.append(weight)

    total_w = sum(weights)
    norm_weights = [w / total_w for w in weights]

    r = random()
    cum_sum = 0.0
    for idx, w in enumerate(norm_weights):
        cum_sum += w
        if r <= cum_sum:
            return candidate_locations[idx]

    return candidate_locations[-1]


#Main function
def step_game(old_array):

    global ilist, jlist

    new_array = zeros((dims[0], dims[1]), dtype=int)

    shuffle(ilist)

    for i in ilist:

        shuffle(jlist)

        for j in jlist:

            if old_array[i][j] != 0:

                old_locations = []
                new_locations = []

                for indices in generate_adjacent_indices(i, j):

                    old_locations.append(
                        [indices, old_array[indices[0]][indices[1]]]
                    )

                    new_locations.append(
                        [indices, new_array[indices[0]][indices[1]]]
                    )

                #Fish parameters
                if 0 < old_array[i][j]:

                    old_locations = remove_occupied(old_locations)
                    new_locations = remove_occupied(new_locations)

                    available_locations = nest_intersection(
                        old_locations,
                        new_locations
                    )

                    if len(available_locations) != 0:

                        #Current-biased selection replacing randint
                        chosen_location = choose_current_biased_location([i, j], available_locations)

                        if breed_time < old_array[i][j]:

                            new_array[
                                chosen_location[0]
                            ][
                                chosen_location[1]
                            ] = 1

                            new_array[i][j] = 1

                        else:

                            new_array[
                                chosen_location[0]
                            ][
                                chosen_location[1]
                            ] = old_array[i][j] + 1

                    else:

                        new_array[i][j] = old_array[i][j]

                    old_array[i][j] = 0

     #Shark stuff
                else:

                    save_old_locations = old_locations
                    save_new_locations = new_locations

                    #Convert negative array energy to positive current energy for satiation
                    current_energy = -old_array[i][j]

                    #Check for fish ONLY if shark is hungry (where energy <= satiation_energy)
                    if current_energy <= satiation_energy:
                        old_locations = find_fish_occupied(old_locations)
                        new_locations = find_fish_occupied(new_locations)
                    else:
                        #Shark is full, do not search for any more fish
                        old_locations = []
                        new_locations = []
                    
                    available_locations = nest_union(
                        old_locations,
                        new_locations
                    )

                    if len(available_locations) != 0:

                        #Current-biased selection replacing randint
                        chosen_location = choose_current_biased_location([i, j], available_locations)

                        if -breed_energy > old_array[i][j] - energy_gain:

                            new_array[
                                chosen_location[0]
                            ][
                                chosen_location[1]
                            ] = round(
                                (old_array[i][j] - energy_gain) / 2
                            )

                            new_array[i][j] = (
                                old_array[i][j]
                                - energy_gain
                                - round(
                                    (old_array[i][j] - energy_gain) / 2
                                )
                            )

                        else:

                            new_array[
                                chosen_location[0]
                            ][
                                chosen_location[1]
                            ] = old_array[i][j] - energy_gain

                        if old_array[
                            chosen_location[0]
                        ][
                            chosen_location[1]
                        ] > 0:

                            old_array[
                                chosen_location[0]
                            ][
                                chosen_location[1]
                            ] = 0

                    else:

                        old_locations = remove_occupied(
                            save_old_locations
                        )

                        new_locations = remove_occupied(
                            save_new_locations
                        )

                        available_locations = nest_intersection(
                            old_locations,
                            new_locations
                        )

                        if len(available_locations) != 0:

                            #Current-biased selection replacing randint
                            chosen_location = choose_current_biased_location([i, j], available_locations)

                            if -breed_energy > old_array[i][j]:

                                new_array[
                                    chosen_location[0]
                                ][
                                    chosen_location[1]
                                ] = round(
                                    old_array[i][j] / 2
                                )

                                new_array[i][j] = (
                                    old_array[i][j]
                                    - round(old_array[i][j] / 2)
                                )

                            else:

                                new_array[
                                    chosen_location[0]
                                ][
                                    chosen_location[1]
                                ] = old_array[i][j] + 1

                        else:

                            new_array[i][j] = old_array[i][j] + 1

                old_array[i][j] = 0

    return new_array


# Function that counts the total number of fish and sharks
def countsNf(game_array):

    fish_count = 0
    shark_count = 0

    for i in range(dims[0]):

        for j in range(dims[1]):

            if game_array[i][j] > 0:
                fish_count += 1

            if game_array[i][j] < 0:
                shark_count += 1

    return [shark_count, fish_count]


#Function to convert the game array into a visual display
def create_img_array(game_array):

    img_array = zeros(
        (dims[0], dims[1]),
        dtype=int
    )

    for i in range(dims[0]):

        for j in range(dims[1]):

            if game_array[i][j] > 0:
                img_array[i][j] = 1

            if game_array[i][j] < 0:
                img_array[i][j] = -1

    return img_array


#Initializes the game array
game_array = zeros(
    (dims[0], dims[1]),
    dtype=int
)


#Initial fish and shark setup
if basicSetup == True:

    #Populates the simulation with fish
    for k in range(initial_fish):

        i = randint(0, dims[0] - 1)
        j = randint(0, dims[1] - 1)

        while game_array[i][j] != 0:

            i = randint(0, dims[0] - 1)
            j = randint(0, dims[1] - 1)

        game_array[i][j] = randint(
            1,
            breed_time
        )

    #Populates the simulation with sharks
    for k in range(initial_sharks):

        i = randint(0, dims[0] - 1)
        j = randint(0, dims[1] - 1)

        while game_array[i][j] != 0:

            i = randint(0, dims[0] - 1)
            j = randint(0, dims[1] - 1)

        game_array[i][j] = randint(
            -breed_energy,
            -1
        )


else:

    #Less random setup
    for i in range(dims[0]):

        for j in range(dims[1]):

            if (
                (i - dims[0] / 2) ** 2
                + (j - dims[1] / 2) ** 2
                < initial_sharks / pi
            ):

                game_array[i][j] = randint(
                    -breed_energy,
                    -1
                )

            elif (
                (i - dims[0] / 2) ** 2
                + (j - dims[1] / 2) ** 2
                < (initial_sharks + initial_fish) / pi
            ):

                game_array[i][j] = randint(
                    1,
                    breed_time
                )

#The following section is for the ocean current vector field
#Coordinate grid
step_size = 8  #Shows an arrow every 8 grid cells
y_coords = arange(0, dims[0], step_size)
x_coords = arange(0, dims[1], step_size)
X, Y = meshgrid(x_coords, y_coords)

#For calculating velocity components (u, v) at each grid point
U = zeros(X.shape)
V = zeros(Y.shape)

for r in range(X.shape[0]):
    for c in range(X.shape[1]):
        u_val, v_val = get_ocean_current(Y[r, c], X[r, c])
        U[r, c] = u_val
        V[r, c] = v_val

#Creates vector field plot
current_fig, current_ax = subplots(figsize=(8, 6))
quiver_plot = current_ax.quiver(
    X, Y, U, V, 
    sqrt(U**2 + V**2),  #Color arrows by current magnitude
    cmap='viridis',
    angles='xy', 
    scale_units='xy', 
    scale=0.1
)

current_ax.set_xlim(0, dims[1])
current_ax.set_ylim(dims[0], 0)  #Inverts Y-axis to match array indexing (where row 0 is at top)
current_ax.set_title("Ocean Current Vector Field")
current_ax.set_xlabel("X (Columns)")
current_ax.set_ylabel("Y (Rows)")
colorbar(quiver_plot, ax=current_ax, label="Current Speed")

show(block=False)

#For the live display

img_array = create_img_array(game_array)

arrayfig = figure(
    figsize=(10, 7)
)

ax = arrayfig.subplots()

ax.set_axis_off()

img = ax.imshow(
    img_array,
    cmap='bwr',
    vmin=-1,
    vmax=1
)

ax.set_title(
    "Wa-Tor Simulation\n"
    + "Step: 0"
    + "   Fish: " + str(initial_fish)
    + "   Sharks: " + str(initial_sharks)
)

show(block=False)


#This is where the simulation runs

fishes = [initial_fish]
sharks = [initial_sharks]

print("Playing game...")

prcnt = 0
k = 1

actual_steps = steps


while k <= steps:

    #Updates the simulation model
    game_array = step_game(game_array)

    #Counts fish and sharks
    currcount = countsNf(game_array)

    fishes.append(currcount[1])
    sharks.append(currcount[0])

    #Live visual update
    img_array = create_img_array(game_array)

    img.set_data(img_array)

    #Title update for Wa-Tor Simulation
    ax.set_title(
        "Wa-Tor Simulation\n"
        + "Step: " + str(k)
        + "   Fish: " + str(currcount[1])
        + "   Sharks: " + str(currcount[0])
    )

    #Refresh the figure
    pause(0.01)

    #Display progress in the console
    if floor(k * 100 / steps) > prcnt:

        ppstr = str(prcnt) + '%'

        sys.stdout.write(
            '%s\r' % ppstr
        )

        sys.stdout.flush()

        prcnt += 1

    #Check if the simulation should continue
    if (
        0 < currcount[0] + currcount[1]
        < dims[0] * dims[1]
    ):

        k += 1

    else:

        print('Early termination!')

        actual_steps = k

        k = steps + 1


sys.stdout.write('%s\r' % '100%')
sys.stdout.flush()

print()
print("Simulation complete!")


#These are the population plots

fig, axs = subplots(2)

fig.suptitle('Wa-Tor Populations')


axs[0].plot(
    range(actual_steps + 1),
    fishes,
    label='fish'
)

axs[0].plot(
    range(actual_steps + 1),
    sharks,
    label='sharks'
)

axs[0].legend()

axs[0].set(
    xlabel="Step",
    ylabel="Population"
)


axs[1].plot(
    take(
        fishes,
        range(actual_steps + 1)
    ),
    take(
        sharks,
        range(actual_steps + 1)
    ),
    marker='.'
)

axs[1].set(
    xlabel="Fish Population",
    ylabel="Shark Population"
)


show()