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
   
        #Reduce opacity of unselected nodes, when some node is selected
        nodes = []
        lighten_factor = 0.6 if sNode is not None else 0.0
        #Save node visual properties, iterate groups
        for x_val, group_nodes in groups.items():
            y_cursor = -100 
            for node in group_nodes:
                node_size = 3 + node.n_visits / 10
                d = node_size
                #set start node an extra height.
                if node.name == start_node:
                    y = -100 -node_size
                else:
                    y = y_cursor + d
                #nodes not in the filter get dumped, and the iteration restituted, this is if i want to change opacity instead, the structure is already inplace.
                if node.name not in graph_valid_nodes:
                    continue
                #Color for nodes (base nodes and first nodes)
                color = (
                    CUSTOMPALETTE.HighlightNodecolor
                    if node.name in first_nodes
                    else CUSTOMPALETTE.BaseNodeColor
                )

                is_selected = node.name in graph_selected_nodes

                if is_selected:
                    color = CUSTOMPALETTE.SelectedBorderColor
                elif sNode is not None:
                    # fade non-selected nodes by whitening them
                    color = lighten_color(color, lighten_factor)
                #save node
                node_dict = {
                    "name": node.name,
                    "symbolSize": node_size,
                    "draggable": True,
                    "tooltip": {
                        "formatter": f"{node.name}<br>Visits: {node.n_visits}<br>Track_pos: {min(node.track_pos)}"
                    },
                    "x": -node.shortest_to_target * 500,
                    "y": y,
                    "itemStyle": {
                        "color": color
                    },
                }
                #Add border to selected nodes
                if is_selected:
                    node_dict["itemStyle"].update({
                        "borderColor": CUSTOMPALETTE.SelectedBorderColor,
                        "borderWidth": 2,
                        "borderType": "solid",
                        "opacity":1
                    })

                nodes.append(node_dict)
                # Update layout state
                if node.name != start_node:
                    y_cursor = y  + d
        
        
        #edge parameters
        max_width = 75
        min_width = 1
        links = []
        for (src, tgt), w in edges_dict.items():
            is_filtered = (src, tgt) in graph_filtered_edges_dict
            is_selected = (src, tgt) in selected_edges
            if not (is_filtered or is_selected):
                continue
            opacity = 1 if sNode == None else 0.3

            src_dist = nodes_dict[src].shortest_to_target
            tgt_dist = nodes_dict[tgt].shortest_to_target

            width = max(
                min(max_width, w * 0.05 * (total_edge_visits) / total_edge_visits),
                min_width
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
        filtered = df_expanded[df_expanded["name"] == displayNode]

        df_plot = (
            filtered
            .sort_values("position")  # ensures lowest position comes first
            .drop_duplicates(subset=["link"], keep="first")
        )

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
        


        chart = alt.Chart(filtered).mark_bar().encode(
            x="n_uses:Q",
            y="position:O",
            color=alt.Color(
                "direction:N",
                scale=alt.Scale(
                    domain=["forward", "backward", "equal", "none"],
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
            height=600
        )
        st.altair_chart(chart, width='stretch')

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
        if tgt in rev_edges:
            rev_edges[tgt].append(src)
        else:
            rev_edges[tgt] = [src]
        
    for src,tgts in rev_edges.items():
        for tgt in tgts:
            final_nodes_dict[tgt].y_sorting = final_edges_dict[tgt,src]

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
    nodes = []
    for i,name in enumerate(order):
        node = final_nodes_dict[name]
        if name in filtered_first_nodes:
            color = CUSTOMPALETTE.HighlightNodecolor
        else :
            color = CUSTOMPALETTE.BaseNodeColor
        if name == sNode:
            color = CUSTOMPALETTE.SelectedBorderColor #Darken
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

    #control click
    if sankey_event["chart_event"]:
        print("sankey event ", sankey_event)
        st.session_state.graph_selected_node = sankey_event["chart_event"]
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