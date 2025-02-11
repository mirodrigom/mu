import matplotlib.pyplot as plt
import json

def visualize_map(map_data, map_name):
    """Visualize the map using matplotlib."""
    obstacles = list(map_data['obstacles'])
    free_spaces = list(map_data['free_spaces'])
    
    # Plot obstacles
    if obstacles:
        ox, oy = zip(*obstacles)
        plt.scatter(ox, oy, c='red', label='Obstacles')
    
    # Plot free spaces
    if free_spaces:
        fx, fy = zip(*free_spaces)
        plt.scatter(fx, fy, c='green', label='Free Spaces')
    
    plt.legend()
    plt.title(f"Map of {map_name}")
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.grid(True)
    plt.show()

def load_map_data(file_path):
    """Load map data from a file."""
    map_data = {}
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            # Convert to lists instead of sets to preserve duplicates
            map_data['obstacles'] = [tuple(coord) for coord in data['obstacles']]
            map_data['free_spaces'] = [tuple(coord) for coord in data['free_spaces']]
    except FileNotFoundError:
        print("No existing map data found.")
    return map_data

# Load and visualize the map
map_data = load_map_data(file_path="./json/maps/dungeon3.json")
print(map_data)
visualize_map(map_data=map_data, map_name="lorencia")
