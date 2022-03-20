#
# PeekingDuck GUI
# DOTW, (C) 2022
#

# Globals
ROOT_PATH = "/Users/dotw"
CURR_PATH = "/Users/dotw/src/pkd/car_project"
DIR_FILTERS = [""]
FILE_FILTERS = ["*.yml"]
WIN_WIDTH = 1280
WIN_HEIGHT = 800
BLACK = (0, 0, 0, 1)
WHITE = (1, 1, 1, 1)
NAVY = (0, 0, 0.5, 1)
NODE_RGBA_COLOR = {
    "augment": (153 / 255, 153 / 255, 153 / 255, 1),
    "dabble": (120 / 255, 117 / 255, 188 / 255, 1),
    "draw": (240 / 255, 115 / 255, 81 / 255, 1),
    "input": (240 / 255, 224 / 255, 156 / 255, 1),
    "model": (177 / 255, 230 / 255, 241 / 255, 1),
    "output": (160 / 255, 112 / 255, 97 / 255, 1),
    # "custom_nodes": (1, 1, 1, 0.5),
}
NODE_COLOR_SELECTED = (0, 0, 1, 0.5)
NODE_COLOR_CLEAR = (0, 0, 1, 0)
CONFIG_COLOR_SELECTED = (0.5, 0.5, 0.5, 0.5)
CONFIG_COLOR_CLEAR = (0.5, 0.5, 0.5, 0)
NODE_CONFIG_RESERVED_KEYS = {"MODEL_NODES", "weights", "weights_parent_dir"}
BUTTON_DELAY = 0.2

# Imports
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
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager

from re import A
from typing import Dict, List
import os
import yaml
from config_parser import NodeConfigParser


# Todo:
# - add pipeline node
# - delete pipeline node
# - configure pipeline node
# - save pipeline
# - show pipeline errors
# - undo/redo
# - support custom nodes definition
# - app config: default folder, etc.
# - PKD playback


class FileLoadDialog(FloatLayout):
    select = ObjectProperty(None)  # map to file/path selected method
    cancel = ObjectProperty(None)  # map to cancel method

    def setup(self, path: str, filters: List[str]):
        # dotw: weakref, cannot use python with statement
        self.ids["id_file_chooser"].rootpath = ROOT_PATH
        self.ids["id_file_chooser"].path = path
        self.ids["id_file_chooser"].filters = filters


