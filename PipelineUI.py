from kivy.app import App
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import Metrics
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

COLOR_LIGHTGRAY = Color(192 / 255, 192 / 255, 192 / 255, 1, mode="rgba")
COLOR_GRAY = Color(128 / 255, 128 / 255, 128 / 255, 1, mode="rgba")
COLOR_RED = Color(1, 0, 0, 1, mode="rgba")
COLOR_GREEN = Color(0, 1, 0, 1, mode="rgba")
COLOR_BLUE = Color(0, 0, 1, 1, mode="rgba")


class NodeNameButton(Button):
    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self.font_size = 12 * Metrics.sp
        self.size_hint = 0.8, 0.8
        self.pos_hint = {"center-x": 0.5, "center-y": 0.5}
        self.color = [1, 1, 1, 1]
        self.background_color = [0, 0, 0, 0]
        self.text = name
        self.bind(pos=self.redraw)
        self.bind(size=self.redraw)
        self.bind(on_press=self.redraw)
        self.bind(on_release=self.redraw)

    def redraw(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == "normal":
                Color(1, 0, 0, 0.5, mode="rgba")
            else:
                Color(0, 0, 1, 0.5, mode="rgba")
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10 * Metrics.dp])
        pass


class PkdPipelineNodeName(BoxLayout):
    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint = (1, None)
        self.pos_hint = {"center-x": 0.5}
        self.button = NodeNameButton(name=name)
        self.add_widget(self.button)
        self.bind(pos=self.redraw)
        self.bind(size=self.redraw)

    def redraw(self, *args):
        # self.canvas.before.clear()
        # with self.canvas.before:
        #     if self.button.state == "normal":
        #         Color(1, 0, 0, 1, mode="rgba")
        #     else:
        #         Color(0, 0, 1, 1, mode="rgba")
        #     RoundedRectangle(pos=self.pos, size=self.size, radius=[10 * Metrics.dp])
        pass


class PkdPipelineNodeConfig(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint = (1, None)


class PkdPipelineNode(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.orientation = "vertical"
        # self.size_hint = (1, None)

        self.node_name = PkdPipelineNodeName(name="NodeName")
        self.add_widget(self.node_name)


class mainApp(App):
    def build(self):
        self.root = PkdPipelineNode()
        return self.root


if __name__ == "__main__":
    mainApp().run()
