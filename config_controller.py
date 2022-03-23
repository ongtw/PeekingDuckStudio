#
# PeekingDuck GUI Controller for Node Config
#

# from typing import Dict
from gui_widgets import NodeConfig
from gui_utils import get_node_type, NODE_RGBA_COLOR, BLACK, WHITE, NAVY

# todo: avoid color definition duplication
NODE_CONFIG_RESERVED_KEYS = {"MODEL_NODES", "weights", "weights_parent_dir"}

# Helper utils


class ConfigController:
    def __init__(self, config_parser, pipeline_view) -> None:
        # todo: remove dependence on pipeline_view
        self.pipeline_view = pipeline_view
        self.config_header = pipeline_view.ids["pipeline_config_header"]
        self.pipeline_config = pipeline_view.ids["pipeline_config"]
        self.config_layout = self.pipeline_config.ids["config_layout"]
        self.config_parser = config_parser

    def clear_node_configs(self) -> None:
        self.config_layout.clear_widgets()
        self.set_node_config_header("Node Config", color=NAVY, font_color=WHITE)

    def scroll_to_config(self, instance, *args) -> None:
        """Move scrollview so that config instance is fully visible

        Args:
            instance (Widget): the config instance to show onscreen

        todo: if config is fully visible on-screen, don't scroll
        """
        self.pipeline_config.scroll_to(instance)

    def set_node_config_header(self, text: str, color=None, font_color=None) -> None:
        header = self.config_header
        header.header_text = text
        if color:
            header.header_color = color
        if font_color:
            header.font_color = font_color

    def show_node_configs(self, node_title: str, node_config) -> None:
        """Shows configuration for given node

        Args:
            node_title (str): name of node, e.g. `input.visual`
            node_config (_type_): configuration of node
        """
        node_type = get_node_type(node_title)
        node_color = NODE_RGBA_COLOR[node_type]
        # update node config view
        if node_type in ("input", "model"):
            self.set_node_config_header(node_title, color=node_color, font_color=BLACK)
        else:
            self.set_node_config_header(node_title, color=node_color, font_color=WHITE)

        config_layout = self.config_layout
        config_layout.clear_widgets()
        default_config = self.config_parser.title_config_map[node_title].copy()
        # replace default with user config
        user_config_keys = set()
        for config in node_config:
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
                        config_value=str(v),
                        config_set=tick,
                        callback_double_tap=self.scroll_to_config,
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
