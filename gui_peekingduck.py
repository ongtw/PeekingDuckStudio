#
# PeekingDuck GUI
# DOTW, (C) 2022
#

# Todo list:
# - support custom nodes definition
# - edit config: click yellow button to restore default
# - edit config: disable input/output, read-only
# - edit config: value range check
# - edit config: value type check
# - edit config: present type-based options when setting values
# - output: playback speed?
# - export output as video file
# - pipeline: new
# - pipeline: save
# - pipeline: error check
# - pipeline: multiple select(?)
# - anomalous pipelines:
#   * duplicate nodes
#   * multiple nodes of same type (any allowed combo?)
# - undo/redo
# - app config: default folder, etc.

##########
# Globals
##########
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
PLAYBACK_DELAY = 0.01

##########
# Imports
##########
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

from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager

# from kivy.uix.spinner import Spinner

import os
from re import A
from typing import Dict, List
from gui_widgets import (
    FileLoadDialog,
    Node,
    ScreenPipeline,
    ScreenPlayback,
)
from config_parser import NodeConfigParser
from config_controller import ConfigController
from output_controller import OutputController
from pipeline_controller import PipelineController
from pipeline_model import ModelPipeline


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
        self.selected_node: Node = None
        self.all_selected_nodes = set()
        self.all_selected_configs = set()
        self.setup_output()
        self.setup_key_widgets()
        self.setup_gui_working_vars()

        self.config_parser = NodeConfigParser()
        self.config_controller = ConfigController(
            self.config_parser, self.pipeline_view
        )
        self.output_controller = OutputController(self.config_parser, self.pkd_view)
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
        self.pkd_view = screen.ids["pkd_view"]

    def setup_key_widgets(self) -> None:
        screen = self.screen_pipeline
        self.project_info = screen.ids["project_info"]
        self.pipeline_view = screen.ids["pipeline_view"]

    def setup_gui_working_vars(self):
        # pre-declare working vars to avoid code crashing on var not found errors
        self.btn_node_move_down_held = None
        self.btn_node_move_up_held = None

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
        self.screen_playback.bind(on_enter=self.auto_play_once)

    def auto_play_once(self, *args) -> None:
        """Autostart playback upon entering playback screen"""
        print(f"auto_play: args={args}")
        self.screen_playback.unbind(on_enter=self.auto_play_once)
        if self.pipeline_model:
            self.output_controller.play_stop()  # auto play

    def show_node_configs(self) -> None:
        """Interface to Config Controller"""
        if self.selected_node is None:
            return
        node = self.selected_node
        node_title = node.button.text
        self.config_controller.show_node_configs(node_title)

    def btn_node_type_select(self, instance, *args) -> None:
        """Set config header node type after node type spinner selection

        Args:
            instance (Button): the selected node type button
        """
        node_type = instance.text
        print(f"btn_node_type_select: {node_type}")
        instance.parent.node_type = node_type
        self.config_controller.set_node_names(node_type)
        # todo: change current model node? or only change after node name selected?

    def btn_node_name_select(self, instance, *args) -> None:
        """Set config header node name after node name spinner selection

        Args:
            instance (Button): the selected node name button
        """
        print(f"btn_node_name_select: {instance.text}")
        instance.parent.node_name = instance.text
        self.config_controller.show_node_configs()
        node = self.selected_node
        node_num = int(node.node_number)
        node_title = node.button.text
        new_node_title = self.config_controller.get_config_header_node_title()
        print(f"  selected_node {node_num}:{node_title} change to {new_node_title}")
        # for new node, there are zero user config (makes life easier)
        new_node_config = [{"None": "No Config"}]
        node_idx = node_num - 1  # index for old new to be replaced with new node
        self.pipeline_model.node_replace(node_idx, new_node_title, new_node_config)
        self.pipeline_controller.draw_nodes()
        self.clear_selected_nodes()
        # NB: need to clear all cached data about the old node...
        # todo: change current model node

    def btn_toggle_config_state(self, *args) -> None:
        """Toggle show all or only user-defined configurations"""
        self.pipeline_controller.toggle_config_state()
        self.show_node_configs()

    def btn_config_press(self, btn: Button, *args) -> None:
        """This method is called when a node config is clicked

        Args:
            btn (Button): the config that is clicked on
        """
        self.clear_selected_configs()
        # set new selected config
        print(f"btn_config_press: btn.text={btn.text}")
        floatlayout = btn.parent
        config = floatlayout.parent
        config.select_color = CONFIG_COLOR_SELECTED
        self.all_selected_configs.add(config)

    def btn_node_press(self, node: Node, *args) -> None:
        """This method is called when a pipeline node is clicked

        Args:
            node (Node): the node that is clicked on
        """
        self.clear_selected_nodes()
        # set new selected node
        node.select_color = NODE_COLOR_SELECTED
        self.all_selected_nodes.add(node)
        self.selected_node = node
        self.show_node_configs()

    def btn_new_file(self, btn) -> None:
        print("btn_new_file: not implemented yet")

    def btn_load_file(self, btn) -> None:
        file_dialog = FileLoadDialog(select=self.load_file, cancel=self.cancel_load)
        file_dialog.setup(root_path=ROOT_PATH, path=CURR_PATH, filters=FILE_FILTERS)
        self._file_dialog = Popup(
            title="Load File", content=file_dialog, size_hint=(0.75, 0.75)
        )
        self._file_dialog.open()

    def btn_save_file(self, btn) -> None:
        print("btn_save_file: not implemented yet")

    def btn_about(self, btn) -> None:
        print("btn_about: not implemented yet")

    def btn_quit(self, btn) -> None:
        # todo: ask user to confirm quit / save changes
        self.stop()

    def cancel_load(self) -> None:
        self._file_dialog.dismiss()

    # Playback controls
    def btn_play_stop_press(self, btn, *args) -> None:
        if self.pipeline_model is None:
            return
        tag = btn.parent.tag
        print(f"btn_play_stop_press: tag={tag}")
        self.output_controller.play_stop()

    def btn_forward_press(self, *args) -> None:
        if self.output_controller.forward_one_frame():
            self.btn_forward_held = Clock.schedule_once(
                self.btn_forward_press, PLAYBACK_DELAY
            )

    def btn_forward_release(self, *args) -> None:
        if hasattr(self, "btn_forward_held"):
            self.btn_forward_held.cancel()

    def btn_backward_press(self, *args) -> None:
        if self.output_controller.backward_one_frame():
            self.btn_backward_held = Clock.schedule_once(
                self.btn_backward_press, PLAYBACK_DELAY
            )

    def btn_backward_release(self, *args) -> None:
        if hasattr(self, "btn_backward_held"):
            self.btn_backward_held.cancel()

    def btn_first_frame(self, *args) -> None:
        self.output_controller.goto_first_frame()

    def btn_last_frame(self, *args) -> None:
        self.output_controller.goto_last_frame()

    def btn_zoom_in(self, *args) -> None:
        self.output_controller.zoom_in()

    def btn_zoom_out(self, *args) -> None:
        self.output_controller.zoom_out()

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
        self.project_info.directory = os.path.dirname(the_path)
        self.project_info.filename = self.filename
        self.pipeline_model = ModelPipeline(the_path)
        self.config_controller.set_pipeline_model(self.pipeline_model)
        self.output_controller.set_pipeline_model(self.pipeline_model)
        self.output_controller.set_output_header(self.filename)
        self.pipeline_controller.set_pipeline_model(self.pipeline_model)
        self.pipeline_controller.draw_nodes()

    #####################
    # Pipeline processing
    #####################
    def btn_node_add(self, instance) -> None:
        if self.pipeline_model is None:
            return
        print("btn_node_add")
        if self.selected_node:
            idx = int(self.selected_node.node_number) - 1
        else:
            idx = self.pipeline_model.num_nodes
        self.pipeline_controller.add_node(idx)
        self.selected_node = None

    def btn_node_delete(self, instance) -> None:
        if self.pipeline_model is None:
            return
        print("btn_node_delete")
        if self.selected_node:
            idx = int(self.selected_node.node_number) - 1
            self.pipeline_controller.delete_node(idx)
            self.selected_node = None
        else:
            print("nothing selected to delete")

    def btn_node_move_up_press(self, *args) -> None:
        if self.all_selected_nodes:
            for node in self.all_selected_nodes:
                break  # only handle one node for now
            # NB: moving will invalidate current selected node due to clearing and
            # recreating widgets
            new_node = self.pipeline_controller.move_node(node, "up")
            self.selected_node = new_node
            self.btn_node_move_up_held = Clock.schedule_once(
                self.btn_node_move_up_press, BUTTON_DELAY
            )

    def btn_node_move_up_release(self, *args) -> None:
        if self.btn_node_move_up_held:
            self.btn_node_move_up_held.cancel()
        node = self.selected_node
        node_num = int(node.node_number)
        node_title = node.button.text
        print(f"btn_node_move_up_release: selected={node_num} {node_title}")

    def btn_node_move_down_press(self, *args) -> None:
        if self.all_selected_nodes:
            for node in self.all_selected_nodes:
                break  # only handle one node for now
            # NB: moving will invalidate current selected node due to clearing and
            # recreating widgets
            new_node = self.pipeline_controller.move_node(node, "down")
            self.selected_node = new_node
            self.btn_node_move_down_held = Clock.schedule_once(
                self.btn_node_move_down_press, BUTTON_DELAY
            )

    def btn_node_move_down_release(self, *args) -> None:
        if self.btn_node_move_down_held:
            self.btn_node_move_down_held.cancel()
        node = self.selected_node
        node_num = int(node.node_number)
        node_title = node.button.text
        print(f"btn_node_move_down_release: selected={node_num} {node_title}")

    def btn_verify_pipeline(self, *args) -> None:
        res = self.pipeline_controller.verify_pipeline()
        print(res)


if __name__ == "__main__":
    PeekingDuckGuiApp().run()
