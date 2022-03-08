#
# PeekingDuck GUI
# by DOTW 2022-03-06
#

from typing import Dict, List

ROOT_PATH = "/Users/dotw"


# change window size from 800x600 to 1024x768 (must be before other kivy modules)
from tkinter.filedialog import LoadFileDialog
from kivy.config import Config

Config.set("graphics", "width", "1024")
Config.set("graphics", "height", "768")
Config.set("graphics", "minimum_width", "1024")
Config.set("graphics", "minimum_height", "768")
Config.set("graphics", "resizable", False)

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup


def show_alert(msg: str, title: str):
    popup = Popup(
        title=title, content=Label(text=msg), size_hint=(None, None), size=(400, 400)
    )
    popup.open()


class FileLoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)

    def setup(self, path: str, filters: List[str]):
        # dotw: weakref, cannot use python with statement
        self.ids["id_file_chooser"].rootpath = ROOT_PATH
        self.ids["id_file_chooser"].path = path
        self.ids["id_file_chooser"].filters = filters


class PeekingDuckGUI(BoxLayout):
    #####################
    # GUI callbacks
    #####################
    def btn_about(self):
        show_alert("PeekingDuckGUI", "About PeekingDuck")

    def btn_load_file(self):
        file_dialog = FileLoadDialog(load=self.do_load, cancel=self.do_cancel)
        file_dialog.setup(path="/Users/dotw/src/ongtw", filters=["*.yml"])
        self._popup = Popup(
            title="Load File", content=file_dialog, size_hint=(0.9, 0.9)
        )
        self._popup.open()

    def btn_save_file(self):
        pass

    def do_cancel(self):
        self._popup.dismiss()

    def do_load(self, path: str, filepath: str):
        print(f"path={path}, filepath={filepath}")
        self._popup.dismiss()


class PeekingDuckGUIApp(App):
    def build(self):
        self.pkd = PeekingDuckGUI()
        self.pkd.app = self
        return self.pkd

    def btn(self):
        show_alert("PeekingDuckApp", "AppDialog")


if __name__ == "__main__":
    PeekingDuckGUIApp().run()
