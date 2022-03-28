#
# PeekingDuck GUI Model for Pipeline
#

from typing import Any, Dict, List
import yaml

NO_CONFIG = [{"None": "No Config"}]


class PipelineModel:
    def __init__(self, the_path: str) -> None:
        self.pipeline_path = the_path
        self.load_pipeline()
        self.parse_pipeline()

    @property
    def dirty(self) -> bool:
        return self._dirty_bit

    @property
    def num_nodes(self) -> int:
        return self._num_nodes

    @property
    def node_config(self) -> Dict[str, Any]:
        return self._node_to_config

    @property
    def node_list(self) -> List[str]:
        return self._idx_to_node

    def debug(self) -> None:
        print(f"pipeline: {self._num_nodes} nodes")
        for i in range(self._num_nodes):
            node = self._idx_to_node[i]
            print(f"{i} {node}")

        print("nodes_to_configs:")
        for k, v in self._node_to_config.items():
            print(f"key={k} val={v}")

    def set_dirty_bit(self) -> None:
        self._dirty_bit = True

    def clear_dirty_bit(self) -> None:
        self._dirty_bit = False

    def load_pipeline(self) -> None:
        with open(self.pipeline_path) as file:
            self.pipeline = yaml.safe_load(file)
        print("load_pipeline:")
        print(f"self.pipeline: {type(self.pipeline)}")
        print(self.pipeline)
        self.set_dirty_bit()

    def parse_pipeline(self) -> None:
        """
        Method to parse loaded pipeline and create internal representation of pipeline
        nodes.
        """
        pipeline_nodes = self.pipeline["nodes"]
        # working vars to store/manage pipeline sequence
        self._num_nodes = len(pipeline_nodes)
        self._idx_to_node = [None] * self._num_nodes
        self._node_to_idx = dict()
        # to cache pipeline nodes->configs
        self._node_to_config = dict()

        # decode pipeline and cache nodes->configs
        for i, node in enumerate(pipeline_nodes):
            if isinstance(node, str):
                node_title = node
                # node_config = [{"None": "No Config"}]
                node_config = NO_CONFIG
            else:  # must be dict
                node_title = list(node.keys())[0]
                node_config = []
                config_dd = node[node_title]
                for k, v in config_dd.items():
                    kv_dict = {k: v}
                    node_config.append(kv_dict)
            self._idx_to_node[i] = node_title
            self._node_to_idx[node_title] = i
            self._node_to_config[node_title] = node_config

    def node_replace(self, i: int, node_title: str, node_config: List) -> None:
        """Replace node at given position index, overwrite existing data

        Args:
            i (int): node position index
            node_title (str): new node title
            node_config (List): new node config
        """
        assert 0 <= i < self._num_nodes
        old_node = self._idx_to_node[i]
        self._node_to_idx.pop(old_node)  # remove old node
        self._node_to_config.pop(old_node)
        self._idx_to_node[i] = node_title  # replace with new node
        self._node_to_idx[node_title] = i
        self._node_to_config[node_title] = node_config
        self.set_dirty_bit()

    def node_delete(self, node: str) -> None:
        """Delete node by:
        1. moving it to the end of pipeline (to preserve other nodes sequence)
        2. popping list and dict data structures

        Args:
            node (str): node to be deleted
        """
        i = self._node_to_idx[node]
        num_percolate = self._num_nodes - i - 1
        for k in range(num_percolate):
            self.node_move_down(node)
        self._idx_to_node.pop()
        self._node_to_idx.pop(node)
        self._node_to_config.pop(node)
        self._num_nodes -= 1
        self.set_dirty_bit()

    def node_get(self, i: int) -> str:
        """Get the i-th node in pipeline

        Args:
            i (int): index of node to get

        Returns:
            str: title of node
        """
        assert 0 <= i < self._num_nodes
        return self._idx_to_node[i]

    def node_move_up(self, node: str) -> None:
        """Move towards start of pipeline

        Args:
            node (_type_): node to be moved
        """
        j = self._node_to_idx[node]
        if j > 0:
            i = j - 1
            prev_node = self._idx_to_node[i]
            self._idx_to_node[i] = node
            self._node_to_idx[node] = i
            self._idx_to_node[j] = prev_node
            self._node_to_idx[prev_node] = j
        self.set_dirty_bit()

    def node_move_down(self, node: str) -> None:
        """Move towards end of pipeline

        Args:
            node (_type_): node to be moved
        """
        i = self._node_to_idx[node]
        j = i + 1
        if j < self._num_nodes:
            next_node = self._idx_to_node[j]
            self._idx_to_node[j] = node
            self._node_to_idx[node] = j
            self._idx_to_node[i] = next_node
            self._node_to_idx[next_node] = i
        self.set_dirty_bit()

    def node_test(self) -> None:
        node = self._idx_to_node[5]
        self.node_delete(node)
        self.debug()

    def node_config_get(self, node: str) -> List:
        # print(f"node_config_get: node={node}")
        # print(self._node_to_config)
        if node in self._node_to_config:
            return self._node_to_config[node]
        else:
            return NO_CONFIG

    def node_config_set(self, node: str, key: str, val: Any) -> None:
        node_config: List = self._node_to_config[node]
        print(f"node_config: {type(node_config)} {node_config}")
        if "None" in node_config[0]:
            # no config, so create first one
            node_config = [{key: val}]
        else:
            # if key exists in any config, update it,
            # else append new config
            found: bool = False
            for dd in node_config:
                if key in dd:
                    dd[key] = val
                    found = True
                    break
            if not found:
                node_config.append({key: val})
        self._node_to_config[node] = node_config
        self.set_dirty_bit()

    def node_config_pop(self, node: str, key: str) -> None:
        node_config: List = self._node_to_config[node]
        print(f"node_config: {type(node_config)} {node_config}")
        for i, dd in enumerate(node_config):
            if key in dd:
                node_config.pop(i)
                break
        self._node_to_config[node] = node_config
        self.set_dirty_bit()
