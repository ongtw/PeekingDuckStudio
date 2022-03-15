#
# PeekingDuck GUI
# DOTW, (C) 2022
#

# Globals
ROOT_PATH = "/Users/dotw"
CURR_PATH = "/Users/dotw/src/pkd/people_walking"
FILE_FILTERS = ["*.yml"]
WIN_WIDTH = 1280
WIN_HEIGHT = 800
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
NODE_SELECT_COLOR = (1, 0, 0, 1)

# Imports
from re import A
from typing import Dict, List
import yaml

from kivy.config import Config

# change window size from 800x600 to 1024x768 (must be before other kivy modules)
Config.set("graphics", "width", WIN_WIDTH)
Config.set("graphics", "height", WIN_HEIGHT)
Config.set("graphics", "minimum_width", WIN_WIDTH)
Config.set("graphics", "minimum_height", WIN_HEIGHT)
Config.set("graphics", "resizable", False)

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.properties import ListProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager


class FileLoadDialog(FloatLayout):
    # map to load_file() and cancel_file() methods
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)

    def setup(self, path: str, filters: List[str]):
        # dotw: weakref, cannot use python with statement
        self.ids["id_file_chooser"].rootpath = ROOT_PATH
        self.ids["id_file_chooser"].path = path
        self.ids["id_file_chooser"].filters = filters


class Node(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    border_color = ListProperty([0, 0, 0, 1])
    node_number = ObjectProperty("0")
    node_text = ObjectProperty("")


class Config(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    config_key = ObjectProperty("key")
    config_value = ObjectProperty("value")


class ScreenOne(Screen):
    pass


###
# Little utils
###
def get_node_type(node_title: str) -> str:
    toks = node_title.split(".")
    node_type = toks[1] if toks[0] == "custom_nodes" else toks[0]
    return node_type


class pkdguiApp(App):
    def build(self):
        self.title = "PeekingDuck GUI"
        sm = ScreenManager()
        self.screen_one = ScreenOne(name="screen_one")
        sm.add_widget(self.screen_one)
        self.sm = sm
        Window.left = 100
        # Window.top = 100
        self.play = "stop"
        self.selected_nodes = set()
        return sm

    # App GUI Widget Access
    def set_pipeline_header(self, text: str):
        screen = self.screen_one
        pipeline_view = screen.ids["pipeline_view"]
        header = pipeline_view.ids["pipeline_header"]
        header.header_text = text

    def set_node_config_header(self, text: str, color=None, font_color=None):
        screen = self.screen_one
        pipeline_view = screen.ids["pipeline_view"]
        header = pipeline_view.ids["pipeline_config_header"]
        header.header_text = text
        if color:
            header.header_color = color
        if font_color:
            header.font_color = font_color

    def set_node_config(self, node_config):
        print(node_config)
        screen = self.screen_one
        pipeline_view = screen.ids["pipeline_view"]
        pipeline_config = pipeline_view.ids["pipeline_config"]
        config_layout = pipeline_config.ids["config_layout"]
        config_layout.clear_widgets()
        for config in node_config:
            for k, v in config.items():
                config = Config(config_key=str(k), config_value=str(v))
                config_layout.add_widget(config)

    # App GUI Event Callbacks
    def btn_dummy(self, *args):
        print("btn_dummy: nothing at all")

    def btn_node_press(self, *args):
        btn = args[0]
        print(f"*args={args}, btn: {btn.text}")
        # clear currently selected node
        for node in self.selected_nodes:
            node.border_color = BLACK
        self.selected_nodes.clear()
        # set new selected node
        node = btn.parent
        node.border_color = NODE_SELECT_COLOR
        self.selected_nodes.add(node)
        node_title = btn.text
        node_type = get_node_type(node_title)
        node_color = NODE_RGBA_COLOR[node_type]
        if node_type in ("input", "model"):
            self.set_node_config_header(node_title, color=node_color, font_color=BLACK)
        else:
            self.set_node_config_header(node_title, color=node_color, font_color=WHITE)
        node_config = self.pipeline_nodes[node_title]
        self.set_node_config(node_config)

    def btn_load_file(self):
        file_dialog = FileLoadDialog(load=self.load_file, cancel=self.cancel_load)
        file_dialog.setup(path=CURR_PATH, filters=FILE_FILTERS)
        self._file_dialog = Popup(
            title="Load File", content=file_dialog, size_hint=(0.75, 0.75)
        )
        self._file_dialog.open()

    def btn_save_file(self):
        print("btn_save_file: not implemented yet")

    def btn_quit(self):
        # todo: ask user to confirm quit / save changes
        self.stop()

    def cancel_load(self):
        self._file_dialog.dismiss()

    # Playback controls
    def btn_play_stop(self):
        print("btn_play_stop")

    #####################
    # File operations
    #####################
    def load_file(self, path: str, file_paths: List[str]):
        print(f"path={path}, file_paths={file_paths}")
        self._file_dialog.dismiss()
        self.pipeline_file_path = file_paths[0]  # only want first file
        with open(self.pipeline_file_path) as file:
            self.pipeline = yaml.safe_load(file)
        self.parse_pipeline()

    #####################
    # Pipeline processing
    #####################
    def parse_pipeline(self):
        # prepare pipeline nodes layout
        screen = self.screen_one
        pipeline_view = screen.ids["pipeline_view"]
        pipeline_nodes = pipeline_view.ids["pipeline_nodes"]
        nodes_layout = pipeline_nodes.ids["pipeline_layout"]
        nodes_layout.clear_widgets()

        # decode pipeline and cache in self
        print(f"self.pipeline: {self.pipeline_file_path}")
        print(self.pipeline)
        pipeline_nodes = self.pipeline["nodes"]
        # set header
        num_nodes = len(pipeline_nodes)
        toks = self.pipeline_file_path.split("/")
        filename = toks[-1]
        self.set_pipeline_header(f"{filename}, {num_nodes} nodes")
        # decode nodes
        self.pipeline_nodes = dict()  # start new data structure
        for i, node in enumerate(pipeline_nodes):
            if isinstance(node, str):
                node_title = node
                node_config = [{"None": "No Config"}]
            else:  # must be dict
                node_title = list(node.keys())[0]
                node_config = []
                config_dd = node[node_title]
                for k, v in config_dd.items():
                    kv_dict = {k: v}
                    node_config.append(kv_dict)

            self.pipeline_nodes[node_title] = node_config

            node_num = str(i + 1)
            # toks = node_title.split(".")
            # node_type = toks[1] if toks[0] == "custom_nodes" else toks[0]
            node_type = get_node_type(node_title)
            node_color = NODE_RGBA_COLOR[node_type]

            node = Node(
                bkgd_color=node_color, node_number=node_num, node_text=node_title
            )
            nodes_layout.add_widget(node)


if __name__ == "__main__":
    pkdguiApp().run()
