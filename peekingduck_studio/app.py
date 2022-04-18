#
# PeekingDuck Studio
# DOTW, (C) 2022
#

#
# Bug list:
# - runtime no exception nor stderr, but stdout has error msg
#   e.g. move dabble.bbox_count to last node and run pipeline
#   -> no error dialog displayed so user doesn't know what happened
# - weights download sends output to stderr, code thinks it's an error
#
# Features:
# - add performance evaluation support
#
# Quirk list:
# - resize window: long text exceeding button width
# - resize window: filechooser not scaling up
#
# Todo list:
# - allow user to change current pipeline working directory
#   (now cwd is changed only upon loading an existing pipeline file)
#   if has custom nodes, load them and update accordingly
# - support user custom nodes directory, e.g. `src/my_nodes`
#   (now default is `src/custom_nodes`)
# - alert if user saves custom node pipeline to directory without custom nodes
# - alert if no output.screen (also some way to track progress if no output?)
# - feedback icon for PeekingDuck running in background?
# - edit config error check: value range
# - edit config error check: value type
# - edit config: present type-based options when setting values
# - output: playback speed?
# - export output as video file
# - confirmation before any operation that destroys unsaved pipeline
# - file save: confirm before overwriting existing file
# - user preferences/app config: default folder, etc.
# - pipeline: error check
# - pipeline: multiple select (for move / delete)
# - pipeline: long-click drag to reposition node
# - anomalous pipelines:
#   * duplicate nodes
#   * multiple nodes of same type (any allowed combo?)
# - undo/redo
# - convert unicode glyphs to images (for cross platform consistency?)
# - garbage collect old video frames (need to?)

##########
# Imports
##########
from kivy.config import Config
from kivy.metrics import Metrics

# change window size from 800x600 to 1024x768 (must be done before importing other kivy modules)
WIN_WIDTH: int = 1280
WIN_HEIGHT: int = 800
Config.set("kivy", "window_icon", "pkds_mac.png")
Config.set("graphics", "width", WIN_WIDTH)
Config.set("graphics", "height", WIN_HEIGHT)
Config.set("graphics", "minimum_width", WIN_WIDTH)
Config.set("graphics", "minimum_height", WIN_HEIGHT)
Config.set("graphics", "resizable", True)

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.widget import Widget

from typing import List
import json
import os
from pathlib import Path
import yaml
from peekingduck_studio.gui_utils import (
    NODE_COLOR_SELECTED,
    NODE_COLOR_CLEAR,
    CONFIG_COLOR_SELECTED,
    CONFIG_COLOR_CLEAR,
    shake_widget,
    make_logger,
)
from peekingduck_studio.gui_widgets import (
    FileLoadDialog,
    FileSaveDialog,
    MsgBox,
    Node,
    ScreenPipeline,
    ScreenPlayback,
)
from peekingduck_studio.config_controller import ConfigController
from peekingduck_studio.config_parser import NodeConfigParser
from peekingduck_studio.output_controller import OutputController
from peekingduck_studio.pipeline_controller import PipelineController
from peekingduck_studio.model_pipeline import ModelPipeline

##########
# Globals
##########
ROOT_PATH = "/"
# temp: for convenience
# CURR_PATH = "/Users/dotw/src/pkd"
CURR_PATH = str(Path.home())
DIR_FILTERS = [""]
FILE_FILTERS = ["*yml"]
BUTTON_DELAY: float = 0.2
PLAYBACK_DELAY: float = 0.01

logger = make_logger(__name__)
logger.info(f"root_path={ROOT_PATH}, curr_path={CURR_PATH}")


