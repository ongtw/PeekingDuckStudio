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
NODE_COLOR_SELECTED = (0, 0, 1, 0.5)
NODE_COLOR_CLEAR = (0, 0, 1, 0)
CONFIG_COLOR_SELECTED = (0.5, 0.5, 0.5, 0.5)
CONFIG_COLOR_CLEAR = (0.5, 0.5, 0.5, 0)
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

from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager

import os
from re import A
from typing import Dict, List
from gui_widgets import (
    FileLoadDialog,
    ScreenPipeline,
    ScreenPlayback,
)
from config_parser import NodeConfigParser
from config_controller import ConfigController
from pipeline_controller import PipelineController
from pipeline_model import PipelineModel

# Todo:
# - add pipeline node
# - delete pipeline node
# - configure pipeline node
# - save pipeline
# - show pipeline errors
# - anomalous pipelines:
#   * duplicate nodes
#   * multiple nodes of same type (any allowed combo?)
# - undo/redo
# - support custom nodes definition
# - app config: default folder, etc.
# - PKD playback


class PeekingDuckGuiApp(App):
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
        # Window.top = 100

        self.play = "stop"
        self.selected_node = None
        self.all_selected_nodes = set()
        self.all_selected_configs = set()
        self.setup_output()
        self.setup_key_widgets()
        self.setup_gui_working_vars()

        self.config_parser = NodeConfigParser()
        self.config_controller = ConfigController(
            self.config_parser, self.pipeline_view
        )
        self.pipeline_controller = PipelineController(
            self.config_parser, self.pipeline_view
        )
        self.pipeline_model = None

        # disable 'coz interferes with TextInput overlay
        # self._keyboard = Window.request_keyboard(
        #     self.keyboard_closed, self.screen_pipeline
        # )
        # self._keyboard.bind(on_key_down=self.on_keyboard_down)

        return sm

    # Keyboard events
    def to_window(self, x, y, initial=True, relative=False):
        # Need this for keyboard events to work properly (quick hack?)
        return x, y

    def keyboard_closed(self) -> None:
        self._keyboard.unbind(on_key_down=self.on_keyboard_down)
        self._keyboard = None

    def on_keyboard_down(self, keyboard, keycode, text, modifiers) -> bool:
        print(f"Keycode: {keycode} pressed, text={text}, modifiers={modifiers}")
        # if keycode[1] == "escape":
        #     keyboard.release()  # stop accepting key inputs
        # if keycode[1] == "escape":
        #     self.clear_selected_configs()
        #     self.clear_selected_nodes()
        #     return True  # to accept key, else will be used by system
        return False

    # App GUI Widget Access
    def setup_output(self) -> None:
        screen = self.screen_playback
        pkd_view = screen.ids["pkd_view"]
        self.output_header = pkd_view.ids["pkd_header"]
        pkd_output = pkd_view.ids["pkd_output"]
        self.pkd_output = pkd_output
        # pkd_output.touch_down_callback = self.on_touch_down

    def setup_key_widgets(self) -> None:
        screen = self.screen_pipeline
        self.project_info = screen.ids["project_info"]
        self.pipeline_view = screen.ids["pipeline_view"]

    def setup_gui_working_vars(self):
        # pre-declare working vars to avoid code crashing on var not found errors
        self.btn_node_move_down_held = None
        self.btn_node_move_up_held = None

    # Change headers
    def set_output_header(self, text: str) -> None:
        self.output_header.header_text = text

    # Misc
    def clear_selected_configs(self) -> None:
        """Unselect currently selected node config"""
        for config in self.all_selected_configs:
            config.select_color = CONFIG_COLOR_CLEAR
        self.all_selected_configs.clear()

    def clear_selected_nodes(self) -> None:
        """Unselect currently selected pipeline node"""
        for node in self.all_selected_nodes:
            node.select_color = NODE_COLOR_CLEAR
        self.all_selected_nodes.clear()
        self.selected_node = None
        self.config_controller.clear_node_configs()

    # App GUI Event Callbacks
    # Buttons: generic dummy callbacks
    def btn_press(self, btn, *args) -> None:
        parent = btn.parent
        print(f"btn_press: {btn.text} tag={parent.tag}")

    def btn_release(self, btn, *args) -> None:
        parent = btn.parent
        print(f"btn_release: {btn.text} tag={parent.tag}")

    # Buttons: Specific
    # Screen transitions
    def btn_goto_screen_pipeline(self, *args) -> None:
        self.sm.transition.direction = "right"
        self.sm.current = "screen_pipeline"

    def btn_goto_screen_playback(self, *args) -> None:
        self.sm.transition.direction = "left"
        self.sm.current = "screen_playback"

    def show_node_configs(self) -> None:
        """Interface to Config Controller"""
        if self.selected_node is None:
            return
        node = self.selected_node
        node_title = node.button.text
        node_config = self.pipeline_controller.get_node_config(node_title)
        self.config_controller.show_node_configs(node_title, node_config)

    def btn_toggle_config_state(self, *args) -> None:
        """Toggle show all or only user-defined configurations"""
        self.pipeline_controller.toggle_config_state()
        self.show_node_configs()

    def btn_config_press(self, btn, *args) -> None:
        """This method is called when a node config is clicked

        Args:
            btn (_type_): the config that is clicked on
        """
        self.clear_selected_configs()
        # set new selected config
        config = btn.parent
        config.select_color = CONFIG_COLOR_SELECTED
        self.all_selected_configs.add(config)

    def btn_node_press(self, btn, *args) -> None:
        """This method is called when a pipeline node is clicked

        Args:
            btn (_type_): the node that is clicked on
        """
        self.clear_selected_nodes()
        # set new selected node
        node = btn.parent
        node.select_color = NODE_COLOR_SELECTED
        self.all_selected_nodes.add(node)
        self.selected_node = node
        self.show_node_configs()

    def btn_load_file(self, btn, *args) -> None:
        file_dialog = FileLoadDialog(select=self.load_file, cancel=self.cancel_load)
        file_dialog.setup(root_path=ROOT_PATH, path=CURR_PATH, filters=FILE_FILTERS)
        self._file_dialog = Popup(
            title="Load File", content=file_dialog, size_hint=(0.75, 0.75)
        )
        self._file_dialog.open()

    def btn_save_file(self, btn, *args) -> None:
        print("btn_save_file: not implemented yet")

    def btn_quit(self, btn, *args) -> None:
        # todo: ask user to confirm quit / save changes
        self.stop()

    def cancel_load(self) -> None:
        self._file_dialog.dismiss()

    # Playback controls
    def btn_play_stop(self) -> None:
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
    def load_file(self, path: str, file_paths: List[str]) -> None:
        """Method to load PeekingDuck pipeline configuration yaml file

        Args:
            path (str): Path containing the pipeline configuration yaml file
            file_paths (List[str]): Selected yaml file(s)
        """
        self._file_dialog.dismiss()
        print(f"path={path}, file_paths={file_paths}")
        the_path = file_paths[0]  # only want first file
        # decode project info
        tokens = the_path.split("/")
        self.filename = tokens[-1]
        self.set_output_header(self.filename)
        self.project_info.directory = os.path.dirname(the_path)
        self.project_info.filename = self.filename
        self.pipeline_model = PipelineModel(the_path)
        self.pipeline_controller.set_pipeline_model(self.pipeline_model)
        self.pipeline_controller.draw_nodes()

    #####################
    # Pipeline processing
    #####################
    def btn_node_move_up_press(self, *args) -> None:
        if self.all_selected_nodes:
            for node in self.all_selected_nodes:
                break  # only handle one node for now
            self.pipeline_controller.move_node(node, "up")
            self.btn_node_move_up_held = Clock.schedule_once(
                self.btn_node_move_up_press, BUTTON_DELAY
            )

    def btn_node_move_up_release(self, *args) -> None:
        if self.btn_node_move_up_held:
            self.btn_node_move_up_held.cancel()

    def btn_node_move_down_press(self, *args) -> None:
        if self.all_selected_nodes:
            for node in self.all_selected_nodes:
                break  # only handle one node for now
            self.pipeline_controller.move_node(node, "down")
            self.btn_node_move_down_held = Clock.schedule_once(
                self.btn_node_move_down_press, BUTTON_DELAY
            )

    def btn_node_move_down_release(self, *args) -> None:
        if self.btn_node_move_down_held:
            self.btn_node_move_down_held.cancel()

    def btn_verify_pipeline(self, *args) -> None:
        res = self.pipeline_controller.verify_pipeline()
        print(res)


if __name__ == "__main__":
    PeekingDuckGuiApp().run()
