import pandas as pd
from dataclasses import dataclass
from streamlit_echarts import st_echarts
from streamlit_javascript import st_javascript
from collections import defaultdict
import streamlit as st
import math

st.set_page_config(layout="wide")
# --- Data Classes ---
@dataclass(unsafe_hash=True)
class WikiNode:
    name: str
    in_track: list
    track_pos: list
    thickest_son: str = ""
    n_visits: int = 0
    time_appearance: int = 0
    y_sorting: int = 0 
    thickest_son: str = ""
    is_target: bool = False




# --- 1. Load Data ---
pathsFinishedDF = pd.read_csv('./data/paths_finished.tsv', sep='\t', comment='#', header=None)
paths = pathsFinishedDF.iloc[:, 3].str.split(';')

def clean_path(path):
    stack = []
    for node in path:
        if node == "<":
            if stack:
                stack.pop()
        else:
            stack.append(node)
    return stack

# Filter for Asteroid -> Viking tracks
ABpaths = pd.DataFrame()
ABpaths["paths"] = paths[(paths.str[0]=="Asteroid") & (paths.str[-1]=="Viking")]#[:100]##
ABpaths["clean_paths"] = ABpaths["paths"].apply(clean_path)
ABpaths["length"] = ABpaths["clean_paths"].apply(len)


min_length = ABpaths["length"].min()
max_length = ABpaths["length"].max()
shortest_AB_paths = ABpaths[ABpaths["length"] <= max_length]
shortest_AB_paths = shortest_AB_paths.sort_values(by="length", ascending=False)
first_nodes = [
    path[1]
    for path in shortest_AB_paths["clean_paths"]
]
# Get first node of every track

# --- 2. Count nodes and edges ---
nodes_dict = defaultdict(WikiNode)
edges_dict = defaultdict(int)

for n_path,path in enumerate(shortest_AB_paths["clean_paths"]):
    path_length = len(path)
    for i, node_name in enumerate(path):
        if node_name not in nodes_dict:
            nodes_dict[node_name] = WikiNode(name=node_name, n_visits=1, time_appearance=-1, in_track=[n_path], track_pos=[path_length-i])
        else:
            nodes_dict[node_name].n_visits += 1
            nodes_dict[node_name].in_track.append(n_path)
            nodes_dict[node_name].track_pos.append(path_length-i)
        if i < len(path) - 1:
            edges_dict[(node_name, path[i+1])] += 1

total_node_visits = 0
total_edge_visits = 0
minimum_edge_weight = 0
filtered_edges_dict = {}

for (src, tgt), w in edges_dict.items():
    if w > minimum_edge_weight:
        filtered_edges_dict[(src,tgt)] = w

valid_nodes = {src for (src, tgt) in filtered_edges_dict} | {tgt for (src, tgt) in filtered_edges_dict}

filtered_nodes_dict = {
    name: nodes_dict[name]
    for name in nodes_dict
}

#Find thickest son, and total edge visits
thickest_of_sons = 0
thickest_son_map = defaultdict(lambda: (0, None))  # (weight, tgt)
for (src, tgt), w in filtered_edges_dict.items():
    current_w, _ = thickest_son_map[src]
    if w > current_w:
        thickest_son_map[src] = (w, tgt)
    total_edge_visits += w
avg_edge_visits = total_edge_visits/len(filtered_edges_dict.items())
for node in filtered_nodes_dict:
    w, tgt = thickest_son_map[node]
    filtered_nodes_dict[node].thickest_son = tgt
    filtered_nodes_dict[node].thickest_son_weight = w

#assign y ordering
for node in filtered_nodes_dict:
    filtered_nodes_dict[node].y_sorting = -thickest_son_map[node][0]
    total_node_visits += filtered_nodes_dict[node].n_visits
avg_node_visits = total_node_visits/len(filtered_nodes_dict)





#Filter again, by post computed metrics
final_edges_dict = {}
for (src,tgt), w in filtered_edges_dict.items():
    #if tgt == filtered_nodes_dict[src].thickest_son:
        if src != "Asteroid":
            final_edges_dict[(src,tgt)] = w

valid_nodes = {src for (src, tgt) in final_edges_dict} | {tgt for (src, tgt) in final_edges_dict}

final_nodes_dict = {
    name: filtered_nodes_dict[name]
    for name in filtered_nodes_dict
    if name in valid_nodes and name != "Asteroid"
}









#Final computing, no touchy
groups = defaultdict(list)
for node in final_nodes_dict.values():
    x_val = min(node.track_pos)
    groups[x_val].append(node)

groups = dict(sorted(groups.items())) #sort
for x_val in groups:
    groups[x_val].sort(key=lambda n: n.y_sorting if n.y_sorting is not None else 0)

# --- 3. Build ECharts nodes and links ---
#width_px = 3000  # Fallback width
height_px = 250 # Fallback height

y_center = height_px / 2

nodes = []
max_len = 0
for x_val, group_nodes in groups.items():
    max_len = max(max_len,(len(group_nodes) + 1))



for x_val, group_nodes in groups.items():
    upper_counter= 0
    y_spacing = 0
    neg_y_spacing = 100
    for i, node in enumerate(group_nodes):
        node_size = 10+(node.n_visits/avg_node_visits)
        #if node.name not in {tgt for (src, tgt) in final_edges_dict}:
        #    y_pos = -neg_y_spacing
        #    neg_y_spacing +=node_size/2
        #else:
        y_pos = y_spacing
        y_spacing += node_size/2
        if node.name in valid_nodes:
            if node.name in first_nodes:
                color = "#33ff47"  
            else:
                color = "#202020"  
            node_dict = {
                "name": node.name,
                "symbolSize": node_size,
                "draggable": True,
                "tooltip": {"formatter": f"{node.name}<br>Visits: {node.n_visits}<br>Track_pos: {min(node.track_pos)}"},
                #"fixed":True,
                "x": (int(max_length)-min(node.track_pos)) * 50,
                "y": y_pos,
                "itemStyle": {
                    "color": color
                }
            }
            nodes.append(node_dict)


max_width = 50
min_width = 0.5
links = []
for (src, tgt), w in final_edges_dict.items():
        if min(final_nodes_dict[src].track_pos) < min(final_nodes_dict[tgt].track_pos):
            color = "#EB0044"  
        elif min(final_nodes_dict[src].track_pos) == min(final_nodes_dict[tgt].track_pos):
            color = "#EBDA00"  
        else:
            color = "#00B5EB"  
        links.append({
            "source": src,
            "target": tgt,
            "value": w,
            "lineStyle": {
                "color":color,
                "width":  max(min(max_width, w*0.05*(total_edge_visits-minimum_edge_weight)/total_edge_visits),min_width)
            }
        })

# --- 4. ECharts options ---
options = {
    "tooltip": {"show": True},
    "series": [
        {
            "type": "graph",
            "layout": "none",
            "data": nodes,
            "links": links,
            "roam": True,  # allow pan/zoom
            "label": {"show": False},
        }
    ]
}

# --- 5. Display in Streamlit ---

st_echarts(options=options, height="100vh")