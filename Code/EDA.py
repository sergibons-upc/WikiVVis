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
for path in ABpaths["clean_paths"].head(50):
    edges += [(path[i], path[i+1]) for i in range(len(path)-1)]

edgesDF = pd.DataFrame(edges, columns=["linkSource", "linkTarget"])

# Count appearances of each target
target_counts = edgesDF["linkTarget"].value_counts().reset_index()
target_counts.columns = ["linkTarget", "target_count"]

# Merge counts back into edgesDF
edgesDF = edgesDF.merge(target_counts, on="linkTarget", how="left")
for track in ABpaths["clean_paths"]:
    print(track)

import networkx as nx
from pyvis.network import Network

G = nx.from_pandas_edgelist(
    edgesDF,
    source='linkSource',
    target='linkTarget',
    create_using=nx.DiGraph()
)

net = Network(
    height='750px',
    width='100%',
    bgcolor='#222222',
    font_color='white',
    directed=True
)

net.from_nx(G)

net.set_options("""
{
  "physics": {
    "enabled": true,
    "solver": "barnesHut",
    "barnesHut": {
      "springConstant": 1.0,
      "springLength": 0,
      "gravitationalConstant": -80000
    },
    "damping": 0.4
  }
}
""")

net.get_node("Asteroid")["x"] = -1500
net.get_node("Asteroid")["y"] = 0
net.get_node("Asteroid")["fixed"] = True

net.get_node("Viking")["x"] = 1500
net.get_node("Viking")["y"] = 0
net.get_node("Viking")["fixed"] = True

net.write_html('AB_map.html')

print("Graph generated!")
