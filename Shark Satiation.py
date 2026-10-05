# A program implementing a Wa-Tor Simulation with Red & Blue visuals,
# live header labels, and Objective 5 (Shark Satiation).

import glob
import os
import shutil
import sys
from pathlib import Path
from random import randint, shuffle
import imageio.v2 as io
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# -------------------------------------------------------------
# Simulation Parameters
# -------------------------------------------------------------
breed_time = 2      # Steps before a fish duplicates
energy_gain = 4     # Energy added to shark upon eating
breed_energy = 10   # Stored energy needed for shark reproduction

# --- OBJECTIVE 5 EXTENSION: Shark Satiation Level ---
# A shark will only eat if current energy <= satiation_energy
satiation_energy = 15

dims = [150, 200]   # Simulation grid dimensions [rows, columns]
initial_fish = 100
initial_sharks = 80
steps = 500         # Maximum duration of the simulation
basicSetup = True # True = random distribution; False = circular grouping
scale_factor = 4    # Sharp pixel upscale factor

# Index lists for randomized grid updates
ilist = list(range(dims[0]))
jlist = list(range(dims[1]))


# -------------------------------------------------------------
# Spatial & Set Helpers
# -------------------------------------------------------------
def generate_adjacent_indices(r, c):
    """Returns 4-neighbor toroidal wrap-around coordinates."""
    return [
        [r, (c + 1) % dims[1]],
        [r, (c - 1) % dims[1]],
        [(r + 1) % dims[0], c],
        [(r - 1) % dims[0], c],
    ]


def remove_occupied(locations):
    return [loc[0] for loc in locations if loc[1] == 0]


def find_fish_occupied(locations):
    return [loc[0] for loc in locations if loc[1] > 0]


def nest_intersection(l1, l2):
    return list(map(list, set(map(tuple, l1)) & set(map(tuple, l2))))


def nest_union(l1, l2):
    return list(map(list, set(map(tuple, l1)) | set(map(tuple, l2))))


# -------------------------------------------------------------
# Frame Renderer: Classic Red/Blue Grid + Partner's Banner
# -------------------------------------------------------------
def render_red_blue_frame_with_banner(game_array, current_step, f_count, s_count, scale=4):
    """
    Renders the classic bwr palette:
      - Fish  (> 0): Blue   [0, 60, 255]
      - Sharks (< 0): Red    [230, 20, 20]
      - Water  (==0): White  [255, 255, 255]
    And attaches a header banner displaying step and population counts.
    """
    h, w = game_array.shape

    # 1. Base grid RGB array (matching classic 'bwr' colormap)
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:] = [255, 255, 255]               # White Water / Empty
    rgb[game_array > 0] = [0, 60, 255]     # Blue Fish
    rgb[game_array < 0] = [230, 20, 20]    # Red Sharks

    # Upscale cleanly using nearest neighbor (crisp pixels)
    img_grid = Image.fromarray(rgb)
    img_scaled = img_grid.resize((w * scale, h * scale), resample=Image.Resampling.NEAREST)

    # 2. Add Top Header Banner (Partner's labeling style)
    banner_height = 42
    total_w = w * scale
    total_h = (h * scale) + banner_height

    # Slate gray header bar for contrast
    full_frame = Image.new("RGB", (total_w, total_h), color=(30, 35, 45))
    full_frame.paste(img_scaled, (0, banner_height))

    # Draw header text
    draw = ImageDraw.Draw(full_frame)
    try:
        font = ImageFont.load_default(size=16)
    except TypeError:
        font = ImageFont.load_default()

    label_text = (
        f"Wa-Tor Simulation  |  Step: {current_step:3d}  |  "
        f"Fish (Blue): {f_count:5d}  |  Sharks (Red): {s_count:5d}  |  SatLimit: {satiation_energy}"
    )

    draw.text((16, 12), label_text, fill=(255, 255, 255), font=font)

    return np.array(full_frame)


# -------------------------------------------------------------
# Main Simulation Step Logic (With Satiation)
# -------------------------------------------------------------
def step_game(old_array):
    global ilist, jlist
    new_array = np.zeros((dims[0], dims[1]), dtype=int)
    shuffle(ilist)

    for i in ilist:
        shuffle(jlist)
        for j in jlist:
            if old_array[i][j] != 0:
                old_locs = []
                new_locs = []
                for adj in generate_adjacent_indices(i, j):
                    old_locs.append([adj, old_array[adj[0]][adj[1]]])
                    new_locs.append([adj, new_array[adj[0]][adj[1]]])

                # --- FISH BEHAVIOR ---
                if old_array[i][j] > 0:
                    open_old = remove_occupied(old_locs)
                    open_new = remove_occupied(new_locs)
                    available = nest_intersection(open_old, open_new)

                    if available:
                        dest = available[randint(0, len(available) - 1)]
                        if old_array[i][j] > breed_time:
                            new_array[dest[0]][dest[1]] = 1
                            new_array[i][j] = 1
                        else:
                            new_array[dest[0]][dest[1]] = old_array[i][j] + 1
                    else:
                        new_array[i][j] = old_array[i][j]
                    old_array[i][j] = 0

                # --- SHARK BEHAVIOR ---
                else:
                    save_old = old_locs
                    save_new = new_locs
                    fish_old = find_fish_occupied(old_locs)
                    fish_new = find_fish_occupied(new_locs)
                    available_fish = nest_union(fish_old, fish_new)

                    current_energy = -old_array[i][j]

                    # OBJECTIVE 5: Only hunt if fish nearby AND shark energy <= satiation threshold
                    if available_fish and (current_energy <= satiation_energy):
                        dest = available_fish[randint(0, len(available_fish) - 1)]
                        shark_energy = old_array[i][j] - energy_gain

                        if shark_energy < -breed_energy:
                            half_e = int(round(shark_energy / 2))
                            new_array[dest[0]][dest[1]] = half_e
                            new_array[i][j] = shark_energy - half_e
                        else:
                            new_array[dest[0]][dest[1]] = shark_energy

                        if old_array[dest[0]][dest[1]] > 0:
                            old_array[dest[0]][dest[1]] = 0

                    # Satiated OR no fish available: move into open water or lose energy
                    else:
                        empty_old = remove_occupied(save_old)
                        empty_new = remove_occupied(save_new)
                        available_empty = nest_intersection(empty_old, empty_new)

                        if available_empty:
                            dest = available_empty[randint(0, len(available_empty) - 1)]
                            if old_array[i][j] < -breed_energy:
                                half_e = int(round(old_array[i][j] / 2))
                                new_array[dest[0]][dest[1]] = half_e
                                new_array[i][j] = old_array[i][j] - half_e
                            else:
                                new_array[dest[0]][dest[1]] = old_array[i][j] + 1
                        else:
                            new_array[i][j] = old_array[i][j] + 1

                    old_array[i][j] = 0

    return new_array


