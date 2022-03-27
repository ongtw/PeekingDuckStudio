#
# Kivy Widget Classes
#
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen

from typing import List


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

    def on_touch_down(self, touch):
        if touch.is_double_tap:
            if self.collide_point(*touch.pos):
                print(f"Node.on_touch_down: double-tap {self.node_text}")
                print(touch)
                return True  # stop event from percolating
        return super().on_touch_down(touch)


class NodeConfig(GridLayout):
    bkgd_color = ListProperty([0, 0, 1, 1])
    select_color = ListProperty([0, 0, 0, 0])
    config_key = ObjectProperty("key")
    config_value = ObjectProperty("value")
    config_set = BooleanProperty(False)
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
    pass
    # def on_touch_down(self, touch):
    # if self.collide_point(*touch.pos):
    #     print("Output: touch inside me")
    # self.touch_down_callback(touch)


class ProjectInfo(GridLayout):
    directory = StringProperty("")
    filename = StringProperty("")


class RoundedButton(BoxLayout):
    color_bkgd = ListProperty([0, 0, 0, 0])
    color_normal = ListProperty([65 / 255, 105 / 255, 225 / 255, 1])
    color_pressed = ListProperty([30 / 255, 144 / 255, 1, 1])
    color_separator = ListProperty([0, 0, 0, 1])
    color_text = ListProperty([1, 1, 1, 1])


class ScreenPipeline(Screen):
    pass


class ScreenPlayback(Screen):
    pass
