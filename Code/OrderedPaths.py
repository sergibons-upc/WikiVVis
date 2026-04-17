import pandas as pd
import networkx as nx
from pyvis.network import Network
from urllib.parse import unquote
from dataclasses import dataclass
from collections import Counter
from collections import deque
import random

@dataclass(unsafe_hash=True)
class WikiNode:
    name :str
    n_visits: int = 0
    shortest_path_length: int = 0
    n_children: int = 0 
    thickest_parent_t: int = 0  
    x_coords: int = 0

@dataclass(unsafe_hash=True)
class WikiEdge:
    nodeFrom:WikiNode
    nodeTo:WikiNode
    n_times_traversed:int = 0

@dataclass
class WikiTrack:
    track:list[WikiEdge]
    exact_repetitions:int = 0



# 1. Load and Clean Data
pathsFinishedDF = pd.read_csv('./data/paths_finished.tsv', sep='\t', comment='#', header=None)
paths = pathsFinishedDF.iloc[:, 3].str.split(';')

def clean_path(path):
    stack = []
    for node in path:
        if node == "<":
            if stack: stack.pop()
        else:
            stack.append(node)
    return stack

# Filter for Asteroid -> Viking tracks
ABpaths = pd.DataFrame()
ABpaths["paths"] = paths[(paths.str[0]=="Asteroid") & (paths.str[-1]=="Viking")]
ABpaths["clean_paths"] = ABpaths["paths"].apply(clean_path)
ABpaths["length"] = ABpaths["clean_paths"].apply(len)

# 2. Initialize Node Registry and Edge Registry
node_registry = {}  # name -> WikiNode object
edge_registry = {}  # (from, to) -> WikiEdge object
children_set_registry = {} # name -> set

def get_or_create_node(name):
    if name not in node_registry:
        node_registry[name] = WikiNode(name=name)
    return node_registry[name]

def get_or_create_as_parent(name):
    if name not in children_set_registry:
        children_set_registry[name] = []
    return children_set_registry[name]

def get_or_create_edge(n1, n2):
    edge_key = (n1.name, n2.name)
    if edge_key not in edge_registry:
        edge_registry[edge_key] = WikiEdge(nodeFrom=n1, nodeTo=n2)
    return edge_registry[edge_key]

# 3. Populate Nodes and Edges
wiki_tracks = []

# We iterate over the original 'paths' (with backspaces) and the cleaned paths
# To calculate n_visits and traverse edges correctly
PathData = ABpaths["clean_paths"][ABpaths["length"] <= 4]
for current_path in PathData:
    # Process track
    current_clean_edges = []
    for i in range(len(current_path) - 1):
        u = get_or_create_node(current_path[i])
        u.n_visits += 1
        v = get_or_create_node(current_path[i+1])
        pc = get_or_create_as_parent(current_path[i])
        pc.append(v.name)
        edge = get_or_create_edge(u, v)
        edge.n_times_traversed += 1
        current_clean_edges.append(edge)
    get_or_create_node(current_path[-1]).n_visits += 1
    get_or_create_as_parent(current_path[-1])


    # Create the WikiTrack object
    wiki_tracks.append(WikiTrack(
        track=current_clean_edges,
        exact_repetitions=0
    ))

track_sequences = [tuple(t.track) for t in wiki_tracks]
repetition_counts = Counter(track_sequences)
# Assign the repetition count to each WikiTrack
for node in node_registry:
    node_registry[node].n_children = len(set(children_set_registry[node]))

for wiki_track in wiki_tracks:
    sequence_key = tuple(wiki_track.track)
    wiki_track.exact_repetitions = repetition_counts[sequence_key] - 1


def calculate_shortest_paths_from_tracks(start_node_name, node_registry, wiki_tracks):
    # Reset lengths
    for node in node_registry.values():
        node.shortest_path_length = float('inf')
    
    if start_node_name not in node_registry:
        return

    # Build an adjacency list from the CLEAN tracks
    # This maps node name -> set of neighbor node objects
    adj = {name: set() for name in node_registry}
    for track in wiki_tracks:
        for edge in track.track:
            adj[edge.nodeFrom.name].add(edge.nodeTo)

    # BFS
    start_node = node_registry[start_node_name]
    start_node.shortest_path_length = 0
    queue = deque([start_node])
    
    while queue:
        current_node = queue.popleft()
        for neighbor in adj[current_node.name]:
            if neighbor.shortest_path_length == float('inf'):
                neighbor.shortest_path_length = current_node.shortest_path_length + 1
                queue.append(neighbor)


# --- Execution ---
calculate_shortest_paths_from_tracks("Asteroid", node_registry, wiki_tracks)

def assign_thickest_parents_t(node_registry, edge_registry):
    # Dictionary to track the max weight seen so far for each 'nodeTo'
    max_edge_weight = {name: -1 for name in node_registry}

    for (src, dst), edge in edge_registry.items():
        if edge.n_times_traversed > max_edge_weight[dst]:
            max_edge_weight[dst] = edge.n_times_traversed
            node_registry[dst].thickest_parent_t = edge.n_times_traversed

assign_thickest_parents_t(node_registry,edge_registry)

def calculate_level_sorted_x(node_registry, spacing=150):
    lvlList = {}

    # Group nodes by level
    for x in node_registry:
        lvlList.setdefault(node_registry[x].shortest_path_length, []).append(x)

    # Sort each level and assign x positions
    for level_nodes in lvlList.values():
        level_nodes.sort(key=lambda x: node_registry[x].thickest_parent_t, reverse=True)

        for i, node in enumerate(level_nodes):
            node_registry[node].x_coords = i * spacing

calculate_level_sorted_x(node_registry)

def visualize_incremental_tree(node_registry, wiki_tracks, filename="wiki_incremental.html"):
    net = Network(height="800px", width="100%", bgcolor="#1a1a1a", font_color="white", directed=True)
    


    for name, node in node_registry.items():
        # Level-based Y positioning
        y_pos = node.shortest_path_length * 400
        is_anchor = name in ["Asteroid", "Viking"]

        net.add_node(
            name, 
            label=name, 
            x=node.x_coords, 
            y=y_pos,
            fixed={'x': True, 'y': True},
            size= node.n_visits/4 + 7,
            color="#44ff5a" if is_anchor else "#4498ff",
            title = f"Visits: {node.n_visits}\nUnique Children: {node.n_children}\nThickest Parent: {node.thickest_parent_t}"
        )

    # Add edges based on traversal counts
    edge_counts = {}
    for track in wiki_tracks:
        for edge in track.track:
            pair = (edge.nodeFrom.name, edge.nodeTo.name)
            edge_counts[pair] = edge_counts.get(pair, 0) + 1

    for (src, dst), count in edge_counts.items():
        net.add_edge(src, dst, value=count, color="rgba(200, 200, 200, 0.4)")

    net.toggle_physics(False)
    net.show(filename, notebook=False)

# Re-run
visualize_incremental_tree(node_registry, wiki_tracks)