from dataclasses import dataclass

@dataclass
class Palette:
    ForwardColor: str = "#88C1EC"
    BackwardColor: str = "#F68181"
    EqualColor: str = "#E7E284"
    HighlightFC: str = "#0A95FF"
    HighlightBC: str = "#FF0000"
    HighlightEC: str = "#FDF003"
    BaseNodeColor: str = "#130B04"
    HighlightNodecolor: str = "#56f966"
    SelectedNodeColor: str ="#D064D1"
    SelectedBorderColor: str = "#FB00FF"


@dataclass(unsafe_hash=True)
class WikiNode:
    name: str
    quoted_name: str
    in_track: list
    track_pos: list
    shortest_to_target: int = 0
    thickest_son: str = ""
    n_visits: int = 0
    time_appearance: int = 0
    y_sorting: int = 0 
    thickest_son: str = ""
    is_target: bool = False