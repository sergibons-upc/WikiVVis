import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts, JsCode
from collections import defaultdict
from dataclasses import dataclass
from collections import deque
import numpy as np
from urllib.parse import unquote
from bs4 import BeautifulSoup
from pathlib import Path
import altair as alt
from cahced_funcs import load_data
from struct_dataclasses import WikiNode,Palette,lighten_color,ST_THEME
import math


st.set_page_config(layout="wide")

#TODO:
#Recursive Sankey?
#Fixing global count appearances
CUSTOMPALETTE = Palette()
EdgeThicknessFilter = 0
NodeVisitFilter = 0

#start_node = "Asteroid"
#target_node = "Viking"
start_node = "Brain"
target_node = "Telephone"

# Initialize Session State for Interaction
if 'graph_selected_node' not in st.session_state:
    st.session_state.graph_selected_node = None
    st.session_state.prev_graph_selected_node = None

thickest_of_sons, edges_dict, nodes_dict, avg_node_visits,first_nodes, max_length, total_edge_visits, article_links,df_expanded = load_data(start_node, target_node)

#Slider controls
st.title("WikiVis")
with st.sidebar:
    st.header("Controls")
    # Percentage sliders (0–100)
    flow_pct = st.slider(
        "Minimum Edge Weight (%)",
        min_value=0,
        max_value=100,
        value=75,
        step=1
    )

    node_pct = st.slider(
        "Minimum Node Weight (Sankey) (%)",
        min_value=0,
        max_value=100,
        value=0,
        step=1
    )
    option = st.selectbox(
        "Graph y axis sorting",
        ["Node size", "Biggest incoming edge"]#,"Biggest outcoming edge"]
    )
    if option == "Node size":
        for node in nodes_dict:
            nodes_dict[node].y_sorting = -nodes_dict[node].n_visits
    elif option == "Biggest incoming edge":
        for node in nodes_dict:
            nodes_dict[node].y_sorting = -nodes_dict[node].thickest_parent_weight
    # elif option == "Biggest outcoming edge":
    #     for node in nodes_dict:
    #         nodes_dict[node].y_sorting = -nodes_dict[node].thickest_son_weight

    # Convert percentage to actual threshold
    EdgeThicknessFilter = (flow_pct / 100) * thickest_of_sons
    NodeVisitFilter = (node_pct / 100) * thickest_of_sons
#filter nodes
filtered_first_nodes = []
for node in first_nodes:
    if nodes_dict[node].n_visits > NodeVisitFilter:
        filtered_first_nodes.append(node)

sNode = st.session_state.get("graph_selected_node")
pNode = st.session_state.get("prev_graph_selected_node")

#Check if any node is selected, then get the node and its children/parents.
graph_selected_nodes = set()
selected_edges = set()
if sNode != None:
    graph_selected_nodes.add(sNode)
    for (src,tgt),w in edges_dict.items():
        if sNode == src:
            graph_selected_nodes.add(tgt)
            selected_edges.add((src,tgt))
        elif sNode == tgt:
            graph_selected_nodes.add(src)
            selected_edges.add((src,tgt))
    st.session_state.prev_graph_selected_node = sNode

#graph
#with st.container(border=True):
with st.expander("Graph", expanded=True):
    st.subheader("Network Graph")
    rowHeight = 600
    col1, col2 = st.columns(2, gap="small")
    with col1:
        colWidth = "." #Currently does nothing, waiting to test widths
#--
        # Total flow
        total_weight = sum(edges_dict.values())
        # Sort edges by weight descending
        sorted_edges = sorted(edges_dict.items(), key=lambda x: x[1], reverse=True)
        # Select edges until we reach the desired %
        threshold = total_weight * (flow_pct / 100)
        cumulative = 0
        top_edges = set()

        for (edge, w) in sorted_edges:
            if cumulative >= threshold:
                break
            top_edges.add(edge)
            cumulative += w
        graph_filtered_edges_dict = {
        edge: edges_dict[edge]
        for edge in top_edges
        }
