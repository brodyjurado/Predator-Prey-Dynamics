# A program implementing and measuring a Wa-Tor Simulation
# Includes a live visual display of the game

from matplotlib.pyplot import *
from numpy import *
from random import *
import sys
import glob
import shutil
import os
from pathlib import Path
import imageio.v2 as io


# Main parameters of the simulation
breed_time = 2
energy_gain = 4
breed_energy = 10


# Other simulation parameters
dims = [150, 200]
initial_fish = 2000
initial_sharks = 1000
steps = 500
basicSetup = True


# Create a list of the row indexes of the game array
ilist = []
for i in range(dims[0]):
    ilist.append(i)


# Create a list of the column indexes of the game array
jlist = []
for j in range(dims[1]):
    jlist.append(j)


# Function to generate a list of adjacent location indices
def generate_adjacent_indices(row_index, column_index):
    return [
        [row_index, (column_index + 1) % dims[1]],
        [row_index, (column_index - 1) % dims[1]],
        [(row_index + 1) % dims[0], column_index],
        [(row_index - 1) % dims[0], column_index]
    ]


# Function to determine available empty spaces to move into
def remove_occupied(locations):
    open_locations = []

    for k in range(4):
        if locations[k][1] == 0:
            open_locations.append(locations[k][0])

    return open_locations


# Function to determine if there are adjacent fish that a shark can feed on
def find_fish_occupied(locations):
    fish_locations = []

    for k in range(4):
        if locations[k][1] > 0:
            fish_locations.append(locations[k][0])

    return fish_locations


# Function to determine the common elements in two lists of lists
def nest_intersection(list1, list2):
    return list(map(list, set(map(tuple, list1)) & set(map(tuple, list2))))


# Function to combine all elements in two lists of lists
def nest_union(list1, list2):
    return list(map(list, set(map(tuple, list1)) | set(map(tuple, list2))))


# Main function of the simulation
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

                # Fish
                if 0 < old_array[i][j]:

                    old_locations = remove_occupied(old_locations)
                    new_locations = remove_occupied(new_locations)

                    available_locations = nest_intersection(
                        old_locations,
                        new_locations
                    )

                    if len(available_locations) != 0:

                        chosen_location = available_locations[
                            randint(0, len(available_locations) - 1)
                        ]

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

                # Shark
                else:

                    save_old_locations = old_locations
                    save_new_locations = new_locations

                    old_locations = find_fish_occupied(old_locations)
                    new_locations = find_fish_occupied(new_locations)

                    available_locations = nest_union(
                        old_locations,
                        new_locations
                    )

                    if len(available_locations) != 0:

                        chosen_location = available_locations[
                            randint(0, len(available_locations) - 1)
                        ]

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

                            chosen_location = available_locations[
                                randint(
                                    0,
                                    len(available_locations) - 1
                                )
                            ]

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


# Function to convert the game array into a format for visual display
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


# Initialize the game array
game_array = zeros(
    (dims[0], dims[1]),
    dtype=int
)


# Set up the initial fish and sharks
if basicSetup == True:

    # Populate the game with fish
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

    # Populate the game with sharks
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

    # Less random setup
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


# ==========================================================
# CREATE THE LIVE GAME DISPLAY
# ==========================================================

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


# ==========================================================
# RUN THE SIMULATION
# ==========================================================

fishes = [initial_fish]
sharks = [initial_sharks]

print("Playing game...")

prcnt = 0
k = 1

actual_steps = steps


while k <= steps:

    # Update the game
    game_array = step_game(game_array)

    # Count fish and sharks
    currcount = countsNf(game_array)

    fishes.append(currcount[1])
    sharks.append(currcount[0])

    # Update the live visual
    img_array = create_img_array(game_array)

    img.set_data(img_array)

    # Update the title
    ax.set_title(
        "Wa-Tor Simulation\n"
        + "Step: " + str(k)
        + "   Fish: " + str(currcount[1])
        + "   Sharks: " + str(currcount[0])
    )

    # Refresh the figure
    pause(0.01)

    # Display progress in the console
    if floor(k * 100 / steps) > prcnt:

        ppstr = str(prcnt) + '%'

        sys.stdout.write(
            '%s\r' % ppstr
        )

        sys.stdout.flush()

        prcnt += 1

    # Check if the simulation should continue
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


# ==========================================================
# CREATE POPULATION PLOTS
# ==========================================================

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