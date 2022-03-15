from typing import List, Tuple

from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import Metrics
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout


NODE_RGB_COLOR = {
    "augment": (153, 153, 153),
    "dabble": (120, 117, 188),
    "draw": (240, 115, 81),
    "input": (240, 224, 156),
    "model": (177, 230, 241),
    "output": (160, 112, 97),
}


class PipelineGraphics:
    def __init__(self, pipeline: List, layout_view: BoxLayout) -> None:
        self.pipeline = pipeline
        self.view = layout_view
        self.pipeline_nodes = []

    def draw(self):
        for i, node in enumerate(self.pipeline):
            if isinstance(node, str):
                title_text = node
                config_text = "No config"
            else:  # must be dict
                title_text = list(node.keys())[0]
                config_dd = node[title_text]
                config_items = []
                for k, v in config_dd.items():
                    kv_text = f"{k} : {v}\n"
                    config_items.append(kv_text)
                config_text = "".join(config_items)

            self.view.add_widget(
                MyWidget(
                    i % 2 is 1,
                    title=title_text,
                    config=config_text,
                    padding=[10, 10, 10, 10],
                )
            )
        # for i in range(20):
        #     self.view.add_widget(
        #         MyWidget(i % 2 is 1, title="Title", config="ConfigText")
        #     )
        # for i, node in enumerate(self.pipeline):
        #     print(i, "->", node, " ", type(node))
        #     pipeline_node = PipelineNode(node)
        #     self.pipeline_nodes.append(pipeline_node)
        #     self.view.add_widget(pipeline_node)


class PipelineNode(BoxLayout):
    def __init__(self, node, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint = (1, None)
        self.padding = 10 * Metrics.dp
        self._draw(node)
        self.bind(pos=self.update_rrect)
        self.bind(size=self.update_rrect)

    def update_rrect(self, *args):
        with self.canvas.before:
            Color(1, 1, 1, 1, mode="rgba")  # white
            Rectangle(pos=self.pos, size=self.size)
            # self.rrect = RoundedRectangle(
            #     pos=self.pos, size=self.size, radius=[8 * Metrics.dp]
            # )
            # self.rrect = Rectangle(pos=self.pos, size=self.size)
        print("--- update_rrect ---")
        print(f"BoxLayout.size={self.size}")
        print(f"#children={len(self.children)}")
        sum_height = 0
        for child in self.children:
            print(f"child={child.text}")
            print(f"  size={child.size}, texture_size={child.texture_size}")
            sum_height += child.texture_size[1]
        print(f"sum_height={sum_height}")
        self.height = sum_height
        print("--- end ---")
        # self.rrect.pos = self.pos
        # self.rrect.size = self.size

    def _draw(self, node):
        self.node = node
        # decode node title and config
        if isinstance(node, str):
            title_text = node
            config_text = "No config"
        else:  # must be dict
            title_text = list(node.keys())[0]
            config_dd = node[title_text]
            config_items = []
            for k, v in config_dd.items():
                kv_text = f"{k} : {v}\n"
                config_items.append(kv_text)
            config_text = "".join(config_items)
        #  draw node title and config
        lbl_title = Label(text=title_text)
        lbl_title.size = lbl_title.texture_size
        self.add_widget(lbl_title)
        lbl_config = Label(text=config_text)
        lbl_config.size = lbl_config.texture_size
        self.add_widget(lbl_config)
        print(f"_draw: add {title_text}")
        # self.title.text = title_text
        # self.config.text = config_text


class HorzLine(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.size_hint = (1, None)
        # self.height = 10 * Metrics.dp
        self.bind(pos=self.update_self)
        self.bind(size=self.update_self)

    def update_self(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, mode="rgb")
            Rectangle(pos=self.pos, size=(self.width, 1 * Metrics.dp))


class MyWidget(BoxLayout):
    def __init__(self, odd, title, config, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint = (0.9, None)
        self.pos_hint = {"center_x": 0.5, "top": 0.9}
        self.odd = odd
        # self.padding = [10, 10, 10, 10]

        # determine node type
        toks = title.split(".")
        self.node_type = toks[0]
        self.node_name = toks[1]
        rgb = NODE_RGB_COLOR[self.node_type]
        self.rgb = tuple(h / 255.0 for h in rgb)
        print(f"node_type={self.node_type}, rgb={self.rgb}")

        ll = Label(
            text=f"{self.node_type} -> {self.node_name}",
            color=(0, 0, 0, 1),
            padding=(10, 10),
        )
        ll.size = ll.texture_size
        self.add_widget(ll)

        llc = Label(text=config, color=(0, 0, 0, 1), padding=(10, 10))
        llc.size = llc.texture_size
        self.add_widget(llc)

        self.bind(pos=self.format_background_color)
        self.bind(size=self.format_background_color)

    def format_background_color(self, *args):
        print("--- format background ---")
        self.canvas.before.clear()
        print(f"self.rgb={self.rgb}")
        with self.canvas.before:
            Color(self.rgb[0], self.rgb[1], self.rgb[2], mode="rgb")
            RoundedRectangle(pos=self.pos, size=self.size, radius=[8 * Metrics.dp])

        print(f"BoxLayout.size={self.size}")
        sum_height = 0
        for child in self.children:
            print(f"sum_height={sum_height}")
            if isinstance(child, Label):
                print(f"text={child.text}")
                print(
                    f"pos={child.pos}, size={child.size}, texture_size={child.texture_size}"
                )
                sum_height += child.texture_size[1]
            else:
                print(f"{type(child)}: pos={child.pos}, size={child.size}")
                sum_height += child.size[1]
        print(f"sum_height={sum_height}")
        self.height = sum_height
