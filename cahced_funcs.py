import pandas as pd
import streamlit as st
from collections import defaultdict
import numpy as np
from urllib.parse import unquote
from bs4 import BeautifulSoup
from pathlib import Path
from struct_dataclasses import WikiNode

@st.cache_data
def load_data(start_node, target_node):
    pathsFinishedDF = pd.read_csv('./Data/paths_finished.tsv', sep='\t', comment='#', header=None)
    articles = pd.read_csv('./Data/articles.tsv', sep='\t', comment='#', header=None, names=['name'])
    article_names = articles['name'].apply(unquote).values

    def load_matrix(filepath):
        data = []
        with open(filepath, 'r') as f:
            for line in f:
                # Skip comments and empty lines
                if line.startswith('#') or not line.strip():
                    continue
                row = list(line.strip())
                data.append(row)
        
        df = pd.DataFrame(data, index=article_names, columns=article_names)
        
        df = df.replace('_', np.nan).apply(pd.to_numeric)
        
        return df
    shortest_path_lengths = load_matrix("./Data/shortest-path-distance-matrix.txt")
    #print(shortest_path_lengths.head())
    paths = pathsFinishedDF.iloc[:, 3].str.split(';')

    def clean_path(path):
        stack = []
        for node in path:
            if node == "<":
                if stack:
                    stack.pop()
            else:
                stack.append(unquote(node))#must be unquoted to read articles
        return stack
    
    def clean_path_quoted(path):
        stack = []
        for node in path:
            if node == "<":
                if stack:
                    stack.pop()
            else:
                stack.append(node)#must be unquoted to read articles
        return stack

    # Filter for Asteroid -> Viking tracks
    ABpaths = pd.DataFrame()
    ABpaths["paths"] = paths[(paths.str[0]==start_node) & (paths.str[-1]==target_node)]#[:100]##
    ABpaths["clean_paths"] = ABpaths["paths"].apply(clean_path)
    ABpaths["quoted_paths"] = ABpaths["paths"].apply(clean_path_quoted)
    ABpaths["length"] = ABpaths["clean_paths"].apply(len)


    min_length = ABpaths["length"].min()
    max_length = ABpaths["length"].max()
    shortest_AB_paths = ABpaths[ABpaths["length"] <= max_length]
    shortest_AB_paths = shortest_AB_paths.sort_values(by="length", ascending=False)
    first_nodes = [
        path[1]
        for path in shortest_AB_paths["clean_paths"]
    ]

    nodes_dict = defaultdict(WikiNode)
    edges_dict = defaultdict(int)

    for n_path,(path,quoted_path) in enumerate(zip(shortest_AB_paths["clean_paths"],shortest_AB_paths["quoted_paths"])):
        path_length = len(path)
        for i, node_name in enumerate(path):
            if node_name not in nodes_dict:
                nodes_dict[node_name] = WikiNode( name=node_name,
                                                  quoted_name=quoted_path[i],
                                                  n_visits=1,
                                                  time_appearance=-1,
                                                  in_track=[n_path],
                                                  track_pos=[path_length-i],
                                                  shortest_to_target = shortest_path_lengths.loc[node_name,target_node]
                                                )
            else:
                nodes_dict[node_name].n_visits += 1
                nodes_dict[node_name].in_track.append(n_path)
                nodes_dict[node_name].track_pos.append(path_length-i)
            if i < len(path) - 1:
                edges_dict[(node_name, path[i+1])] += 1
    total_edge_visits = 0
    total_node_visits = 0 
    thickest_of_sons = 0
    thickest_son_map = defaultdict(lambda: (0, None))  # (weight, tgt)
    for (src, tgt), w in edges_dict.items():
        current_w, _ = thickest_son_map[src]
        if w > current_w:
            thickest_son_map[src] = (w, tgt)
        total_edge_visits += w
    avg_edge_visits = total_edge_visits/len(edges_dict.items())
    for node in nodes_dict:
        w, tgt = thickest_son_map[node]
        nodes_dict[node].thickest_son = tgt
        nodes_dict[node].thickest_son_weight = w
        nodes_dict[node].y_sorting = -thickest_son_map[node][0]
        thickest_of_sons = max(thickest_of_sons, w )
        total_node_visits += nodes_dict[node].n_visits
    avg_node_visits = total_node_visits/len(nodes_dict)

    article_links = []
    for node in nodes_dict:
        #load article
        with open("./Data/wpcd/wp/"+str(nodes_dict[node].quoted_name.lower()[0])+"/"+str(nodes_dict[node].quoted_name)+".htm", "r", encoding="utf-8") as file:
            html_content = file.read()
            soup = BeautifulSoup(html_content, "html.parser")
            # Extract links in order
            links = []
            for a_tag in soup.find_all("a"):

                href = a_tag.get("href")
                if href:  # ignore <a> tags without href
                    if "/images/" in href:
                        #print(href)
                        continue
                    if "/index/" in href:
                        #print(href)
                        continue
                    clean_name = Path(href).stem 
                    links.append(clean_name)
            article_links.append((node,links))

            df_links = pd.DataFrame(article_links, columns=["name", "links"])
            df_expanded = df_links.explode("links").rename(columns={"links": "link"})
            df_expanded["position"] = df_expanded.groupby("name").cumcount()
            df_expanded["n_uses"] = df_expanded.apply(
                lambda row: edges_dict[row["name"],row["link"]]
                if (row["name"], row["link"]) in edges_dict
                else 0,
                axis=1
            )

            

            mask = df_expanded.groupby(["name", "link"])["position"].transform("min") == df_expanded["position"]
            df_expanded["direction"] = ""
            df_expanded.loc[~mask, "direction"] = "repeated link"
            #not set to Nan, mark direction

    return thickest_of_sons, edges_dict, nodes_dict, avg_node_visits,first_nodes, max_length, total_edge_visits, article_links, df_expanded

