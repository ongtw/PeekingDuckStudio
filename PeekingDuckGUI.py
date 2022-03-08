#
# PeekingDuck GUI
# by DOTW 2022-03-06
#

# Globals
ROOT_PATH = "/Users/dotw"
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
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup


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

    #####################
    # GUI callbacks
    #####################
    def btn_about(self):
        show_alert(title="About PeekingDuck", msg=COPYRIGHT_MSG)

    def btn_load_file(self):
        file_dialog = FileLoadDialog(load=self.load_file, cancel=self.cancel_load)
        file_dialog.setup(path="/Users/dotw/src/ongtw", filters=["*.yml"])
        self._popup = Popup(
            title="Load File", content=file_dialog, size_hint=(0.9, 0.9)
        )
        self._popup.open()

    def btn_save_file(self):
        pass

    def cancel_load(self):
        self._popup.dismiss()

    #####################
    # File operations
    #####################
    def load_file(self, path: str, file_paths: List[str]):
        print(f"path={path}, file_paths={file_paths}")
        self._popup.dismiss()
        self.pipeline_file_path = file_paths[0]  # only want first file
        with open(self.pipeline_file_path) as file:
            self.pipeline = yaml.safe_load(file)
        print(f"self.pipeline: {self.pipeline_file_path}")
        print(self.pipeline)


class PeekingDuckGUIApp(App):
    def build(self):
        self.pkd = PeekingDuckGUI()
        self.pkd.app = self
        return self.pkd


if __name__ == "__main__":
    PeekingDuckGUIApp().run()
