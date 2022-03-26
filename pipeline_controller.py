#
# PeekingDuck GUI Controller for Pipeline Nodes
#

from typing import List
from gui_widgets import Node
from gui_utils import get_node_color
from config_parser import NodeConfigParser
from pipeline_model import PipelineModel


class PipelineController:
    def __init__(self, config_parser, pipeline_view) -> None:
        self.pipeline_view = pipeline_view
        self.pipeline_header = self.pipeline_view.ids["pipeline_header"]
        self.pipeline_nodes_view = self.pipeline_view.ids["pipeline_nodes"]
        self.nodes_layout = self.pipeline_nodes_view.ids["pipeline_layout"]
        self.config_parser: NodeConfigParser = config_parser
        self.pipeline_model: PipelineModel = None

    def get_node_config(self, node_title: str):
        node_config = self.pipeline_model.node_config_get(node_title)
        return node_config

    def move_node(self, node: Node, direction: str) -> None:
        if direction == "up":
            self.pipeline_model.node_move_up(node.node_text)
        elif direction == "down":
            self.pipeline_model.node_move_down(node.node_text)
        else:
            print(f"move_node: unknown direction {direction}")
            return

        # as self.draw_nodes() clears all widgets and makes new ones,
        # need to get the new_node equivalent of current node in order
        # to move scrollview to the new_node
        new_node = self.draw_nodes(node.node_text)
        self.pipeline_nodes_view.scroll_to(new_node)

    def set_pipeline_header(self, text: str) -> None:
        self.pipeline_header.header_text = text

    def set_pipeline_model(self, pipeline_model) -> None:
        self.pipeline_model = pipeline_model

    def toggle_config_state(self) -> None:
        """Toggle show all or only user-defined configurations"""
        if self.pipeline_view.config_state == "expand":
            self.pipeline_view.config_state = "contract"
        else:
            self.pipeline_view.config_state = "expand"

    def update_node_config(self, node_title: str, key: str, val) -> None:
        # todo: reconcile node updating of user configs
        node_config: List = self.pipeline_nodes_to_configs[node_title]
        for config in node_config:
            if config.key == node_title:
                config[key] = val

    def verify_pipeline(self):
        if self.pipeline_model:
            node_list = self.pipeline_model.node_list
            res = self.config_parser.verify_config(node_list)
            return res
        else:
            return None

    ########################
    # Node layout management
    ########################
    def draw_nodes(self, return_node_title: str = None):
        """Redraw pipeline nodes layout"""
        self.nodes_layout.clear_widgets()
        node_to_return = None
        n = self.pipeline_model.num_nodes
        self.set_pipeline_header(f"Pipeline: {n} nodes")
        for i in range(n):
            node_title = self.pipeline_model.node_get(i)
            print(f"draw {node_title}")
            node_num = str(i + 1)
            node_color = get_node_color(node_title)
            node = Node(
                bkgd_color=node_color, node_number=node_num, node_text=node_title
            )
            self.nodes_layout.add_widget(node)
            if return_node_title and node_title == return_node_title:
                node_to_return = node
        return node_to_return
