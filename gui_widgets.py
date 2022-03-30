#
# Kivy Widget Classes
#
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.metrics import Metrics
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen
from kivy.uix.slider import Slider
from pygame import mixer

from typing import List
from gui_utils import get_node_color, NAVY

SINGLE_TAP_DELAY = 0.25


class ButtonLabel(ButtonBehavior, Label):
    # experimental
    callback_press = ObjectProperty(None)
    callback_release = ObjectProperty(None)


class FileLoadDialog(FloatLayout):
    select = ObjectProperty(None)  # map to file/path selected method
    cancel = ObjectProperty(None)  # map to cancel method

    def setup(self, root_path: str, path: str, filters: List[str]):
        # dotw: weakref, cannot use python with statement
        file_chooser = self.ids["id_file_chooser"]
        file_chooser.rootpath = root_path
        file_chooser.path = path
        file_chooser.filters = filters


class Node(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    select_color = ListProperty([0, 0, 0, 0])
    node_number = ObjectProperty("0")  # shown as index in GUI
    node_text = ObjectProperty("")
    # don't use 'uid' as Kivy seems to use it internally, so will conflict!
    node_id = StringProperty("")
    callback_double_tap = ObjectProperty(None)
    # callback_press = ObjectProperty(None)
    scheduled_press = None

    def __init__(self, uid: str, node_title: str, node_idx: int, **kwargs):
        super().__init__(**kwargs)
        self.node_id = uid
        self.node_text = node_title
        self.node_number = str(node_idx)
        self.bkgd_color = get_node_color(node_title)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.is_double_tap:
                print(f"Node.on_touch_down: double-tap {self.node_text}")
                print("touch:", touch)
                if self.scheduled_press:
                    print("cancelling scheduled press")
                    self.scheduled_press.cancel()
                    self.scheduled_press = None
                if self.callback_double_tap:
                    self.callback_double_tap(self)
            else:
                print(f"Node.on_touch_down: tap {self.node_text}")
                # dotw: Need to schedule do_press in order to properly differentiate
                # between single and double tap. If double tap occurs, then cancel
                # the single tap do_press callback.
                if self.callback_press:
                    self.scheduled_press = Clock.schedule_once(
                        self.do_press, SINGLE_TAP_DELAY
                    )
            return True  # stop event from percolating
        return super().on_touch_down(touch)

    def do_press(self, *args):
        print("do_press")
        self.callback_press(self)


class NodeConfig(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    select_color = ListProperty([0, 0, 0, 0])
    config_key = StringProperty("key")
    config_type = StringProperty("nonetype")
    config_value = ObjectProperty("value")
    config_set = BooleanProperty(False)
    config_readonly = BooleanProperty(False)
    callback_double_tap = ObjectProperty(None)

    def on_touch_down(self, touch):
        if touch.is_double_tap:
            if self.collide_point(*touch.pos):
                print(f"NodeConfig.on_touch_down: double-tap {self.config_key}")
                if self.callback_double_tap:
                    self.callback_double_tap(self)
                return True  # stop event from percolating
        return super().on_touch_down(touch)


class Output(GridLayout):
    def install_progress_bar(self) -> None:
        grid = self.ids["grid"]
        left_label = grid.children[0]  # this is zoom
        right_label = grid.children[2]  # this is speed
        grid.clear_widgets()
        grid.add_widget(right_label)
        progress = ProgressBar(size_hint_x=0.6)
        grid.add_widget(progress)
        self.ids["progress"] = progress  # set kivy id in python code
        grid.add_widget(left_label)
        # for i, child in enumerate(grid.children):
        #     print(f"{i} {child}")

    def install_slider(self) -> None:
        grid = self.ids["grid"]
        left_label = grid.children[0]  # this is zoom
        right_label = grid.children[2]  # this is speed
        grid.clear_widgets()
        grid.add_widget(right_label)
        slider = Slider(size_hint_x=0.6)
        grid.add_widget(slider)
        self.ids["slider"] = slider  # set kivy id in python code
        grid.add_widget(left_label)
        # for i, child in enumerate(grid.children):
        #     print(f"{i} {child}")

    # def on_touch_down(self, touch):
    # if self.collide_point(*touch.pos):
    #     print("Output: touch inside me")
    # self.touch_down_callback(touch)


class ProjectInfo(GridLayout):
    directory = StringProperty("")
    filename = StringProperty("")
    callback_tap = ObjectProperty(None)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.callback_tap:
                print("Yes")
                self.callback_tap(self)
        return super().on_touch_down(touch)


class RoundedButton(BoxLayout):
    color_bkgd = ListProperty([0, 0, 0, 0])
    color_normal = ListProperty([65 / 255, 105 / 255, 225 / 255, 1])  # royal blue
    color_pressed = ListProperty([30 / 255, 144 / 255, 1, 1])  # dodger blue
    color_separator = ListProperty([0, 0, 0, 1])
    color_text = ListProperty([1, 1, 1, 1])
    text = StringProperty(None)


class ScreenPipeline(Screen):
    pass


class ScreenPlayback(Screen):
    pass


class MsgBox:
    """Custom dialog box class for messages"""

    def __init__(self, title: str, msg: str, btn_close_text: str) -> None:
        self._title = title
        self._msg = msg
        self._btn_close_text = btn_close_text

    def show(self) -> None:
        popup = Factory.MsgBoxPopup()
        popup.title = self._title
        popup.message.text = self._msg
        popup.close_button.text = self._btn_close_text
        popup.open()


class Sounds:
    def __init__(self) -> None:
        self._sound_on = False
        self._mixer = mixer
        self._mixer.init()
        self.load_sounds()

    @property
    def sound_on(self) -> bool:
        return self._sound_on

    @sound_on.setter
    def sound_on(self, flag: bool) -> None:
        self._sound_on = flag

    def load_sounds(self):
        self.snd_add_node = mixer.Sound("sounds/message-ringtone-21467.mp3")
        self.snd_delete_node = mixer.Sound("sounds/chew-21768.mp3")
        self.snd_error = mixer.Sound("sounds/slash-21834.mp3")