class Node(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    select_color = ListProperty([0, 0, 0, 0])
    node_number = ObjectProperty("0")
    node_text = ObjectProperty("")


class Config(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    select_color = ListProperty([0, 0, 0, 0])
    config_key = ObjectProperty("key")
    config_value = ObjectProperty("value")
    config_set = BooleanProperty(False)


class Output(GridLayout):
    def on_touch_down(self, touch):
        # if self.collide_point(*touch.pos):
        #     print("Output: touch inside me")
        self.touch_down_callback(touch)


class ProjectInfo(GridLayout):
    directory = StringProperty("")
    filename = StringProperty("")


class ScreenPipeline(Screen):
    pass


class ScreenPlayback(Screen):
    pass


###
# Little utils
###
def get_node_type(node_title: str) -> str:
    toks = node_title.split(".")
    node_type = toks[1] if toks[0] == "custom_nodes" else toks[0]
    return node_type


def get_node_color(node_title: str):
    node_type = get_node_type(node_title)
    node_color = NODE_RGBA_COLOR[node_type]
    return node_color


class pkdguiApp(App):
    def build(self):
        """
        Main Kivy application entry point
        """
        self.title = "PeekingDuck GUI"

        sm = ScreenManager()
        self.screen_pipeline = ScreenPipeline(name="screen_pipeline")
        sm.add_widget(self.screen_pipeline)
        self.screen_playback = ScreenPlayback(name="screen_playback")
        sm.add_widget(self.screen_playback)
        self.sm = sm
        Window.left = 100
        Window.top = 100

        self.play = "stop"
        self.selected_nodes = set()
        self.selected_configs = set()
        self.setup_output()
        self.setup_key_widgets()
        self.setup_gui_working_vars()

        self.config_parser = NodeConfigParser()
        self.num_nodes = 0
        self.idx_to_node = None
        self.node_to_idx = None

        return sm

    # App GUI Widget Access
    def setup_output(self):
        screen = self.screen_playback
        pkd_view = screen.ids["pkd_view"]
        self.output_header = pkd_view.ids["pkd_header"]
        pkd_output = pkd_view.ids["pkd_output"]
        self.pkd_output = pkd_output
        # pkd_output.touch_down_callback = self.on_touch_down

    def setup_key_widgets(self):
        screen = self.screen_pipeline
        self.project_info = screen.ids["project_info"]
        pipeline_view = screen.ids["pipeline_view"]
        pipeline_header = pipeline_view.ids["pipeline_header"]
        self.pipeline_header = pipeline_header
        pipeline_config_header = pipeline_view.ids["pipeline_config_header"]
        self.pipeline_config_header = pipeline_config_header
        pipeline_config = pipeline_view.ids["pipeline_config"]
        self.pipeline_config = pipeline_config
        self.config_layout = pipeline_config.ids["config_layout"]
        pipeline_nodes_view = pipeline_view.ids["pipeline_nodes"]
        self.pipeline_nodes_view = pipeline_nodes_view
        self.nodes_layout = pipeline_nodes_view.ids["pipeline_layout"]

    def setup_gui_working_vars(self):
        # pre-declare working vars to avoid code crashing on var not found errors
        self.btn_node_move_down_held = None
        self.btn_node_move_up_held = None

    # Change headers
    def set_pipeline_header(self, text: str):
        self.pipeline_header.header_text = text

    def set_node_config_header(self, text: str, color=None, font_color=None):
        header = self.pipeline_config_header
        header.header_text = text
        if color:
            header.header_color = color
        if font_color:
            header.font_color = font_color

    def set_output_header(self, text: str):
        self.output_header.header_text = text

    def set_node_config(self, node_title: str, node_config):
        config_layout = self.config_layout
        config_layout.clear_widgets()
        default_config = self.config_parser.title_config_map[node_title].copy()
        # replace default with user config
        set_configs = set()
        for config in node_config:
            for k, v in config.items():
                if k in default_config:
                    set_configs.add(k)
                    default_config[k] = v
        # show consolidated config
        for k, v in default_config.items():
            if k not in NODE_CONFIG_RESERVED_KEYS:
                tick = k in set_configs
                config = Config(config_key=str(k), config_value=str(v), config_set=tick)
                config_layout.add_widget(config)
        self.pipeline_config.scroll_y = 1.0  # move scrollview to top

    def reset_node_config(self):
        self.config_layout.clear_widgets()
        self.set_node_config_header("Node Config", color=NAVY, font_color=WHITE)

    def clear_selected_configs(self):
        for config in self.selected_configs:
            config.select_color = CONFIG_COLOR_CLEAR
        self.selected_configs.clear()

    def clear_selected_nodes(self):
        for node in self.selected_nodes:
            node.select_color = NODE_COLOR_CLEAR
        self.selected_nodes.clear()
        self.reset_node_config()

    # App GUI Event Callbacks
    # Buttons: generic dummy callbacks
    def btn_press(self, btn, *args):
        parent = btn.parent
        print(f"btn_press: {btn.text} tag={parent.tag}")

    def btn_release(self, btn, *args):
        parent = btn.parent
        print(f"btn_release: {btn.text} tag={parent.tag}")

    # Screen transitions
    def goto_screen_pipeline(self, *args):
        self.sm.transition.direction = "right"
        self.sm.current = "screen_pipeline"

    def goto_screen_playback(self, *args):
        self.sm.transition.direction = "left"
        self.sm.current = "screen_playback"

    # Buttons: Specific
    def btn_config_press(self, btn, *args):
        """This method is called when a node config is clicked

        Args:
            btn (_type_): the config that is clicked on
        """
        self.clear_selected_configs()
        # set new selected config
        config = btn.parent
        config.select_color = CONFIG_COLOR_SELECTED
        self.selected_configs.add(config)

    def btn_node_press(self, btn, *args):
        """This method is called when a pipeline node is clicked

        Args:
            btn (_type_): the node that is clicked on
        """
        self.clear_selected_nodes()
        # set new selected node
        node = btn.parent
        node.select_color = NODE_COLOR_SELECTED
        self.selected_nodes.add(node)
        # update node config view
        node_title = btn.text
        node_type = get_node_type(node_title)
        node_color = NODE_RGBA_COLOR[node_type]
        if node_type in ("input", "model"):
            self.set_node_config_header(node_title, color=node_color, font_color=BLACK)
        else:
            self.set_node_config_header(node_title, color=node_color, font_color=WHITE)
        node_config = self.pipeline_nodes_to_configs[node_title]
        self.set_node_config(node_title, node_config)

    def btn_load_file(self, btn, *args):
        file_dialog = FileLoadDialog(select=self.load_file, cancel=self.cancel_load)
        file_dialog.setup(path=CURR_PATH, filters=FILE_FILTERS)
        self._file_dialog = Popup(
            title="Load File", content=file_dialog, size_hint=(0.75, 0.75)
        )
        self._file_dialog.open()

    def btn_save_file(self, btn, *args):
        print("btn_save_file: not implemented yet")

    def btn_quit(self, btn, *args):
        # todo: ask user to confirm quit / save changes
        self.stop()

    def cancel_load(self):
        self._file_dialog.dismiss()

    # Playback controls
    def btn_play_stop(self):
        print("btn_play_stop")

        # Touch events
        # def on_touch_down(self, touch):
        """This method is passed as a callback to widgets to get them to reroute
        their touch_down event back here.

        Args:
            touch (_type_): the touch event
        """
        # print(f"app touch: {touch.x}, {touch.y}")
        # if self.pkd_output.collide_point(*touch.pos):
        #     self.clear_selected_configs()
        #     self.clear_selected_nodes()
        # else:
        #     pass

    #####################
    # File operations
    #####################
    def load_file(self, path: str, file_paths: List[str]):
        """Method to load PeekingDuck pipeline configuration yaml file

        Args:
            path (str): Path containing the pipeline configuration yaml file
            file_paths (List[str]): Selected yaml file(s)
        """
        print(f"path={path}, file_paths={file_paths}")
        self._file_dialog.dismiss()
        the_path = file_paths[0]  # only want first file
        self.pipeline_file_path = the_path
        with open(the_path) as file:
            self.pipeline = yaml.safe_load(file)
        self.parse_pipeline()
        self.set_pipeline_header(f"Pipeline: {len(self.pipeline['nodes'])} nodes")
        self.set_output_header(self.filename)
        self.project_info.directory = os.path.dirname(the_path)
        self.project_info.filename = self.filename

    #####################
    # Pipeline processing
    #####################
    def btn_node_move_up_press(self, *args):
        # print(f"btn_node_move_up, selected={self.selected_nodes}")
        if self.selected_nodes:
            for node in self.selected_nodes:
                self.node_map_move_up(node)
            self.node_map_draw()
            self.pipeline_nodes_view.scroll_to(node)
            self.btn_node_move_up_held = Clock.schedule_once(
                self.btn_node_move_up_press, BUTTON_DELAY
            )

    def btn_node_move_up_release(self, *args):
        if self.btn_node_move_up_held:
            self.btn_node_move_up_held.cancel()

    def btn_node_move_down_press(self, *args):
        # print(f"btn_node_move_down, selected={self.selected_nodes}")
        if self.selected_nodes:
            for node in self.selected_nodes:
                self.node_map_move_down(node)
            self.node_map_draw()
            self.pipeline_nodes_view.scroll_to(node)
            self.btn_node_move_down_held = Clock.schedule_once(
                self.btn_node_move_down_press, BUTTON_DELAY
            )

    def btn_node_move_down_release(self, *args):
        if self.btn_node_move_down_held:
            self.btn_node_move_down_held.cancel()

    def btn_verify_pipeline(self, *args):
        res = self.config_parser.verify_config(self.idx_to_node)
        print(res)

    ########################
    # Node layout management
    ########################
    def setup_node_map(self, num_nodes):
        self.num_nodes = num_nodes
        self.idx_to_node = [None] * num_nodes
        self.node_to_idx = dict()

    def node_map_add(self, node, i: int):
        """Add node "node list" at given position index

        Args:
            node (_type_): node to be added
            i (int): node position index
        """
        assert i >= 0
        assert i < self.num_nodes
        self.idx_to_node[i] = node
        self.node_to_idx[node] = i
        node.node_number = str(i + 1)

    def node_map_draw(self):
        """Redraw pipeline nodes layout"""
        self.nodes_layout.clear_widgets()
        for i in range(self.num_nodes):
            node = self.idx_to_node[i]
            self.nodes_layout.add_widget(node)

    def node_map_move_up(self, node):
        """Move towards start of pipeline

        Args:
            node (_type_): node to be moved
        """
        j = self.node_to_idx[node]
        if j > 0:
            i = j - 1
            prev_node = self.idx_to_node[i]
            self.idx_to_node[i] = node
            self.node_to_idx[node] = i
            node.node_number = str(i + 1)
            self.idx_to_node[j] = prev_node
            self.node_to_idx[prev_node] = j
            prev_node.node_number = str(j + 1)

    def node_map_move_down(self, node):
        """Move towards end of pipeline

        Args:
            node (_type_): node to be moved
        """
        i = self.node_to_idx[node]
        j = i + 1
        if j < self.num_nodes:
            next_node = self.idx_to_node[j]
            self.idx_to_node[j] = node
            self.node_to_idx[node] = j
            node.node_number = str(j + 1)
            self.idx_to_node[i] = next_node
            self.node_to_idx[next_node] = i
            next_node.node_number = str(i + 1)

    def parse_pipeline(self):
        """
        Method to parse the loaded pipeline and create graphical layout of pipeline
        nodes. A copy of the pipeline is cached within self (App).
        """
        self.pipeline_nodes_to_configs = dict()  # start new data structure
        # decode pipeline
        print(f"self.pipeline: {type(self.pipeline)}")
        loaded_pipeline_nodes = self.pipeline["nodes"]
        # set header
        num_nodes = len(loaded_pipeline_nodes)
        toks = self.pipeline_file_path.split("/")
        self.filename = toks[-1]
        self.setup_node_map(num_nodes)

        # decode nodes
        for i, node in enumerate(loaded_pipeline_nodes):
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
            # cache pipeline by adding to App
            self.pipeline_nodes_to_configs[node_title] = node_config
            # create Node widget
            node_num = str(i + 1)
            node_color = get_node_color(node_title)
            node = Node(
                bkgd_color=node_color, node_number=node_num, node_text=node_title
            )
            self.node_map_add(node, i)

        self.node_map_draw()


if __name__ == "__main__":
    pkdguiApp().run()
