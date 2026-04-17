import pandas as pd
import networkx as nx
from dataclasses import dataclass
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st
from networkx.drawing.nx_pydot import graphviz_layout
from streamlit_echarts import st_echarts


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

edges = {}
for track in ABpaths["clean_paths"][:10]:
    for i in range(len(track)-1):
        key = (str(track[i]),str(track[i+1]))
        if key in edges:
            edges[key] += 1
        else:
            edges[key] = 1
G = nx.DiGraph()
G.graph["graph"] = {"rankdir": "LR"} 
for (u, v), w in edges.items():
    G.add_edge(u, v, weight=w)

edge_widths = [G[u][v]["weight"] for u, v in G.edges()]
plt.figure(figsize=(6, 4))
pos = graphviz_layout(G, prog="dot")



nx.draw(
    G,
    pos,
    with_labels=True,
    width=edge_widths,
    #node_size=node_sizes,
    node_color="skyblue"
)

st.pyplot(plt)