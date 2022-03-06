#
# PeekingDuck GUI
# by DOTW 2022-03-06
#

# change window size from 800x600 to 1024x768 (must be before other kivy modules)
from kivy.config import Config
Config.set("graphics", "width", "1024")
Config.set("graphics", "height", "768")
Config.set("graphics", "minimum_width", "1024")
Config.set("graphics", "minimum_height", "768")
Config.set("graphics", "resizable", False)

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder

class PeekingDuckGUIApp(App):
    def build(self):
        self.title = "PeekingDuck GUI"

if __name__ == "__main__":
    PeekingDuckGUIApp().run()
