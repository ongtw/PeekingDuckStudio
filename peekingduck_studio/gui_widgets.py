#
# Kivy Widget Classes
#
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.metrics import Metrics
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen
from kivy.uix.slider import Slider
from kivy.uix.spinner import SpinnerOption
from typing import List
from functools import partial
from peekingduck_studio.colors import (
    BLACK,
    BLUE,
    DARK_BLUE,
    DARK_SLATE_GRAY,
    DEEP_SKY_BLUE,
    LIGHT_SKY_BLUE,
    MIDNIGHT_BLUE,
    SILVER,
    WHITE,
)
from peekingduck_studio.gui_utils import get_node_color, make_logger

NODE_HEIGHT: int = 80
NODE_PADDING: int = 5
NODE_TEXT_SCALE: float = 0.25
SINGLE_TAP_DELAY: float = 0.25
TOOLTIP_DELAY: float = 2.0

logger = make_logger(__name__)


class ButtonLabel(ButtonBehavior, Label):
    # experimental
    callback_press = ObjectProperty(None)
    callback_release = ObjectProperty(None)


class FileLoadDialog(FloatLayout):
    select = ObjectProperty(None)  # map to file/path selected method
    cancel = ObjectProperty(None)  # map to cancel method

    def setup(self, root_path: str, path: str, filters: List[str]):
        # dotw: weak ref, cannot use python `with ... as file_chooser:` context manager syntax
        file_chooser = self.ids["id_file_chooser"]
        file_chooser.rootpath = root_path
        file_chooser.path = path
        file_chooser.filters = filters


class FileSaveDialog(FloatLayout):
    save = ObjectProperty(None)
    cancel = ObjectProperty(None)
    text_input = ObjectProperty(None)

    def setup(self, root_path: str, path: str, filters: List[str], filename: str):
        self.text_input.text = filename
        # dotw: weakref, cannot use python with statement
        file_chooser = self.ids["id_file_chooser"]
        file_chooser.rootpath = root_path
        file_chooser.path = path
        file_chooser.filters = filters


class MsgBox:
    """Custom dialog box class for messages
    MsgBoxPopup defined in peekingduckstudio.kv file
    Todo: mimic MFC MsgBox behavior
    """

    def __init__(
        self,
        title: str,
        msg: str,
        btn_close_text: str,
        font_name: str = "Arial",
        font_size: int = 15,
    ) -> None:
        self._title = title
        self._msg = msg
        self._btn_close_text = btn_close_text
        self._font_name = font_name
        self._font_size = font_size * Metrics.dp

    def show(self) -> None:
        popup = Factory.MsgBoxPopup()
        popup.title = self._title
        popup.font_name = self._font_name
        popup.font_size = self._font_size
        popup.message.text = self._msg
        popup.close_button.text = self._btn_close_text
        popup.open()


