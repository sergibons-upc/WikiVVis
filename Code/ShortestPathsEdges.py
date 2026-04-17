import pandas as pd
import networkx as nx
from pyvis.network import Network
from urllib.parse import unquote

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
ABpaths["clean_paths"] = paths[(paths.str[0]=="Asteroid") & (paths.str[-1]=="Viking")].apply(clean_path)
ABpaths["length"] = ABpaths["clean_paths"].apply(len)

# 2. Filter for Shortest Paths Only
min_length = ABpaths["length"].min()
shortest_AB_paths = ABpaths[ABpaths["length"] == min_length]

# 3. Count Edge Frequencies
all_edges = []
for path in shortest_AB_paths["clean_paths"]:
    # Create list of (source, target) tuples
    all_edges += [(path[i], path[i+1]) for i in range(len(path)-1)]

# Count identical paths
path_counts = shortest_AB_paths["clean_paths"].apply(tuple).value_counts()

# Convert to dict: {path: weight}
path_weights = path_counts.to_dict()

def center_order_paths(paths):
    paths_sorted = sorted(paths, key=lambda p: path_weights[p], reverse=True)
    
    result = [None] * len(paths_sorted)
    mid = len(paths_sorted) // 2
    
    left = mid - 1
    right = mid + 1
    
    result[mid] = paths_sorted[0]
    
    for i, path in enumerate(paths_sorted[1:], start=1):
        if i % 2:
            result[left] = path
            left -= 1
        else:
            result[right] = path
            right += 1
            
    return result

ordered_paths = center_order_paths(list(path_weights.keys()))

path_y_positions = {}
gap_y = 120

for i, path in enumerate(ordered_paths):
    y = (i - len(ordered_paths)/2) * gap_y
    path_y_positions[path] = y

node_positions = {}
node_weights = {}

for path, weight in path_weights.items():
    y = path_y_positions[path]
    
    for lvl, node in enumerate(path):
        key = (node, lvl)
        
        node_positions[key] = node_positions.get(key, 0) + y * weight
        node_weights[key] = node_weights.get(key, 0) + weight
# Normalize
for node in node_positions:
    node_positions[node] /= node_weights[node]



# Convert to a dictionary of {(src, target): count}
edge_counts = pd.Series(all_edges).value_counts().to_dict()

# 4. Build the Graph
G = nx.DiGraph()
for (src, dst), weight in edge_counts.items():
    G.add_edge(src, dst, weight=weight)

# 5. Setup PyVis
net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", directed=True)
net.from_nx(G)

# 6. Calculate Levels and Apply Styling
start_node = "Asteroid"
target_node = "Viking"
levels = nx.single_source_shortest_path_length(G, start_node)

# Set "Viking" level to the very end
max_level_others = max([lvl for node, lvl in levels.items() if node != target_node], default=0)
viking_level = max_level_others + 1

level_gap_x = 300

for node in net.nodes:
    node_id = node['id']
    
    lvl = viking_level if node_id == target_node else levels.get(node_id, 0)
    
    y = node_positions.get((node_id, lvl), 0)
    
    node['x'] = lvl * level_gap_x
    node['y'] = y
    node['fixed'] = True

    node['size'] = 15
    node['color'] = '#ff4d4d' if node_id == target_node else '#97c2fc'
# Apply edge thickness (value) and sort to the center
for edge in net.edges:
    src, dst = edge['from'], edge['to']
    weight = edge_counts.get((src, dst), 1)
    edge['value'] = weight
    # Change color slightly for thicker edges to make them stand out
    edge['color'] = {
        'color': '#848484',
        'highlight': '#ffffff',
        'hover': '#ffffff',
        'inherit': False
    }

# 7. Configure Hierarchical Layout
net.set_options("""
{
  "edges": {
    "scaling": {
      "min": 1,
      "max": 15,
      "label": { "enabled": false }
    },
    "smooth": {
      "type": "cubicBezier",
      "forceDirection": "horizontal",
      "roundness": 0.5
    }
  },
  "physics": {
    "enabled": true
  }
}
""")

net.write_html("AB_ThickEdges.html")
print(f"Graph generated with {len(shortest_AB_paths)} paths of length {min_length}.")