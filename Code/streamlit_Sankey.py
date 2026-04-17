import pandas as pd
from dataclasses import dataclass
from streamlit_echarts import st_echarts, JsCode
from streamlit_javascript import st_javascript
from collections import defaultdict
import streamlit as st
import json
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
    thickest_son_weight: int = 0
    is_target: bool = False
    depth:int = 0




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
    total_node_visits += filtered_nodes_dict[node].n_visits
avg_node_visits = total_node_visits/len(filtered_nodes_dict)





#Filter again, by post computed metrics firstclicked paths
final_edges_dict = {}
for start_node in first_nodes:
    src = start_node
    tgt = nodes_dict[start_node].thickest_son
    while tgt != "Asteroid" and tgt != None:
        final_edges_dict[(src,tgt)] = filtered_edges_dict[(src,tgt)]
        src = tgt
        tgt = nodes_dict[tgt].thickest_son

valid_nodes = {src for (src, tgt) in final_edges_dict} | {tgt for (src, tgt) in final_edges_dict}

final_nodes_dict = {
    name: filtered_nodes_dict[name]
    for name in filtered_nodes_dict
    if name in valid_nodes and name != "Asteroid"
}
#Assign values based on reverse tree:
rev_edges = defaultdict(list)
for (src,tgt),w in final_edges_dict.items():
    if tgt in rev_edges:
        rev_edges[tgt].append(src)
    else:
        rev_edges[tgt] = [src]
    
for src,tgts in rev_edges.items():
    for tgt in tgts:
        final_nodes_dict[tgt].y_sorting = final_edges_dict[tgt,src]

max_depth = 0
final_nodes_dict["Viking"].depth = 0
next_nodes = ["Viking"]
while next_nodes:
    src = next_nodes.pop() 
    for tgt in rev_edges[src]:
        next_nodes.append(tgt)
        final_nodes_dict[tgt].depth = final_nodes_dict[src].depth+1
        max_depth = max(max_depth,final_nodes_dict[tgt].depth)


rev_edges = dict(
    sorted(rev_edges.items(), key=lambda item: final_nodes_dict[item[0]].depth, reverse=False)
)


for src in rev_edges:
    rev_edges[src].sort(key=lambda node: final_nodes_dict[node].y_sorting, reverse=True)


from collections import deque

def bfs(root, rev_edges):
    visited = set()
    order = []

    queue = deque([root])
    visited.add(root)

    while queue:
        node = queue.popleft()
        order.append(node)

        # process children
        for tgt in rev_edges.get(node, []):
            if tgt not in visited:
                visited.add(tgt)
                queue.append(tgt)
    return order

order = bfs("Viking", rev_edges)
#print(order)
nodes = []
for i,name in enumerate(order):
    node = final_nodes_dict[name]
    color = "#33ff47" if name in first_nodes else "#202020"
    nodes.append({
        "name": name,
        "itemStyle": {"color": color},
        "depth":max_depth-node.depth,
        "tooltip": {"formatter": f"{name}<br>Visits:{node.n_visits}"}
    })


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
        "value": w+5,
        "real_value":w,
        "lineStyle": {"color": color}
    })

# --- 4. ECharts options ---
tooltip_formatter = JsCode("""
function (params) {
    if (params.dataType === 'edge') {
        return params.data.source + ' → ' + params.data.target +
               '<br/>Value: ' + params.data.real_value;
    }
    return params.name;
}
""")

options = {
    "tooltip": {"trigger": "item",
                "formatter": tooltip_formatter},
    "series": [
        {
            "type": "sankey",
            "nodeAlign": "right",
            "data": nodes,
            "links": links,
            "nodeGap": 10,  
            "layoutIterations": 0,
            "emphasis": {
                "focus": "adjacency"
            },
            "lineStyle": {
                "curveness": 0.5
            },
            "label": {
                "show": True,
                "color": "#000"
            }
        }
    ]
}

# --- 5. Display in Streamlit ---

st_echarts(options=options, height="800px")