#--
        #Filter nodes based on the edge filter
        graph_valid_nodes = (
            {src for (src, tgt) in graph_filtered_edges_dict} |
            {tgt for (src, tgt) in graph_filtered_edges_dict} |
            {node for node in graph_selected_nodes}
        )

        #Divide in groups to make y stacking.
        groups = defaultdict(list)
        for node in nodes_dict.values():
            groups[node.shortest_to_target].append(node)
        groups = dict(sorted(groups.items())) #sort
        for x_val in groups:
            groups[x_val].sort(key=lambda n: n.y_sorting if n.y_sorting is not None else 0)

        max_group_len = max(
            (sum(1 for node in group if node.name in graph_valid_nodes)
            for group in groups.values()),
            default=0
        )
        #max_group_len = max((len(group) for group in groups.values()), default=0)

        # --- Constants ---
        max_node_size = 50
        min_node_size = 1
        height = 100
        ratio = 12/3



        all_nodes = nodes_dict.values()
        min_x = min(n.shortest_to_target for n in all_nodes)
        max_x = max(n.shortest_to_target for n in all_nodes)
        x_range = max_x - min_x or 1

        max_visits = max(n.n_visits for n in all_nodes)

        lighten_factor = 0.6 if sNode is not None else 0.0


        # --- Helpers ---
        def compute_color(node, base_color):
            if node.name in graph_selected_nodes:
                return CUSTOMPALETTE.SelectedBorderColor
            if sNode is not None:
                return lighten_color(base_color, lighten_factor)
            return base_color


        # --- Build nodes ---
        nodes = []

        for x_val, group_nodes in groups.items():
            y_cursor = 0
            valid_y_group_nodes = [node for node in group_nodes if node.name in graph_valid_nodes]
            if valid_y_group_nodes:
                y_gap = height / len(valid_y_group_nodes)
            else:
                y_gap = height/1
            for node in group_nodes:
                if node.name not in graph_valid_nodes:
                    continue

                is_start = node.name == start_node
                is_selected = node.name in graph_selected_nodes
                # Size
                norm = math.log1p(node.n_visits) / math.log1p(max_visits)
                node_size =  min_node_size + (max_node_size - min_node_size) * (norm ** 4)
                # Base color
                base_color = (
                    CUSTOMPALETTE.HighlightNodecolor
                    if node.name in first_nodes
                    else CUSTOMPALETTE.BaseNodeColor
                )

                color = compute_color(node, base_color)
                # Position
                y = -node_size/2 if is_start else y_cursor + y_gap
                # X scaling
                x = -((node.shortest_to_target - min_x) / x_range) * height * ratio

                node_dict = {
                    "name": node.name,
                    "symbolSize": node_size,
                    "draggable": True,
                    "tooltip": {
                        "formatter": (
                            f"{node.name}<br>"
                            f"Visits: {node.n_visits}<br>"
                            f"Track_pos: {min(node.track_pos)}"
                        )
                    },
                    "x": x,
                    "y": y,
                    "itemStyle": {"color": color},
                }

                if is_selected:
                    node_dict["itemStyle"].update({
                        "borderColor": CUSTOMPALETTE.SelectedBorderColor,
                        "borderWidth": 2,
                        "borderType": "solid",
                        "opacity": 1,
                    })

                nodes.append(node_dict)

                if not is_start:
                    y_cursor = y + y_gap
        
        #edge parameters
        max_width = max_node_size/2
        min_width = 1
        links = []
        for (src, tgt), w in edges_dict.items():
            is_filtered = (src, tgt) in graph_filtered_edges_dict
            is_selected = (src, tgt) in selected_edges
            if not (is_filtered or is_selected):
                continue
            opacity = 0.5 if sNode == None else 0.3

            src_dist = nodes_dict[src].shortest_to_target
            tgt_dist = nodes_dict[tgt].shortest_to_target
            
            max_weight = max(edges_dict.values())
            width = min_width + (max_width - min_width) * (
                (math.log1p(w) / math.log1p(max_weight)) ** 4
            )

            # Determine color #TODO highlight
            if src_dist < tgt_dist:
                color =  CUSTOMPALETTE.BackwardColor
            elif src_dist == tgt_dist:
                color =  CUSTOMPALETTE.EqualColor
            else:
                color =  CUSTOMPALETTE.ForwardColor

            line_style = {
                "color": color,
                "width": width,
                "opacity": 1 if is_selected else opacity
            }

            if is_selected:
                line_style.update({
                    "shadowBlur": 5,
                    "shadowColor": CUSTOMPALETTE.SelectedBorderColor,
                    "opacity":1
                })

            links.append({
                "source": src,
                "target": tgt,
                "value": w,
                "lineStyle": line_style
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
                    "label": {"show": False}
                }
            ]
        }

        events = {
        "click": "function(params) { return params.data.name; }"
        }   

        # --- 5. Display in Streamlit ---
        clicked_graph = st_echarts(options=options,
                                    events=events,
                                    on_select="ignore",
                                    height="600px", key="graph_viz",
                                    #theme=ST_THEME
                                    )
        
        clicked = clicked_graph.get("chart_event")
        if clicked:
            current = st.session_state.get("graph_selected_node")
            if current == clicked:
                # if same node clicked twice reset
                st.session_state.graph_selected_node = None
                st.session_state.prev_graph_selected_node = None
            else:
                st.session_state.prev_graph_selected_node = current
                st.session_state.graph_selected_node = clicked
            st.rerun()

    with col2:
        displayNode = sNode if sNode is not None else start_node
        filtered = df_expanded[df_expanded["name"] == displayNode].copy()

        # Map shortest distances
        filtered["src_dist"] = filtered["name"].map(
            lambda x: nodes_dict[x].shortest_to_target
        )
        filtered["tgt_dist"] = filtered["link"].map(
            lambda x: nodes_dict[x].shortest_to_target if x in nodes_dict else 0
        )

        # Compute direction directly
        filtered["direction"] = np.where(
            filtered["src_dist"] < filtered["tgt_dist"], "backward",
            np.where(
                filtered["src_dist"] == filtered["tgt_dist"], "equal",
                "forward"
            )
        )
        #Map NaN to direction
        filtered["direction"] = np.where(
            filtered["duplicated"] == 1,
            "repeated link",
            filtered["direction"]
        )

        # max_val = filtered["n_uses"].max()
        # filtered["n_uses"] = np.where(
        #     filtered["duplicated"] ==1,
        #     max_val,
        #     filtered["n_uses"]
        # )

        chart = alt.Chart(filtered).mark_bar().encode(
            x="n_uses:Q",
            y="position:O",
            color=alt.Color(
                "direction:N",
                scale=alt.Scale(
                    domain=["forward", "backward", "equal", "repeated link"],
                    range=[
                        CUSTOMPALETTE.ForwardColor,
                        CUSTOMPALETTE.BackwardColor,
                        CUSTOMPALETTE.EqualColor,
                        "lightgray"
                    ]
                )
            ),
            tooltip=["link", "n_uses", "direction"]
        ).properties(
            height=600,
            width=300
        )
        st.altair_chart(chart)

    # --- COLUMN 2: SANKEY ---
    #with col2:
