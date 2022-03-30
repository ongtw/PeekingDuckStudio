#
# PeekingDuck GUI General Utilities
#
from turtle import left
from typing import Tuple
from kivy.animation import Animation
from kivy.uix.widget import Widget

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
NODE_COLOR_SELECTED = (0.8, 0.8, 0.8, 0.3)
NODE_COLOR_CLEAR = (0, 0, 1, 0)
CONFIG_COLOR_SELECTED = (0.5, 0.5, 0.5, 0.5)
CONFIG_COLOR_CLEAR = (0.5, 0.5, 0.5, 0)


def get_node_type(node_title: str) -> str:
    tokens = node_title.split(".")
    node_type = tokens[1] if tokens[0] == "custom_nodes" else tokens[0]
    return node_type


def get_node_color(node_title: str) -> Tuple:
    node_type = get_node_type(node_title)
    node_color = NODE_RGBA_COLOR[node_type]
    return node_color


#
# Some animations just for fun
#
def up_down_widget(thing: Widget) -> None:
    # experimental
    delay = 0.10
    orig_size = (thing.width, thing.height)  # error to link direct to thing.size!
    smaller_size = (thing.width * 0.95, thing.height * 0.95)
    anim = Animation(size=smaller_size, duration=delay)
    anim += Animation(size=orig_size, duration=delay)
    anim += Animation(size=smaller_size, duration=delay)
    anim += Animation(size=orig_size, duration=delay)
    anim += Animation(size=smaller_size, duration=delay)
    anim += Animation(size=orig_size, duration=delay)
    anim.start(thing)


def shake_widget(thing: Widget) -> None:
    delay = 0.05
    orig_pos = (thing.x, thing.y)  # error to link direct to thing.pos!
    left_pos = (thing.x - 2, thing.y - 2)
    right_pos = (thing.x + 2, thing.y + 2)
    print(f"orig_pos: {orig_pos} left_pos: {left_pos} right_pos: {right_pos}")
    anim = Animation(pos=left_pos, duration=delay)
    anim += Animation(pos=right_pos, duration=delay)
    anim += Animation(pos=left_pos, duration=delay)
    anim += Animation(pos=right_pos, duration=delay)
    anim += Animation(pos=left_pos, duration=delay)
    anim += Animation(pos=right_pos, duration=delay)
    anim += Animation(pos=orig_pos, duration=delay)
    anim.start(thing)


def vanish_widget(thing: Widget) -> None:
    # experimental
    delay = 1.00
    anim = Animation(size=(0, 0), duration=delay)
    anim.start(thing)