class Node(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    select_color = ListProperty([0, 0, 0, 0])
    node_number = ObjectProperty("0")  # shown as index in GUI
    node_text = ObjectProperty("")
    node_height = NumericProperty(NODE_HEIGHT * Metrics.dp)
    # don't use 'uid' as Kivy seems to use it internally, so will conflict!
    node_id = StringProperty("")
    callback_double_tap = ObjectProperty(None)
    scheduled_press = None

    def __init__(self, uid: str, node_title: str, node_idx: int, **kwargs):
        super().__init__(**kwargs)
        self.node_id = uid
        self.node_text = node_title
        self.node_number = str(node_idx)
        self.bkgd_color = get_node_color(node_title)
        if "height" in kwargs:
            height = int(kwargs["height"])
            self.update(height)
            # logger.debug(f"height={height}, node_height={self.node_height}")

    def update(self, height: int):
        self.node_height = height * Metrics.dp

    def on_touch_down(self, touch):
        # logger.debug(f"button={touch.button}")
        if self.collide_point(*touch.pos):
            if touch.is_double_tap:
                logger.debug(f"double-tap text={self.node_text}, button={touch.button}")
                if self.scheduled_press:
                    logger.debug("cancel scheduled_press")
                    self.scheduled_press.cancel()
                    self.scheduled_press = None
                if self.callback_double_tap:
                    self.callback_double_tap(self)
            else:
                logger.debug(f"text={self.node_text}, button={touch.button}")
                # dotw: Need to schedule do_press in order to properly differentiate
                # between single and double tap. If double tap occurs, then cancel
                # the single tap do_press callback.
                if self.callback_press:
                    self.scheduled_press = Clock.schedule_once(
                        partial(self.do_press, touch), SINGLE_TAP_DELAY
                    )
            return True  # stop event from percolating
        return super().on_touch_down(touch)

    # def on_touch_up(self, touch):
    #     logger.debug(f"button={touch.button}")
    #     return super().on_touch_up(touch)

    def do_press(self, touch, delay):
        logger.debug(f"touch={touch}, button={touch.button}, delay={delay}")
        if touch.button == "left":
            self.callback_press(self)


class NodeConfig(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    select_color = ListProperty([0, 0, 0, 0])
    config_key = StringProperty("key")
    config_type = StringProperty("nonetype")
    config_value = ObjectProperty("value")
    config_set = BooleanProperty(False)
    config_readonly = BooleanProperty(False)
    node_height = NumericProperty(NODE_HEIGHT * Metrics.dp)
    has_tooltip = BooleanProperty(False)
    callback_double_tap = ObjectProperty(None)
    scheduled_press = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "height" in kwargs:
            height = int(kwargs["height"])
            self.update(height)
            # logger.debug(f"height={height}, config_height={self.node_height}")
        # experimental: not sure if having tooltip is better
        if self.has_tooltip:
            self.enable_tooltip()

    def update(self, height: int):
        self.node_height = height * Metrics.dp

    def on_touch_down(self, touch):
        logger.debug(f"button={touch.button}")
        if touch.is_double_tap:
            if self.collide_point(*touch.pos):
                logger.debug(f"double-tap key:{self.config_key}")
                if self.scheduled_press:
                    logger.debug("cancel scheduled_press")
                    self.scheduled_press.cancel()
                    self.scheduled_press = None
                if self.callback_double_tap:
                    self.callback_double_tap(self)
                return True  # stop event from percolating
        return super().on_touch_down(touch)

    # def on_touch_up(self, touch):
    #     logger.debug(f"button={touch.button}")
    #     return super().on_touch_up(touch)

    def debug(self):
        logger.debug(f"key={self.config_key} height={self.height}")
        for i, child in enumerate(self.children):
            logger.debug(f" child: {type(child)} height={child.height}")
            if i == 0:
                for grandkid in child.children:
                    logger.debug(f"  child: {type(grandkid)} height={grandkid.height}")

    def enable_tooltip(self):
        Window.bind(mouse_pos=self.on_mouse_pos)
        self.tooltip = Tooltip()

    def on_mouse_pos(self, win, pos):
        if not self.get_root_window():
            # logger.debug("get_root_window is False")
            return
        Clock.unschedule(self.show_tooltip)  # cancel on moving cursor
        self.close_tooltip()  # close if it's opened
        if self.collide_point(*self.to_widget(*pos)):
            # logger.debug(f"  mouse over: {self.text}")
            self.tooltip.pos = pos
            self.tooltip.text = f"{self.config_key}: {self.config_value}"
            Clock.schedule_once(self.show_tooltip, TOOLTIP_DELAY)

    def close_tooltip(self, *args):
        Window.remove_widget(self.tooltip)

    def show_tooltip(self, *args):
        logger.debug(f"show_tooltip: args={args}")
        Window.add_widget(self.tooltip)


class Output(GridLayout):
    def install_progress_bar(self) -> None:
        grid = self.ids["grid"]
        widget_zoom = grid.children[0]
        widget_frame = grid.children[1]
        widget_speed = grid.children[3]
        grid.clear_widgets()
        grid.add_widget(widget_speed)
        progress = ProgressBar(size_hint_x=0.6)
        grid.add_widget(progress)
        self.ids["progress"] = progress  # set kivy id in python code
        grid.add_widget(widget_frame)
        grid.add_widget(widget_zoom)
        # for i, child in enumerate(grid.children):
        #     logger.debug(f"{i} {child}")

    def install_slider(self) -> None:
        grid = self.ids["grid"]
        widget_zoom = grid.children[0]
        widget_frame = grid.children[1]
        widget_speed = grid.children[3]
        grid.clear_widgets()
        grid.add_widget(widget_speed)
        slider = Slider(size_hint_x=0.6)
        grid.add_widget(slider)
        self.ids["slider"] = slider  # set kivy id in python code
        grid.add_widget(widget_frame)
        grid.add_widget(widget_zoom)
        # for i, child in enumerate(grid.children):
        #     logger.debug(f"{i} {child}")

    # def on_touch_down(self, touch):
    # if self.collide_point(*touch.pos):
    #     logger.debug("touch inside me")
    # self.touch_down_callback(touch)


class ProjectInfo(GridLayout):
    directory = StringProperty("")
    filename = StringProperty("")
    callback_tap = ObjectProperty(None)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.callback_tap:
                logger.debug(f"self.callback_tap: {self.callback_tap}")
                self.callback_tap(self)
        return super().on_touch_down(touch)


class Button3D(Button):
    # cannot assign colors in kv file, need to create properties here
    btn_height = NumericProperty(40 * Metrics.dp)
    color_normal = ListProperty(list(DEEP_SKY_BLUE))
    color_pressed = ListProperty(list(DEEP_SKY_BLUE))
    color_shadow = ListProperty(list(MIDNIGHT_BLUE))
    has_tooltip = BooleanProperty(False)
    tooltip_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.has_tooltip:
            self.enable_tooltip()

    def enable_tooltip(self):
        Window.bind(mouse_pos=self.on_mouse_pos)
        self.tooltip = Tooltip()

    def on_mouse_pos(self, win, pos):
        if not self.get_root_window():
            # logger.debug("get_root_window is False")
            return
        Clock.unschedule(self.show_tooltip)  # cancel on moving cursor
        self.close_tooltip()  # close if it's opened
        if self.collide_point(*self.to_widget(*pos)):
            # logger.debug(f"  mouse over: {self.text}")
            self.tooltip.pos = pos
            self.tooltip.text = f"{self.tooltip_text}"
            Clock.schedule_once(self.show_tooltip, TOOLTIP_DELAY)

    def close_tooltip(self, *args):
        Window.remove_widget(self.tooltip)

    def show_tooltip(self, *args):
        Window.add_widget(self.tooltip)


class RoundedButton(Button):
    # cannot assign colors in kv file, need to create properties here
    btn_height = NumericProperty(40 * Metrics.dp)
    color_normal = ListProperty(list(DEEP_SKY_BLUE))
    color_pressed = ListProperty(list(LIGHT_SKY_BLUE))


class ScreenPipeline(Screen):
    pass


class ScreenPlayback(Screen):
    pass


class SpinnerOptionCustom(SpinnerOption):
    bkgd_color = ListProperty([0, 0, 1, 1])
    node_height = NumericProperty(NODE_HEIGHT * Metrics.dp)

    def update(self, height: int):
        self.node_height = height * Metrics.dp


class Tooltip(Label):
    pass
