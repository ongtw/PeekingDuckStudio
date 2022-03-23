NODE_RGBA_COLOR = {
    "augment": (153 / 255, 153 / 255, 153 / 255, 1),
    "dabble": (120 / 255, 117 / 255, 188 / 255, 1),
    "draw": (240 / 255, 115 / 255, 81 / 255, 1),
    "input": (240 / 255, 224 / 255, 156 / 255, 1),
    "model": (177 / 255, 230 / 255, 241 / 255, 1),
    "output": (160 / 255, 112 / 255, 97 / 255, 1),
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
