#
# PeekingDuck GUI
# DOTW, (C) 2022
#

# Bug list:
# - runtime no exception nor stderr, but stdout has error msg
#   e.g. move dabble.bbox_count to last node and run pipeline
#   -> no error dialog displayed so user doesn't know what happened
# Todo list:
# - support custom nodes definition
# - edit config: value range check
# - edit config: value type check
# - edit config: present type-based options when setting values
# - output: playback speed?
# - export output as video file
# - pipeline: save
# - pipeline: error check
# - pipeline: multiple select(?)
# - anomalous pipelines:
#   * duplicate nodes
#   * multiple nodes of same type (any allowed combo?)
# - garbage collect old video frames (need to?)
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

import os
from typing import List
from gui_utils import (
    NODE_COLOR_SELECTED,
    NODE_COLOR_CLEAR,
    CONFIG_COLOR_SELECTED,
    CONFIG_COLOR_CLEAR,
    shake_widget,
)
from gui_widgets import (
    FileLoadDialog,
    MsgBox,
    Node,
    ScreenPipeline,
    ScreenPlayback,
    Sounds,
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
        self.setup_key_widgets()
        self.setup_gui_working_vars()
        self.sounds = Sounds()

        self.config_parser = NodeConfigParser()
        self.config_controller = ConfigController(
            self.config_parser, self.pipeline_view, self.sounds
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

    # Keyboard events (experimental codes)
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
    def setup_key_widgets(self) -> None:
        """Init important widgets within self"""
        playback_screen = self.screen_playback
        self.pkd_view = playback_screen.ids["pkd_view"]
        screen = self.screen_pipeline
        self.project_info = screen.ids["project_info"]
        self.project_info.callback_tap = self.tap_project_info
        self.pipeline_view = screen.ids["pipeline_view"]

    def setup_gui_working_vars(self):
        """Pre-declare working vars to avoid crashing on var not found errors"""
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

    def _mark_selected_node(self, node: Node) -> None:
        """Internal management method to select GUI node

        Args:
            node (Node): the selected GUI node
        """
        self.selected_node = node
        self.all_selected_nodes.add(node)
        node.select_color = NODE_COLOR_SELECTED

    # App GUI Event Callbacks
    # Buttons: generic dummy callbacks
    def btn_press(self, btn) -> None:
        parent = btn.parent
        print(f"btn_press: '{btn.text}' tag={parent.tag}")

    def btn_release(self, btn) -> None:
        parent = btn.parent
        print(f"btn_release: '{btn.text}' tag={parent.tag}")

    # Buttons: Specific
    # Screen transitions
    def btn_goto_screen_pipeline(self, *args) -> None:
        """Transition right to pipeline screen"""
        self.sm.transition.direction = "right"
        self.sm.current = "screen_pipeline"

    def btn_goto_screen_playback(self, *args) -> None:
        """Transition left to playback screen"""
        self.sm.transition.direction = "left"
        self.sm.current = "screen_playback"
        self.screen_playback.bind(on_enter=self.auto_play_once)

    def auto_play_once(self, *args) -> None:
        """Autostart playback upon entering playback screen"""
        print(f"auto_play: args={args}")
        self.screen_playback.unbind(on_enter=self.auto_play_once)
        if self.pipeline_model:
            self.output_controller.play_stop()  # auto play

    def btn_config_press(self, btn: Button) -> None:
        """This method is called when a node config is clicked

        Args:
            btn (Button): the config that is clicked on
        """
        self.clear_selected_configs()
        # set new selected config
        floatlayout = btn.parent
        config = floatlayout.parent
        config_key = config.config_key
        print(f"btn_config_press: btn.text={btn.text} config_key={config_key}")
        config.select_color = CONFIG_COLOR_SELECTED
        self.all_selected_configs.add(config)

    def btn_config_set_default_press(self, btn: Button) -> None:
        """Called when node config reset is clicked

        Args:
            btn (Button): the reset button
        """
        # print(f"btn_config_press: btn.text={btn.text}")
        config = btn.parent.parent.parent
        config_key = config.config_key
        print(f"btn_config_press: btn.text={btn.text} config_key={config_key}")
        self.config_controller.reset_node_config_to_default(config_key)

    def btn_toggle_config_state(self, *args) -> None:
        """Toggle show all or only user-defined configurations"""
        self.pipeline_controller.toggle_config_state()
        self.do_show_node_configs()

    def do_show_node_configs(self) -> None:
        """Interface to Config Controller"""
        if self.selected_node is None:
            return
        node = self.selected_node
        self.config_controller.show_node_configs(node.node_id)

    def btn_node_type_select(self, instance, *args) -> None:
        """Set config header node type after node type spinner selection

        Args:
            instance (Button): the selected node type button
        """
        node_type = instance.text
        print(f"btn_node_type_select: {node_type}")
        # update spinner to show correct name
        instance.parent.node_type = node_type
        self.config_controller.set_node_names(node_type)
        self._replace_current_selected_pipeline_node()

    def btn_node_name_select(self, instance, *args) -> None:
        """Set config header node name after node name spinner selection

        Args:
            instance (Button): the selected node name button
        """
        print(f"btn_node_name_select: {instance.text}")
        # update spinner to show correct name
        instance.parent.node_name = instance.text
        # refresh configuration view with node defaults
        self.config_controller.show_node_configs()
        self._replace_current_selected_pipeline_node()

    def _replace_current_selected_pipeline_node(self):
        """Internal method to replace the current selected pipeline node.
        Called when either node type or node name is changed.
        """
        gui_node = self.selected_node
        if not gui_node:
            return  # no node currently selected
        node_num = int(gui_node.node_number)
        node_idx = node_num - 1  # index of node to replace
        new_node_title = self.config_controller.get_config_header_node_title()
        # old_node_title = gui_node.button.text
        # print(f"  replace {node_num}:{old_node_title} with {new_node_title}")
        gui_node = self.pipeline_controller.replace_with_new_node(
            node_idx, new_node_title
        )
        self.clear_selected_nodes()
        # trigger callback to select new node
        self.btn_node_press(gui_node)

    def btn_node_press(self, node: Node) -> None:
        """This method is called when a pipeline node is clicked

        Args:
            node (Node): the node that is clicked on
        """
        # print(f"btn_node_press: {node.node_text}")
        self.clear_selected_nodes()
        self._mark_selected_node(node)
        self.pipeline_controller.focus_on_node(node)
        self.do_show_node_configs()

    def tap_project_info(self, instance) -> None:
        """Callback to clear current node selection (quick hack)"""
        if self.selected_node:
            self.clear_selected_nodes()

    #
    # Main app buttons
    #
    def btn_new_file(self, btn) -> None:
        """Start a new pipeline

        Args:
            btn (Button): the New button
        """
        print("btn_new_file")
        self.filename = "new_pipeline.yml"
        self.project_info.filename = self.filename
        self.pipeline_model = ModelPipeline()
        self._do_begin_pipeline()

    def btn_load_file(self, btn) -> None:
        """Show FileChooser for user to load a pipeline file

        Args:
            btn (Buton): the Load button
        """
        file_dialog = FileLoadDialog(select=self.load_file, cancel=self.cancel_load)
        file_dialog.setup(root_path=ROOT_PATH, path=CURR_PATH, filters=FILE_FILTERS)
        self._file_dialog = Popup(
            title="Load File", content=file_dialog, size_hint=(0.75, 0.75)
        )
        self._file_dialog.open()

    def btn_save_file(self, btn) -> None:
        print("btn_save_file: not implemented yet")

    def btn_sound_on_off(self, btn) -> None:
        """Toggle sound on/off

        Args:
            btn (Button): the Sound On/Off button
        """
        parent = btn.parent
        print(f"btn_sound_on_off: tag={parent.tag}")
        # self._sound_on = not self._sound_on
        # parent.tag = "on" if self._sound_on else "off"
        self.sounds.sound_on = not self.sounds.sound_on
        parent.tag = "on" if self.sounds.sound_on else "off"

    def btn_about(self, btn) -> None:
        """Show About this Program dialog box

        Args:
            btn (Button): the About button
        """
        title = "About PeekingDuck GUI"
        msg = """
PeekingDuck GUI
by David Ong Tat-Wee
(C) 2022

A pipeline editor and playback viewer for PeekingDuck
        """
        msgbox = MsgBox(title, msg, "Ok")
        msgbox.show()

    def btn_quit(self, btn) -> None:
        """Stop and quit PeekingDuck GUI application

        Args:
            btn (Button): the Quit button
        """
        # todo: ask user to confirm quit / save changes
        self.stop()

    def cancel_load(self) -> None:
        """Called when user clicks 'Cancel' in Load File dialog
        Will close the Load File dialog.
        """
        self._file_dialog.dismiss()

    #
    # Playback controls
    #
    def btn_replay_press(self, btn) -> None:
        if self.pipeline_model is None:
            return
        tag = btn.parent.tag
        print(f"btn_replay_press: tag={tag}")
        self.output_controller.replay()

    def btn_play_stop_press(self, btn) -> None:
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
        if not file_paths:
            return
        the_path = file_paths[0]  # only want first file
        # decode project info
        tokens = the_path.split("/")
        self.filename = tokens[-1]
        self.project_info.directory = os.path.dirname(the_path)
        self.project_info.filename = self.filename
        self.pipeline_model = ModelPipeline(the_path)
        self._do_begin_pipeline()

    def _do_begin_pipeline(self) -> None:
        """Called by both New and Load pipeline operations.
        Does housekeeping tasks.
        """
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
        gui_node = self.pipeline_controller.add_node(idx)
        self.selected_node = None
        btn = gui_node.button
        # trigger callback to select new node
        self.btn_node_press(gui_node)
        self.anim_function = shake_widget
        Clock.schedule_once(self.clock_do_anim_node, 0.2)
        if self.sounds.sound_on:
            self.sounds.snd_add_node.play()

    def clock_do_anim_node(self, *args) -> None:
        self.anim_function(self.selected_node)

    def clock_do_select_node(self, *args) -> None:
        self.btn_node_press(self.selected_node)

    def btn_node_delete(self, instance) -> None:
        if self.pipeline_model is None:
            return
        print("btn_node_delete")
        if self.selected_node:
            shake_widget(self.selected_node)
            if self.sounds.sound_on:
                self.sounds.snd_delete_node.play()
            Clock.schedule_once(self.clock_do_delete_node, 1.0)
        else:
            print("nothing selected to delete")

    def clock_do_delete_node(self, *args) -> None:
        idx = int(self.selected_node.node_number) - 1
        self.pipeline_controller.delete_node(idx)
        self.selected_node = None

    def btn_node_move_up_press(self, *args) -> None:
        if self.all_selected_nodes:
            for node in self.all_selected_nodes:
                break  # only handle one node for now
            # NB: moving will invalidate current selected node due to clearing and
            # recreating widgets
            new_node = self.pipeline_controller.move_node(node, "up")
            self._mark_selected_node(new_node)
            self.btn_node_move_up_held = Clock.schedule_once(
                self.btn_node_move_up_press, BUTTON_DELAY
            )

    def btn_node_move_up_release(self, *args) -> None:
        if self.btn_node_move_up_held:
            self.btn_node_move_up_held.cancel()
        if self.selected_node:
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
            self._mark_selected_node(new_node)
            self.btn_node_move_down_held = Clock.schedule_once(
                self.btn_node_move_down_press, BUTTON_DELAY
            )

    def btn_node_move_down_release(self, *args) -> None:
        if self.btn_node_move_down_held:
            self.btn_node_move_down_held.cancel()
        if self.selected_node:
            node = self.selected_node
            node_num = int(node.node_number)
            node_title = node.button.text
            print(f"btn_node_move_down_release: selected={node_num} {node_title}")

    def btn_verify_pipeline(self, *args) -> None:
        res = self.pipeline_controller.verify_pipeline()
        print(res)


if __name__ == "__main__":
    PeekingDuckGuiApp().run()
