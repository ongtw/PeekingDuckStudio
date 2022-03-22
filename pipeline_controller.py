#
# PeekingDuck GUI Controller for Pipeline Nodes
#

import yaml
from pkdgui_widgets import Node
from utils import get_node_color


class PipelineController:
    def __init__(self, config_parser, pipeline_view) -> None:
        self.pipeline_view = pipeline_view
        self.pipeline_header = self.pipeline_view.ids["pipeline_header"]
        self.pipeline_nodes_view = self.pipeline_view.ids["pipeline_nodes"]
        self.nodes_layout = self.pipeline_nodes_view.ids["pipeline_layout"]
        self.config_parser = config_parser
        self.num_nodes = 0
        self.idx_to_node = None
        self.node_to_idx = None

    def get_node_config(self, node_title: str):
        node_config = self.pipeline_nodes_to_configs[node_title]
        return node_config

    def move_node(self, node, direction: str) -> None:
        if direction == "up":
            self.node_map_move_up(node)
        elif direction == "down":
            self.node_map_move_down(node)
        else:
            print(f"move_node: unknown direction {direction}")
            return

        self.node_map_draw()
        self.pipeline_nodes_view.scroll_to(node)

    def set_pipeline_header(self, text: str) -> None:
        self.pipeline_header.header_text = text

    def toggle_config_state(self) -> None:
        """Toggle show all or only user-defined configurations"""
        if self.pipeline_view.config_state == "expand":
            self.pipeline_view.config_state = "contract"
        else:
            self.pipeline_view.config_state = "expand"

    def load_file(self, the_path: str) -> None:
        with open(the_path) as file:
            self.pipeline = yaml.safe_load(file)
        self.parse_pipeline()
        self.set_pipeline_header(f"Pipeline: {len(self.pipeline['nodes'])} nodes")

    def parse_pipeline(self) -> None:
        """
        Method to parse the loaded pipeline and create graphical layout of pipeline
        nodes. A copy of the pipeline is cached within self (App).
        """
        self.pipeline_nodes_to_configs = dict()  # start new data structure
        # decode pipeline
        print(f"self.pipeline: {type(self.pipeline)}")
        loaded_pipeline_nodes = self.pipeline["nodes"]
        # set header
        num_nodes = len(loaded_pipeline_nodes)
        self.setup_node_map(num_nodes)

        # decode nodes
        for i, node in enumerate(loaded_pipeline_nodes):
            if isinstance(node, str):
                node_title = node
                node_config = [{"None": "No Config"}]
            else:  # must be dict
                node_title = list(node.keys())[0]
                node_config = []
                config_dd = node[node_title]
                for k, v in config_dd.items():
                    kv_dict = {k: v}
                    node_config.append(kv_dict)
            # cache pipeline by adding to App
            self.pipeline_nodes_to_configs[node_title] = node_config
            # create Node widget
            node_num = str(i + 1)
            node_color = get_node_color(node_title)
            node = Node(
                bkgd_color=node_color, node_number=node_num, node_text=node_title
            )
            self.node_map_add(node, i)

        self.node_map_draw()

    def verify_pipeline(self):
        res = self.config_parser.verify_config(self.idx_to_node)
        return res

    ########################
    # Node layout management
    ########################
    def setup_node_map(self, num_nodes) -> None:
        self.num_nodes = num_nodes
        self.idx_to_node = [None] * num_nodes
        self.node_to_idx = dict()

    def node_map_add(self, node, i: int) -> None:
        """Add node "node list" at given position index

        Args:
            node (_type_): node to be added
            i (int): node position index
        """
        assert i >= 0
        assert i < self.num_nodes
        self.idx_to_node[i] = node
        self.node_to_idx[node] = i
        node.node_number = str(i + 1)

    def node_map_draw(self) -> None:
        """Redraw pipeline nodes layout"""
        self.nodes_layout.clear_widgets()
        for i in range(self.num_nodes):
            node = self.idx_to_node[i]
            self.nodes_layout.add_widget(node)

    def node_map_move_up(self, node) -> None:
        """Move towards start of pipeline

        Args:
            node (_type_): node to be moved
        """
        j = self.node_to_idx[node]
        if j > 0:
            i = j - 1
            prev_node = self.idx_to_node[i]
            self.idx_to_node[i] = node
            self.node_to_idx[node] = i
            node.node_number = str(i + 1)
            self.idx_to_node[j] = prev_node
            self.node_to_idx[prev_node] = j
            prev_node.node_number = str(j + 1)

    def node_map_move_down(self, node) -> None:
        """Move towards end of pipeline

        Args:
            node (_type_): node to be moved
        """
        i = self.node_to_idx[node]
        j = i + 1
        if j < self.num_nodes:
            next_node = self.idx_to_node[j]
            self.idx_to_node[j] = node
            self.node_to_idx[node] = j
            node.node_number = str(j + 1)
            self.idx_to_node[i] = next_node
            self.node_to_idx[next_node] = i
            next_node.node_number = str(i + 1)
