#
# PeekingDuck GUI Model for Pipeline
#

from typing import List
import yaml


class PipelineModel:
    def __init__(self, the_path: str) -> None:
        self.pipeline_path = the_path
        self.load_pipeline()
        self.parse_pipeline()

    @property
    def num_nodes(self) -> int:
        return self._num_nodes

    @property
    def node_list(self) -> List[str]:
        return self.idx_to_node

    def debug(self) -> None:
        print(f"pipeline: {self._num_nodes} nodes")
        for i in range(self._num_nodes):
            node = self.idx_to_node[i]
            print(f"{i} {node}")

        print("nodes_to_configs:")
        for k, v in self.nodes_to_configs.items():
            print(f"key={k} val={v}")

    def load_pipeline(self) -> None:
        with open(self.pipeline_path) as file:
            self.pipeline = yaml.safe_load(file)
        print(f"self.pipeline: {type(self.pipeline)}")

    def parse_pipeline(self) -> None:
        """
        Method to parse loaded pipeline and create internal representation of pipeline
        nodes.
        """
        pipeline_nodes = self.pipeline["nodes"]
        # working vars to store/manage pipeline sequence
        self._num_nodes = len(pipeline_nodes)
        self.idx_to_node = [None] * self._num_nodes
        self.node_to_idx = dict()
        # to cache pipeline nodes->configs
        self.nodes_to_configs = dict()

        # decode pipeline and cache nodes->configs
        for i, node in enumerate(pipeline_nodes):
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
            self.idx_to_node[i] = node_title
            self.node_to_idx[node_title] = i
            self.nodes_to_configs[node_title] = node_config

    def node_add(self, node: str, i: int) -> None:
        """Add node "node list" at given position index

        Args:
            node (_type_): node to be added
            i (int): node position index
        """
        assert 0 <= i < self._num_nodes
        self.idx_to_node[i] = node
        self.node_to_idx[node] = i

    def node_delete(self, node: str) -> None:
        """Delete node by:
        1. moving it to the end of pipeline (to preserve other nodes sequence)
        2. popping list and dict data structures

        Args:
            node (str): node to be deleted
        """
        i = self.node_to_idx[node]
        num_percolate = self._num_nodes - i - 1
        for k in range(num_percolate):
            self.node_move_down(node)
        self.idx_to_node.pop()
        self.node_to_idx.pop(node)
        self._num_nodes -= 1
        self.nodes_to_configs.pop(node)

    def node_get(self, i: int) -> str:
        """Get the i-th node in pipeline

        Args:
            i (int): index of node to get

        Returns:
            str: title of node
        """
        assert 0 <= i < self._num_nodes
        return self.idx_to_node[i]

    def node_move_up(self, node: str) -> None:
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
            self.idx_to_node[j] = prev_node
            self.node_to_idx[prev_node] = j

    def node_move_down(self, node: str) -> None:
        """Move towards end of pipeline

        Args:
            node (_type_): node to be moved
        """
        i = self.node_to_idx[node]
        j = i + 1
        if j < self._num_nodes:
            next_node = self.idx_to_node[j]
            self.idx_to_node[j] = node
            self.node_to_idx[node] = j
            self.idx_to_node[i] = next_node
            self.node_to_idx[next_node] = i

    def node_test(self) -> None:
        node = self.idx_to_node[5]
        self.node_delete(node)
        self.debug()

    def node_config_get(self, node: str):
        return self.nodes_to_configs[node]
