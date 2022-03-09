#
# PeekingDuck GUI
# by DOTW 2022-03-06
#

# Globals
ROOT_PATH = "/Users/dotw"
CURR_PATH = "/Users/dotw/src/ongtw/PeekingDuck"
FILE_FILTERS = ["*.yml"]
WIN_WIDTH = 1024
WIN_HEIGHT = 768
COPYRIGHT_MSG = """
PeekingDuckGUI
By DOTW
(C) 2022

A GUI application to manage 
PeekingDuck's pipeline nodes
"""

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
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from PipelineGraphics import PipelineGraphics

Builder.load_file("PipelineGraphics.kv")


def show_alert(msg: str, title: str):
    popup = Popup(
        title=title,
        content=Label(text=msg, halign="center"),
        size_hint=(None, None),
        size=(400, 300),
    )
    popup.open()


class FileLoadDialog(FloatLayout):
    # map to load_file() and cancel_file() methods
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)

    def setup(self, path: str, filters: List[str]):
        # dotw: weakref, cannot use python with statement
        self.ids["id_file_chooser"].rootpath = ROOT_PATH
        self.ids["id_file_chooser"].path = path
        self.ids["id_file_chooser"].filters = filters


class PeekingDuckGUI(BoxLayout):
    #####################
    # Object vars
    #####################
    pipeline_file_path: str = None
    pipeline: Dict = None
    pipeline_nodes: List = None

    #####################
    # GUI callbacks
    #####################
    def btn_about(self):
        show_alert(title="About PeekingDuck", msg=COPYRIGHT_MSG)

    def btn_load_file(self):
        file_dialog = FileLoadDialog(load=self.load_file, cancel=self.cancel_load)
        file_dialog.setup(path=CURR_PATH, filters=FILE_FILTERS)
        self._file_dialog = Popup(
            title="Load File", content=file_dialog, size_hint=(0.9, 0.9)
        )
        self._file_dialog.open()

    def btn_save_file(self):
        pass

    def cancel_load(self):
        self._file_dialog.dismiss()

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
        print(f"self.pipeline: {self.pipeline_file_path}")
        print(self.pipeline)
        # decode top-level pipeline nodes
        self.pipeline_nodes = self.pipeline["nodes"]
        # for i, node in enumerate(self.pipeline_nodes):
        #     print(i, ":", node)
        # setup scroll viewport for pipeline nodes layout
        pipeline_scroll_view = self.pipeline_scrollview
        pipeline_scroll_view.clear_widgets()
        # prevent BoxLayout from adapting to parent ScrollView height
        pipeline_layout = BoxLayout(orientation="vertical", size_hint=(1, None))
        pipeline_scroll_view.add_widget(pipeline_layout)
        pipeline_layout.bind(minimum_height=pipeline_layout.setter("height"))
        # send to graphics drawing object
        self.pipeline_graphics = PipelineGraphics(
            pipeline=self.pipeline_nodes, layout_view=pipeline_layout
        )
        self.pipeline_graphics.draw()

        # # this works, very good
        # for i in range(20):
        #     pipeline_layout.add_widget(MyWidget(i % 2 is 1))


class MyWidget(BoxLayout):
    def __init__(self, odd, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint = (1, None)
        self.odd = odd
        self.padding = 10
        for i in range(3):
            ll = Label(text=f"I am Label\nLine\nNumber {i + 1}")
            ll.size = ll.texture_size
            self.add_widget(ll)
        self.bind(pos=self.format_background_color)
        self.bind(size=self.format_background_color)

    def format_background_color(self, *args):
        with self.canvas.before:
            if self.odd:
                Color(0.0, 0.0, 0.2, mode="rgb")
            else:
                Color(0.0, 0.0, 0.8, mode="rgb")
            Rectangle(pos=self.pos, size=self.size)
        print(f"BoxLayout.size={self.size}")
        sum_height = 0
        for child in self.children:
            print(f"text={child.text}")
            print(f"size={child.size}, texture_size={child.texture_size}")
            sum_height += child.texture_size[1]
        print(f"sum_height={sum_height}")
        self.height = sum_height


class PeekingDuckGUIApp(App):
    def build(self):
        self.pkd = PeekingDuckGUI()
        self.pkd.app = self
        return self.pkd


if __name__ == "__main__":
    PeekingDuckGUIApp().run()