# -------------------------------------------------------------
# Population Setup
# -------------------------------------------------------------
game_array = np.zeros((dims[0], dims[1]), dtype=int)

if basicSetup:
    for _ in range(initial_fish):
        r, c = randint(0, dims[0] - 1), randint(0, dims[1] - 1)
        while game_array[r][c] != 0:
            r, c = randint(0, dims[0] - 1), randint(0, dims[1] - 1)
        game_array[r][c] = randint(1, breed_time)

    for _ in range(initial_sharks):
        r, c = randint(0, dims[0] - 1), randint(0, dims[1] - 1)
        while game_array[r][c] != 0:
            r, c = randint(0, dims[0] - 1), randint(0, dims[1] - 1)
        game_array[r][c] = randint(-breed_energy, -1)
else:
    for r in range(dims[0]):
        for c in range(dims[1]):
            d_sq = (r - dims[0] / 2) ** 2 + (c - dims[1] / 2) ** 2
            if d_sq < initial_sharks / np.pi:
                game_array[r][c] = randint(-breed_energy, -1)
            elif d_sq < (initial_sharks + initial_fish) / np.pi:
                game_array[r][c] = randint(1, breed_time)


# -------------------------------------------------------------
# Simulation Loop & In-Memory Frame Generation
# -------------------------------------------------------------
fishes = [initial_fish]
sharks = [initial_sharks]
frames = [render_red_blue_frame_with_banner(game_array, 0, initial_fish, initial_sharks, scale=scale_factor)]

print("Playing Wa-Tor simulation...")
actual_steps = steps

for k in range(1, steps + 1):
    game_array = step_game(game_array)

    fish_pop = int(np.sum(game_array > 0))
    shark_pop = int(np.sum(game_array < 0))
    fishes.append(fish_pop)
    sharks.append(shark_pop)

    frames.append(render_red_blue_frame_with_banner(game_array, k, fish_pop, shark_pop, scale=scale_factor))

    if k % 10 == 0 or k == steps:
        sys.stdout.write(f"\rProgress: {k:3d}/{steps} steps | Fish: {fish_pop:5d} | Sharks: {shark_pop:5d}")
        sys.stdout.flush()

    if fish_pop == 0 or shark_pop == 0 or (fish_pop + shark_pop >= dims[0] * dims[1]):
        print("\nEarly termination: Population reached extinction or saturation.")
        actual_steps = k
        break

# Resolve directory safely in Windows
try:
    save_dir = Path(__file__).resolve().parent
except NameError:
    save_dir = Path.cwd()

# Encode GIF using an alphanumeric safe filename
gif_filename = f"SnFanimation_{dims[1]}x{dims[0]}_{breed_time}_{energy_gain}_{breed_energy}_{initial_sharks}_{initial_fish}_{actual_steps}_sat{satiation_energy}.gif"
gif_full_path = os.path.join(str(save_dir), gif_filename)

print("\nEncoding Red & Blue GIF animation with banner labels...")
io.mimsave(gif_full_path, frames, fps=20, subrectangles=True)
print(f"GIF saved successfully: {gif_full_path}")


# -------------------------------------------------------------
# Population Plots
# -------------------------------------------------------------
fig, axs = plt.subplots(2, 1, figsize=(8, 8))
fig.suptitle(f"Wa-Tor Populations (Satiation Limit = {satiation_energy})")

# 1. Population vs Time
axs[0].plot(range(actual_steps + 1), fishes, label="fish", color="blue")
axs[0].plot(range(actual_steps + 1), sharks, label="sharks", color="red")
axs[0].legend()
axs[0].set(xlabel="Step", ylabel="Population")
axs[0].grid(True, linestyle="--", alpha=0.5)

# 2. Phase-Plane Orbit
axs[1].plot(fishes, sharks, marker=".", markersize=3, color="purple", alpha=0.7)
axs[1].set(xlabel="Fish Population", ylabel="Shark Population")
axs[1].grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()

# Save PNG using sanitized path
png_filename = f"SnFplots_{dims[1]}x{dims[0]}_{breed_time}_{energy_gain}_{breed_energy}_{initial_sharks}_{initial_fish}_{actual_steps}_sat{satiation_energy}.png"
png_full_path = os.path.join(str(save_dir), png_filename)

plt.savefig(png_full_path, bbox_inches="tight")
plt.show()

print(f"Plots saved successfully: {png_full_path}")