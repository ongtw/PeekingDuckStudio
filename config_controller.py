#
# PeekingDuck GUI Controller for Node Config
#

from typing import List
from gui_widgets import NodeConfig
from gui_utils import get_node_type, NODE_RGBA_COLOR, BLACK, WHITE, NAVY
from config_parser import NodeConfigParser
from pipeline_model import PipelineModel
from kivy.clock import Clock
from kivy.uix.textinput import TextInput
import ast

NODE_TEXT_INPUT_DELAY = 0.5  # half second
NODE_CONFIG_RESERVED_KEYS = {"MODEL_NODES", "weights", "weights_parent_dir"}


class ConfigController:
    def __init__(self, config_parser, pipeline_view) -> None:
        self.pipeline_view = pipeline_view
        self.config_header = pipeline_view.ids["pipeline_config_header"]
        self.pipeline_config = pipeline_view.ids["pipeline_config"]
        self.config_layout = self.pipeline_config.ids["config_layout"]
        self.config_parser: NodeConfigParser = config_parser
        self.overlay = None

    def set_pipeline_model(self, pipeline_model) -> None:
        self.pipeline_model: PipelineModel = pipeline_model

    def clear_node_configs(self) -> None:
        self.config_layout.clear_widgets()
        self.set_node_config_header("Node Config", color=NAVY, font_color=WHITE)

    def config_double_tap(self, instance, *args) -> None:
        """Move scrollview so that config instance is fully visible

        Args:
            instance (Widget): the config instance to show onscreen

        todo: if config is fully visible on-screen, don't scroll
        """
        print(f"double-tap instance {type(instance)}")
        print(f"  pos={instance.pos} size={instance.size}")
        parent = self.config_layout.parent
        # print(
        #     f"config_layout: pos={self.config_layout.pos} size={self.config_layout.size}"
        # )
        # print(f"parent: {type(parent)}")
        # print(f"  pos={parent.pos} size={parent.size}")

        # don't scroll if boxlayout.height < scrollview.height
        # 'coz nodes will flush towards bottom of scrollview and look weird
        if self.config_layout.height > parent.height:
            self.pipeline_config.scroll_to(instance)

        if self.overlay:
            print("overlay present, exiting")
            return

        overlay = instance.the_overlay
        key = instance.config_key
        val = instance.config_value
        print(f"key: {key}, val: {val}, overlay: {overlay.pos} {overlay.size}")
        text_input = TextInput(
            multiline=False,
            pos=overlay.pos,
            size=overlay.size,
            text=val,
            halign="center",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            size_hint=(1, 1),
        )
        text_input.bind(on_text_validate=self.ti_on_enter)
        text_input.bind(focus=self.ti_on_focus)
        # to simulate valign="center" since it's not available for TextInput
        text_input.padding = [
            6,
            text_input.height / 2.0 - (text_input.line_height / 2.0),
            6,
            6,
        ]
        overlay.add_widget(text_input)
        self.overlay = overlay
        # dotw: trick to get text input overlay working...
        #       doing a TextInput(..., focus=True) does not work 'coz widget will get
        #       focus but cannot type, so let overlay widget refresh itself, then
        #       trigger a focus on the TextInput widget.
        Clock.schedule_once(self.ti_do_focus, NODE_TEXT_INPUT_DELAY)

    def ti_do_focus(self, *args):
        print(f"do_focus: args={args}")
        self.overlay.children[0].focus = True

    def ti_on_enter(self, instance, *args):
        print(f"on_enter: instance={instance} args={args}")
        print(f"  text={instance.text}")

    def ti_on_focus(self, instance, value, *args):
        print(f"on_focus: focus={value} instance={instance} args={args}")
        if not value:
            # out of focus, disable overlay TextInput
            assert self.overlay
            # todo: callback app/caller to set config for current node
            great_grandparent = instance.parent.parent.parent
            # print(f"great_grandparent: {great_grandparent}")
            val = instance.text
            great_grandparent.config_value = val
            key = great_grandparent.config_key
            # print(f"key={key} val={val} node_configs={self.node_configs}")
            self.set_node_config(key, val)
            self.overlay.clear_widgets()
            self.overlay = None
            # refresh config display
            self.show_node_configs(self.node_title)

    def set_node_config_header(self, text: str, color=None, font_color=None) -> None:
        header = self.config_header
        header.header_text = text
        if color:
            header.header_color = color
        if font_color:
            header.font_color = font_color

    def set_node_config(self, key: str, val: str) -> None:
        # ast.literal_eval will crash on strings (e.g. "v4tiny"),
        # so need to catch exception and assume string as baseline
        try:
            val_eval = ast.literal_eval(val)
        except:
            val_eval = val
        print(f"val: {type(val)} {val}")

        node_title = self.node_title
        default_val = self.config_parser.get_default_value(node_title, key)
        print(f"check {val_eval} {type(val_eval)} =? {default_val} {type(default_val)}")

        for i, config in enumerate(self.node_configs):
            if key in config:
                # if user value == default value, remove config[key]
                if val_eval == default_val:
                    # print(f"removing {i}, {config}")
                    # self.node_configs.pop(i)
                    self.pipeline_model.node_config_pop(node_title, key)
                else:
                    # print(f"different, changing config[{key}]")
                    # config[key] = val_eval
                    self.pipeline_model.node_config_set(node_title, key, val_eval)
                return  # always return since something is updated
        # print(f"key {key} not found in any config")
        # if different from default value, add as new user config
        if val_eval != default_val:
            # print("add new user config")
            # self.node_configs.append({key: val_eval})
            self.pipeline_model.node_config_set(node_title, key, val_eval)

    def show_node_configs(self, node_title: str) -> None:
        # def show_node_configs(self, node_title: str, node_configs_tmp: List) -> None:
        """Shows configuration for given node

        Args:
            node_title (str): name of node, e.g. `input.visual`
            node_config (List): list of node configurations
        """
        self.node_title = node_title  # reference to current node
        self.node_configs = self.pipeline_model.node_config_get(node_title)
        self.draw_node_configs()

    def draw_node_configs(self) -> None:
        node_title = self.node_title
        node_configs = self.node_configs
        node_type = get_node_type(node_title)
        node_color = NODE_RGBA_COLOR[node_type]
        # update node config view
        if node_type in ("input", "model"):
            self.set_node_config_header(node_title, color=node_color, font_color=BLACK)
        else:
            self.set_node_config_header(node_title, color=node_color, font_color=WHITE)

        config_layout = self.config_layout
        config_layout.clear_widgets()
        # need to make a copy else configs will get overridden by user updates
        default_config = self.config_parser.get_default_configs(node_title).copy()
        # replace default with user config
        user_config_keys = set()
        for config in node_configs:
            for k, v in config.items():
                if k in default_config:
                    user_config_keys.add(k)
                    default_config[k] = v
        # show default config with user overrides
        show_all: bool = self.pipeline_view.config_state == "expand"
        no_config: bool = True
        for k, v in default_config.items():
            if k not in NODE_CONFIG_RESERVED_KEYS:
                tick = k in user_config_keys
                if show_all or tick:
                    config = NodeConfig(
                        config_key=str(k),
                        config_value=str(v).replace("'", '"'),
                        config_set=tick,
                        callback_double_tap=self.config_double_tap,
                    )
                    config_layout.add_widget(config)
                    no_config = False
        if no_config:
            # add dummy widget showing "No Config" message
            config = NodeConfig(
                config_key="",
                config_value="No user defined configurations",
                config_set=False,
                callback_double_tap=None,
            )
            config_layout.add_widget(config)
        self.pipeline_config.scroll_y = 1.0  # move scrollview to top