class PeekingDuckStudioApp(App):
    def build(self):
        """
        Main Kivy application entry point
        """
        self.title = "PeekingDuck Studio v1.0b (Internal Preview)"
        # self.icon = "pkds_mac.png"

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

        Window.bind(on_resize=self.on_window_resize)

        return sm

    # Window events (experimental)
    def on_window_resize(self, win, width, height):
        # recalculate height for GUI node/node config
        increase = height / WIN_HEIGHT - 1.0
        new_node_height = int(80 * (1.0 + increase * 0.3))
        # logger.debug(f"x={width}, y={height}, new_node_height={new_node_height}")
        self.pipeline_controller.node_height = new_node_height
        self.config_controller.node_height = new_node_height
        self.output_controller.node_height = new_node_height
        self.font_size = max(16, int(15 * Window.height / WIN_HEIGHT)) * Metrics.sp

    # Keyboard events (experimental codes)
    def to_window(self, x, y, initial=True, relative=False):
        # Need this for keyboard events to work properly (quick hack?)
        return x, y

    def keyboard_closed(self) -> None:
        self._keyboard.unbind(on_key_down=self.on_keyboard_down)
        self._keyboard = None

    def on_keyboard_down(self, keyboard, keycode, text, modifiers) -> bool:
        logger.debug(f"keycode: {keycode} pressed, text={text}, modifiers={modifiers}")
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
        self.font_size = 15 * Metrics.sp

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
        logger.debug(f"press: '{btn.text}' tag={btn.tag}")

    def btn_release(self, btn) -> None:
        logger.debug(f"release: '{btn.text}' tag={btn.tag}")

    # Buttons: Specific
    # Screen transitions
    def btn_goto_screen_pipeline(self, *args) -> None:
        """Transition right to pipeline screen"""
        self.sm.transition.direction = "right"
        self.sm.current = "screen_pipeline"

    def btn_goto_screen_playback(self, *args) -> None:
        if self.pipeline_model:
            """Transition left to playback screen"""
            self.sm.transition.direction = "left"
            self.sm.current = "screen_playback"
            self.screen_playback.bind(on_enter=self.auto_play_once)
        else:
            msgbox = MsgBox(
                "Alert",
                "No pipeline to run. Please create one first.",
                "Ok",
                font_size=self.font_size,
            )
            msgbox.show()

    def auto_play_once(self, *args) -> None:
        """Autostart playback upon entering playback screen"""
        logger.debug(f"args={args}")
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
        logger.debug(f"btn.text={btn.text} config_key={config_key}")
        config.select_color = CONFIG_COLOR_SELECTED
        self.all_selected_configs.add(config)

    def btn_config_set_default_press(self, btn: Button) -> None:
        """Called when node config reset is clicked

        Args:
            btn (Button): the reset button
        """
        config = btn.parent.parent.parent
        config_key = config.config_key
        logger.debug(f"btn.text={btn.text} config_key={config_key}")
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
        if self.selected_node is None:
            return
        node_type = instance.text
        logger.debug(f"node_type: {node_type}")
        # update spinner to show correct name
        instance.parent.node_type = node_type
        self.config_controller.set_node_names(node_type)
        self._replace_current_selected_pipeline_node()

    def btn_node_name_select(self, instance, *args) -> None:
        """Set config header node name after node name spinner selection

        Args:
            instance (Button): the selected node name button
        """
        if self.selected_node is None:
            return
        node_name = instance.text
        logger.debug(f"node_name: {node_name}")
        # update spinner to show correct name
        instance.parent.node_name = node_name
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
        # debug
        old_node_title = gui_node.button.text
        logger.debug(f"replace {node_num}:{old_node_title} with {new_node_title}")
        # end debug
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
        logger.debug(f"node_text: {node.node_text}")
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
    def btn_about(self, btn) -> None:
        """Show About this Program dialog box

        Args:
            btn (Button): the About button
        """
        title = "About PeekingDuck Studio"
        msg = """
PeekingDuck Studio v1.0b (Internal Preview)
by David Ong Tat-Wee
(C) 2022

PeekingDuck Atelier:
- pipeline editor
- playback viewer

A multiple-nights/weekends project using Python and Kivy
        """
        msgbox = MsgBox(title, msg, "Ok", font_size=self.font_size)
        msgbox.show()

    def btn_quit(self, btn) -> None:
        """Stop and quit PeekingDuck Studio application

        Args:
            btn (Button): the Quit button
        """
        # todo: ask user to confirm quit / save changes
        self.stop()

    def btn_load_file(self, btn) -> None:
        """Show FileChooser for user to load a pipeline file

        Args:
            btn (Buton): the Load button
        """
        file_dialog = FileLoadDialog(
            select=self.load_file, cancel=self.cancel_file_dialog
        )
        logger.debug(f"CURR_PATH={CURR_PATH}")
        file_dialog.setup(root_path=ROOT_PATH, path=CURR_PATH, filters=FILE_FILTERS)
        self._file_dialog = Popup(
            title="Load File", content=file_dialog, size_hint=(0.75, 0.75)
        )
        self._file_dialog.open()

    def btn_new_file(self, btn) -> None:
        """Start a new pipeline

        Args:
            btn (Button): the New button
        """
        logger.debug("new pipeline")
        self.pipeline_model = ModelPipeline()
        self.filename = self.pipeline_model.filename
        self.project_info.filename = self.filename
        self._do_begin_pipeline()

    def btn_save_file(self, btn) -> None:
        if self.pipeline_model:
            file_dialog = FileSaveDialog(
                save=self.save_file, cancel=self.cancel_file_dialog
            )
            file_dialog.setup(
                root_path=ROOT_PATH,
                path=CURR_PATH,
                filters=FILE_FILTERS,
                filename=self.filename,
            )
            self._file_dialog = Popup(
                title="Load File", content=file_dialog, size_hint=(0.75, 0.75)
            )
            self._file_dialog.open()
        else:
            msgbox = MsgBox(
                "File Save Alert",
                "No pipeline to save. Please create one first.",
                "Ok",
                font_size=self.font_size,
            )
            msgbox.show()

    def btn_sound_on_off(self, btn) -> None:
        """Toggle sound on/off

        Args:
            btn (Button): the Sound On/Off button
        """
        parent = btn.parent
        logger.debug(f"tag={parent.tag}")

    def btn_yaml(self, btn) -> None:
        """Show pipeline's yaml source code

        Args:
            btn (_type_): the Yaml button
        """

        def split_long_line(yaml_line: str, max_len: int = 80, indent: int = 4) -> str:
            """Helper method to split a long YAML line, if it contains a comma.
            Even though 'width=80' is set in yaml.dump, it does not work for long string
            parameters, which is split into two lines here.
            """
            if len(yaml_line) <= max_len:
                return yaml_line
            text = []
            if "," in yaml_line:
                tokens = yaml_line.split(",")
                is_comma = True
            elif "{" in yaml_line and "}" in yaml_line:
                tokens = yaml_line.split("{")
                is_comma = False
            else:
                return yaml_line  # nothing to split on
            curr_str = ""
            for tok in tokens:
                tok = tok.strip()
                if tok.endswith("}") and "{" not in tok:
                    tok = tok[:-1]
                if tok:
                    if len(curr_str) + len(tok) <= max_len:
                        curr_str = f"{curr_str},{tok}" if curr_str else tok
                    else:
                        text.append(f"{curr_str}{',' if is_comma else ''}")
                        curr_str = f"{' '*indent}{tok}"
                else:
                    # empty tok means orig line ends with a ","
                    curr_str = f"{curr_str},"
            if curr_str:
                text.append(curr_str)
            return text

        def split_long_yaml_lines(yaml_str: str) -> str:
            """Helper method to process a multiline YAML dump string and split long lines

            Args:
                yaml_str (str): the YAML dump string

            Returns:
                str: the reformatted string, if any
            """
            if "\n" not in yaml_str:
                return yaml_str
            text = []
            tokens = yaml_str.split("\n")
            for tok in tokens:
                if tok:
                    logger.debug(f" > tok={len(tok)}, {tok}")
                    x = split_long_line(tok)
                    logger.debug(f"tok_split={x}")
                    text.extend(x) if isinstance(x, list) else text.append(x)
            return "\n".join(text)

        if self.pipeline_model:
            json_str = self.pipeline_model.get_string_representation()
            logger.debug(f"json_str: {json_str}")
            dd = json.loads(json_str)
            logger.debug(f"dd: {type(dd)} {dd}")
            yaml_str = yaml.dump(dd, default_flow_style=None, width=60)
            logger.debug(f"yaml_str: {yaml_str}")
            # yaml_clean = split_long_yaml_lines(yaml_str)
            yaml_clean = yaml_str
            logger.debug(f"yaml_clean: {yaml_clean}")

            msgbox = MsgBox(
                "Yaml Source Code",
                yaml_clean,
                "Ok",
                font_name="Courier New",
                font_size=self.font_size,
            )
            msgbox.show()
        else:
            msgbox = MsgBox(
                "Alert",
                "No pipeline to display. Please create one first.",
                "Ok",
                font_size=self.font_size,
            )
            msgbox.show()

    def cancel_file_dialog(self) -> None:
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
        logger.debug(f"tag={btn.tag}")
        self.output_controller.replay()

    def btn_play_stop_press(self, btn) -> None:
        if self.pipeline_model is None:
            return
        logger.debug(f"tag={btn.tag}")
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
    # logger.debug(f"app touch: {touch.x}, {touch.y}")
    # if self.pkd_output.collide_point(*touch.pos):
    #     self.clear_selected_configs()
    #     self.clear_selected_nodes()
    # else:
    #     pass

    #####################
    # File operations
    #####################
    def load_file(self, instance: Widget, file_paths: List[str], *args) -> None:
        """Load selected PeekingDuck pipeline configuration yaml file.
        Called when user selects a file and clicks Select button in FileLoadDialog.

        Technote: there are spurious callbacks when selection is a folder and not a
                  file! (Kivy bug??) That's why need to check file ends with ".yml"
                  to ensure it's not a folder.
                  A more robust (but slower) way is to use Path to check for file.

        Args:
            path (str): Path containing the pipeline configuration yaml file
            file_paths (List[str]): Selected yaml file(s) (default 1)
        """
        global CURR_PATH
        # logger.debug(f"instance={instance}, file_paths={file_paths}")
        if not file_paths:
            logger.debug(f"empty file_paths={file_paths}")
            return
        the_path = file_paths[0]  # only want first file
        if not the_path.endswith(".yml"):
            logger.debug(f"bogus submit: file={the_path}")
            return
        self._file_dialog.dismiss()
        # decode project info
        logger.debug(f"path={the_path}")
        tokens = the_path.split("/")
        self.filename = tokens[-1]
        CURR_PATH = os.path.dirname(the_path)  # set as last visited path
        self.project_info.directory = CURR_PATH
        self.project_info.filename = self.filename
        self.pipeline_model = ModelPipeline(the_path)
        self.config_parser.set_pipeline_model(self.pipeline_model)
        self._do_begin_pipeline()

    def _do_begin_pipeline(self) -> None:
        """Called by both New and Load pipeline operations.
        Does housekeeping tasks.
        """
        self.config_controller.set_pipeline_model(self.pipeline_model)
        self.output_controller.set_pipeline_model(self.pipeline_model)
        self.pipeline_controller.set_pipeline_model(self.pipeline_model)
        self.pipeline_controller.draw_nodes()

    def save_file(self, path: str, file_path: str) -> None:
        self._file_dialog.dismiss()
        full_path = file_path if file_path.startswith(path) else f"{path}/{file_path}"
        logger.debug(f"path: {path}, file_path: {file_path}")
        logger.debug(f"full_path: {full_path}")
        json_str = self.pipeline_model.get_string_representation()
        clean_json_str = self.clean_json(json_str)
        dd = json.loads(clean_json_str)
        with open(full_path, "w") as outfile:
            yaml.dump(dd, outfile, default_flow_style=None)
        msgbox = MsgBox(
            "Alert", f"File saved to {full_path}", "Ok", font_size=self.font_size
        )
        msgbox.show()

    #####################
    # Pipeline processing
    #####################
    def btn_node_add(self, instance) -> None:
        if self.pipeline_model is None:
            return
        logger.debug("add node")
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

    def clock_do_anim_node(self, *args) -> None:
        self.anim_function(self.selected_node)

    def clock_do_select_node(self, *args) -> None:
        self.btn_node_press(self.selected_node)

    def btn_node_delete(self, instance) -> None:
        if self.pipeline_model is None:
            return
        logger.debug("delete node")
        if self.selected_node:
            shake_widget(self.selected_node)
            Clock.schedule_once(self.clock_do_delete_node, 1.0)
        else:
            logger.debug("nothing selected to delete")

    def clock_do_delete_node(self, *args) -> None:
        idx = int(self.selected_node.node_number) - 1
        self.pipeline_controller.delete_node(idx)
        self.clear_selected_nodes()

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
            logger.debug(f"selected={node_num} {node_title}")

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
            logger.debug(f"selected={node_num} {node_title}")

    def btn_verify_pipeline(self, *args) -> None:
        res = self.pipeline_controller.verify_pipeline()
        logger.debug(res)


if __name__ == "__main__":
    PeekingDuckStudioApp().run()
