from dataclasses import dataclass


directionColors = ["#fc8d59","#ffffbf","#91bfdb"]
highlightColors = ["#6e40aa","#1ac7c2","#aff05b"]
@dataclass
class Palette:
    BackwardColor: str = directionColors[0]
    EqualColor: str = directionColors[1]
    ForwardColor: str = directionColors[2]



    BaseNodeColor: str = highlightColors[0]
    HighlightNodecolor: str = highlightColors[1]
    SelectedBorderColor: str = highlightColors[2]



def lighten_color(hex_color: str, factor: float = 0.5) -> str:
    """
    factor: 0 → original color
            1 → completely white
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)

    return f"#{r:02X}{g:02X}{b:02X}"

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
    thickest_son_weight: int = 0
    thickest_parent_weight: int = 0
    is_target: bool = False

ST_THEME = {
    "color": ["#000000", "#ff6b6b"],
    "backgroundColor": "#717171"
}