with st.expander("Sankey", expanded=True):
    st.subheader("Sankey Flow")

    #Filter by thickest son
    final_edges_dict = {}
    #print(filtered_first_nodes, end="\n\n")
    for s_node in filtered_first_nodes:
        src = s_node
        tgt = nodes_dict[src].thickest_son
        while  tgt != None:# and tgt != start_node:
            final_edges_dict[(src,tgt)] = edges_dict[(src,tgt)]
            src = tgt
            tgt = nodes_dict[tgt].thickest_son

    valid_nodes = {src for (src, tgt) in final_edges_dict} | {tgt for (src, tgt) in final_edges_dict}

    final_nodes_dict = {
        name: nodes_dict[name]
        for name in nodes_dict
        if name in valid_nodes# and name != start_node
    }
    #Assign values based on reverse tree:
    rev_edges = defaultdict(list)
    for (src,tgt),w in final_edges_dict.items():
        rev_edges[tgt].append(src)
        
    for src,tgts in rev_edges.items():
        for tgt in tgts:
            final_nodes_dict[tgt].y_sorting = final_edges_dict[(tgt,src)]

    max_depth = 0
    final_nodes_dict[target_node].depth = 0
    next_nodes = [target_node]
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

    order = bfs(target_node, rev_edges)
    #print(order)
    def process_order(order, selected_node, nodes_dict, rev_edges, edges):
        result = []
        thickest_post = nodes_dict[selected_node].thickest_son
        thickest_pre = max(
            (src for (src, tgt) in edges_dict
            if tgt == selected_node and src),
            key=lambda src: edges_dict[src,selected_node],
            default=None
        )
        [tgt for (src, tgt) in edges_dict if src == selected_node]
        thickest_pre
        for node in order:
            result.append(node)
            if node == thickest_post:
                for afterNode in [tgt for (src, tgt) in edges_dict if src == selected_node]:
                    if afterNode not in order:
                        nodes_dict[afterNode].depth = nodes_dict[sNode].depth-1
                        result.append(afterNode)
            elif node == thickest_pre:
                for preNode in [src for (src, tgt) in edges_dict if tgt == selected_node]:
                    if preNode not in order:
                        nodes_dict[preNode].depth = nodes_dict[sNode].depth+1
                        result.append(preNode)

        return result
    
    sankey_edges_dict = defaultdict(int)
    if sNode != None:
        order = process_order(order, sNode , nodes_dict, rev_edges, final_edges_dict)

        sankey_edges_dict = final_edges_dict
        for node in [src for (src, tgt) in edges_dict if tgt == sNode]:
            sankey_edges_dict[node,sNode] = edges_dict[node,sNode]
        for node in [tgt for (src, tgt) in edges_dict if src == sNode]:
            sankey_edges_dict[sNode,node] = edges_dict[sNode,node]
    else:
        sankey_edges_dict = final_edges_dict
    #deduplicate
    sankey_edges_dict = list(dict.fromkeys(sankey_edges_dict.keys()))
    order = list(dict.fromkeys(order))
    # print("--------")
    # print(order," \n.\n")
    # print(sankey_edges_dict, "\n.\n")
    nodes = []
    for i,name in enumerate(order):
        node = nodes_dict[name]
        if name in filtered_first_nodes:
            color = CUSTOMPALETTE.HighlightNodecolor
        else :
            color = CUSTOMPALETTE.BaseNodeColor
        if name == sNode:
            color = CUSTOMPALETTE.SelectedBorderColor
        if name in graph_valid_nodes:
            opacity = 1
        else:
            opacity = 0.1
        if name in graph_selected_nodes:
            nodes.append({
                "name": name,
                "itemStyle": {"color": color,
                            "opacity":opacity,
                            "borderColor": CUSTOMPALETTE.SelectedBorderColor, # Pborder
                            "borderWidth": 3,
                            "borderType": "solid"   
                            },
                "depth":max_depth-node.depth,
                "tooltip": {"formatter": f"{name}<br>Visits:{node.n_visits}"}
            })
        else:
            nodes.append({
                "name": name,
                "itemStyle": {"color": color,
                            "opacity":opacity},
                "depth":max_depth-node.depth,
                "tooltip": {"formatter": f"{name}<br>Visits:{node.n_visits}"}
            })


    links = []
    for (src, tgt), w in final_edges_dict.items():

        if (src,tgt) in graph_filtered_edges_dict:
            opacity = 0.9
        else:
            opacity = 0.1
        if (src,tgt) in selected_edges:
            if nodes_dict[src].shortest_to_target < nodes_dict[tgt].shortest_to_target:
                color = CUSTOMPALETTE.BackwardColor
            elif nodes_dict[src].shortest_to_target == nodes_dict[tgt].shortest_to_target:
                color = CUSTOMPALETTE.EqualColor
            else:
                color = CUSTOMPALETTE.ForwardColor
            links.append({
                "source": src,
                "target": tgt,
                "value": w+3,
                "real_value":w,
                "lineStyle": {"color": color,
                            "opacity":opacity,
                            "shadowBlur": 5,
                            "shadowColor": CUSTOMPALETTE.SelectedBorderColor
                            },
            })
        else:
            if final_nodes_dict[src].shortest_to_target < final_nodes_dict[tgt].shortest_to_target:
                color = CUSTOMPALETTE.BackwardColor
            elif final_nodes_dict[src].shortest_to_target == final_nodes_dict[tgt].shortest_to_target:
                color = CUSTOMPALETTE.EqualColor
            else:
                color = CUSTOMPALETTE.ForwardColor
            links.append({
                "source": src,
                "target": tgt,
                "value": w+3,
                "real_value":w,
                "lineStyle": {"color": color,
                            "opacity":opacity,
                            },
            })

    #function to display real weight without added value
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
                "nodeGap": 30,  
                "layoutIterations": 0,
                "emphasis": {
                    "focus": "adjacency"
                },
                "lineStyle": {
                    "curveness": 0.3
                },
                "label": {
                    "show": True,
                    "color": "#000"
                }
            }
        ]
    }
    events = {
        "click": "function(params) { return params.data.name; }"
    }   
    sankey_event = st_echarts(options=options,
                              events=events, 
                              on_select="ignore",
                              height="600px", 
                              key="sankey_viz",
                              #theme=ST_THEME
                              )

    clicked = sankey_event.get("chart_event")
    if clicked:
        current = st.session_state.get("graph_selected_node")
        if current == clicked:
            # if same node clicked twice reset
            st.session_state.graph_selected_node = None
            st.session_state.prev_graph_selected_node = None
        else:
            st.session_state.prev_graph_selected_node = current
            st.session_state.graph_selected_node = clicked
        st.rerun()

with st.expander("Global chart", expanded=False):

#Total sum
    df_expanded["relative_uses"] = (
        df_expanded["n_uses"] /
        df_expanded.groupby("name")["n_uses"].transform("sum")
    )

    df_unique = df_expanded.drop_duplicates(subset=["name", "position"])

    df_positions = (
        df_unique.groupby("position", as_index=False)["relative_uses"].sum()
    )

    df_positions = df_positions.sort_values("position")

    chart = alt.Chart(df_positions).mark_bar().encode(
        x=alt.X("relative_uses:Q", title="Total Relative Uses"),
        y=alt.Y("position:O", sort="ascending", title="Link Position"),
        tooltip=["position", "relative_uses"]
    ).properties(
        width=600,
        height=400
    )
    
    st.altair_chart(chart, width='stretch')
