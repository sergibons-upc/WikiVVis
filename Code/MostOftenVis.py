import pandas as pd
import networkx as nx
from pyvis.network import Network
from urllib.parse import unquote


articlesDF = pd.read_csv('./data/articles.tsv', sep='\t', comment='#', header=None)
articlesDF = articlesDF.map(unquote)
linksDF = pd.read_csv("./data/links.tsv", sep='\t', comment='#', names=['linkSource', 'linkTarget'])
linksDF = linksDF.map(unquote)
pathsFinishedDF = pd.read_csv("./data/paths_finished.tsv", sep='\t', comment='#', header=None)
#pathsFinishedDF = pathsFinishedDF.map(unquote)
pathsUnfinishedDF = pd.read_csv("./data/paths_unfinished.tsv", sep='\t', comment='#', header=None)
#pathsUnfinishedDF = pathsUnfinishedDF.map(unquote)

paths = pathsFinishedDF.iloc[:, 3].str.split(';')

pathsFinishedDF['start_article'] = paths.str[0]
pathsFinishedDF['end_article'] = paths.str[-1]

common_tracks = pathsFinishedDF.groupby(['start_article', 'end_article']).size().reset_index(name='track_count')

common_tracks = common_tracks.sort_values(by='track_count', ascending=False)

AsteroidPaths = pd.DataFrame()
ABpaths = pd.DataFrame()
AsteroidPaths["paths"] = paths[paths.str[0]=="Asteroid"]
#Backspace navigation, may be useful to see where.
def clean_path(path):
    stack = []
    for node in path:
        if node == "<":
            if stack:
                stack.pop()
        else:
            stack.append(node)
    return stack


ABpaths["ABpaths"] = AsteroidPaths[paths.str[-1]=="Viking"]
ABpaths["clean_paths"] = ABpaths["ABpaths"].apply(clean_path)
ABpaths["length"] = ABpaths["ABpaths"].apply(len)
ABpaths = ABpaths.sort_values(by="length", ascending=True)





#Asteroid Viking
#Brain Telephone
edges = []
for path in ABpaths["clean_paths"].head(100):
    edges += [(path[i], path[i+1]) for i in range(len(path)-1)]

edgesDF = pd.DataFrame(edges, columns=["linkSource", "linkTarget"])

# Count appearances of each target
target_counts = edgesDF["linkTarget"].value_counts().reset_index()
target_counts.columns = ["linkTarget", "target_count"]

# Merge counts back into edgesDF
edgesDF = edgesDF.merge(target_counts, on="linkTarget", how="left")
for track in ABpaths["clean_paths"]:
    print(track)
from pyvis.network import Network
import pandas as pd
import networkx as nx

# Build directed graph
G = nx.from_pandas_edgelist(
    edgesDF,
    source="linkSource",
    target="linkTarget",
    create_using=nx.DiGraph()
)

# Create PyVis network
net = Network(
    height="750px",
    width="100%",
    bgcolor="#222222",
    font_color="white",
    directed=True
)
# 1. Calculate shortest path distances for all nodes
start_node = "Asteroid"
target_node = "Viking"
levels = nx.single_source_shortest_path_length(G, start_node)

# 2. Determine the furthest level reached by any node (excluding Viking)
# This ensures Viking is always in its own column on the right
if levels:
    max_level_others = max([lvl for node, lvl in levels.items() if node != target_node], default=0)
    viking_level = max_level_others + 1
else:
    viking_level = 1

# 3. Apply levels to the PyVis network
for node in net.nodes:
    node_id = node['id']
    if node_id == target_node:
        node['level'] = viking_level
        node['color'] = '#ff4d4d' # Optional: Highlight the target in red
    else:
        # Default to 0 if node is unreachable for some reason
        node['level'] = levels.get(node_id, 0)
# 2. Create PyVis network
net = Network(
    height="750px",
    width="100%",
    bgcolor="#222222",
    font_color="white",
    directed=True
)

net.from_nx(G)

# 3. Manually assign levels to the PyVis nodes
for node in net.nodes:
    node_id = node['id']
    # If a node isn't reachable from the start, we put it at level 0 or skip
    node['level'] = levels.get(node_id, 0) 

# 4. Update options to use 'hubsize' or 'directed' and block manual level overrides
net.set_options("""
{
  "layout": {
    "hierarchical": {
      "enabled": true,
      "direction": "LR",
      "sortMethod": "directed",
      "levelSeparation": 200,
      "nodeSpacing": 100,
      "treeSpacing": 200,
      "blockShifting": false,
      "edgeMinimization": true,
      "parentCentralization": true
    }
  },
  "physics": {
    "enabled": false
  }
}
""")

net.write_html("AB_map_hierarchical.html")
print("Hierarchical tree with BFS levels saved!")