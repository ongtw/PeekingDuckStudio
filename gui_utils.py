NODE_RGBA_COLOR = {
    "augment": (142 / 255, 142 / 255, 142 / 255, 1),
    "dabble": (109 / 255, 106 / 255, 180 / 255, 1),
    "draw": (238 / 255, 103 / 255, 71 / 255, 1),
    "input": (238 / 255, 220 / 255, 146 / 255, 1),
    "model": (167 / 255, 226 / 255, 238 / 255, 1),
    "output": (150 / 255, 101 / 255, 86 / 255, 1),
    # "custom_nodes": (1, 1, 1, 0.5),
}
BLACK = (0, 0, 0, 1)
WHITE = (1, 1, 1, 1)
NAVY = (0, 0, 0.5, 1)


def get_node_type(node_title: str) -> str:
    tokens = node_title.split(".")
    node_type = tokens[1] if tokens[0] == "custom_nodes" else tokens[0]
    return node_type


def get_node_color(node_title: str):
    node_type = get_node_type(node_title)
    node_color = NODE_RGBA_COLOR[node_type]
    return node_color
