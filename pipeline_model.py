#
# PeekingDuck GUI Model for Pipeline
#

from re import U
from typing import Any, Dict, List, Optional, Union
import uuid
import yaml

EMPTY_NODE = "augment.brightness"
NO_USER_CONFIG = [{"None": "No Config"}]


class ModelNode:
    def __init__(self, node_title: str, user_config: Optional[List] = None) -> None:
        self._uid: str = str(uuid.uuid4())
        self._node_title = node_title
        self._user_config = user_config if user_config else NO_USER_CONFIG

    def __str__(self) -> str:
        ss = [
            f"Node: {self._node_title} {self._uid}",
            f"{self._user_config}",
            "----------",
        ]
        return "\n".join(ss)

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def node_title(self) -> str:
        return self._node_title

    @node_title.setter
    def node_title(self, node_title: str) -> None:
        self._node_title = node_title

    @property
    def user_config(self) -> List:
        return self._user_config

    @user_config.setter
    def user_config(self, user_config: List) -> None:
        self._user_config = user_config

    def pop_user_config(self, key: str) -> None:
        """Delete node's user config for given key.

        Args:
            key (str): key of user config to delete
        """
        for i, dd in enumerate(self._user_config):
            if key in dd:
                self._user_config.pop(i)
                break
        # don't forget to handle empty user config, else will cause bugs
        if not self._user_config:
            self._user_config = NO_USER_CONFIG

    def set_user_config(self, key: str, val: Any) -> None:
        """Set or update node's user config with given {key,val} pair.

        Args:
            key (str): user config key
            val (Any): user config value
        """
        if self._user_config == NO_USER_CONFIG:
            self._user_config = [{key: val}]
        else:
            # if key exists in any config, update it else append new config
            found: bool = False
            for dd in self._user_config:
                if key in dd:
                    dd[key] = val
                    found = True
                    break
            if not found:
                self._user_config.append({key: val})


class ModelPipeline:
    def __init__(self, the_path: Optional[str] = None) -> None:
        # declare internal working vars
        self._idx_to_node: List[ModelNode] = None  # indexed lookup
        self._uid_to_idx: Dict[str, int] = None  # reverse lookup
        if the_path:
            self.load_pipeline(the_path)
            self.parse_pipeline()
        else:
            basic_pipeline = {
                "nodes": [
                    {"input.visual": {"source": 0}},
                    "model.posenet",
                    "draw.poses",
                    "output.screen",
                ]
            }
            self.parse_pipeline(basic_pipeline)
        self.set_dirty_bit()

    def __getitem__(self, i: int) -> Union[ModelNode, None]:
        return self._idx_to_node[i] if self._idx_to_node else None

    def __len__(self) -> int:
        return len(self._idx_to_node)

    def __str__(self) -> str:
        ss = [str(node) for node in self._idx_to_node]
        return "\n".join(ss)

    @property
    def dirty(self) -> bool:
        return self._dirty_bit

    @property
    def num_nodes(self) -> int:
        return len(self._idx_to_node)

    @property
    def node_list(self) -> List[ModelNode]:
        return self._idx_to_node

    def debug(self) -> None:
        print(f"pipeline: {self.num_nodes} nodes")
        for i in range(self.num_nodes):
            node = self._idx_to_node[i]
            print(f"{i} {node}")

    def clear_dirty_bit(self) -> None:
        self._dirty_bit = False

    def set_dirty_bit(self) -> None:
        self._dirty_bit = True

    def get_node_by_index(self, i: int) -> ModelNode:
        """Get the i-th node in pipeline

        Args:
            i (int): index of node to get

        Returns:
            ModelNode: node object required
        """
        assert 0 <= i < self.num_nodes
        return self._idx_to_node[i]

    def get_node_by_uid(self, uid: str) -> ModelNode:
        """Get node in pipeline with given uuid

        Args:
            uid (str): uuid of node to get

        Returns:
            ModelNode: node object required
        """
        i = self._uid_to_idx[uid]
        node = self._idx_to_node[i]
        return node

    def get_string_representation(self, node_list: List[ModelNode] = None) -> str:
        """Return JSON string representation for given list of ModelNodes.
        This string can be parsed by PeekingDuck.

        Args:
            node_list (List[ModelNode]): given list of ModelNodes

        Returns:
            str: their JSON string representation
        """
        if node_list is None:
            node_list = self.node_list

        pipeline_nodes = []

        for node in node_list:
            node_title = node.node_title
            user_config = node.user_config
            print(f"{node_title} -> {user_config}")

            if "None" in user_config[0]:
                # print(f"append {node_title}")
                pipeline_nodes.append(node_title)
            else:
                configs = {k: v for dd in user_config for k, v in dd.items()}
                node_dict = {node_title: configs}
                # print(f"append {node_dict}")
                pipeline_nodes.append(node_dict)

        pipeline = {"nodes": pipeline_nodes}
        res = f"{pipeline}"
        print("run pipeline:", res)
        return res

    def load_pipeline(self, pipeline_path: str) -> None:
        """Load pipeline file in given path

        Args:
            pipeline_path (str): full path to pipeline file
        """
        with open(pipeline_path) as file:
            self._pipeline = yaml.safe_load(file)
        print(f"load_pipeline: {type(self._pipeline)}")
        print(self._pipeline)

    def parse_pipeline(self, the_pipeline: Optional[Dict] = None) -> None:
        """Parse pipeline and create internal representation of it.
        If the_pipeline is not given, parse self._pipeline instead.

        Args:
            the_pipeline (Optional[Dict], optional):
                Pipeline to parse. Defaults to None.

        Raises:
            ValueError: Node type error
        """
        pipeline = the_pipeline["nodes"] if the_pipeline else self._pipeline["nodes"]
        # init working vars to store/manage pipeline sequence
        num_nodes = len(pipeline)
        self._idx_to_node = [None] * num_nodes
        self._uid_to_idx = dict()  # reverse lookup
        # decode pipeline nodes
        for i, node in enumerate(pipeline):
            if isinstance(node, str):
                node_title = node
                user_config = NO_USER_CONFIG
            elif isinstance(node, dict):
                node_title = list(node.keys())[0]
                user_config = []
                config_dd = node[node_title]
                for k, v in config_dd.items():
                    kv_dict = {k: v}
                    user_config.append(kv_dict)
            else:
                raise ValueError(f"parse_pipeline error: i={i} node type={type(node)}")
            # add new node to pipeline
            node = ModelNode(node_title, user_config)
            self._idx_to_node[i] = node
            self._uid_to_idx[node.uid] = i

    ####################
    # Node Management
    ####################
    def node_delete(self, i: int) -> None:
        """Delete node by:
        1. moving it to the end of pipeline (to preserve other nodes sequence)
        2. popping list and dict data structures

        Args:
            i (int): index of node to be deleted
        """
        node = self._idx_to_node[i]
        num_percolate = self.num_nodes - i - 1
        for k in range(num_percolate):
            self.node_move_down(node.uid)
        self._idx_to_node.pop()
        self._uid_to_idx.pop(node.uid)
        self.set_dirty_bit()

    def node_insert(self, i: int) -> None:
        """Insert "empty" node at index i, shift all nodes "down".
        But since there is no "empty" node, will insert augment.brightness
        by default.

        Args:
            i (int): index to insert node
        """
        assert 0 <= i <= self.num_nodes
        node_title = EMPTY_NODE
        node_config = NO_USER_CONFIG
        node = ModelNode(node_title, node_config)
        if i == self.num_nodes:
            # add to end
            self._idx_to_node.append(node)
            self._uid_to_idx[node.uid] = i
        else:
            # insert at i, blockshift everything down by 1
            self._idx_to_node.append(None)  # create one new empty slot
            # NB: 'self.num_nodes - 2' 'coz n-1 == last node (n = self.num_nodes),
            #     so shift n-2 -> n-1,
            #              n-3 -> n-2,
            #              ... etc, all the way up to
            #                i -> i + 1
            for j in range(self.num_nodes - 2, i - 1, -1):
                curr_node = self._idx_to_node[j]
                k = j + 1
                self._idx_to_node[k] = curr_node
                self._uid_to_idx[curr_node.uid] = k
            self._idx_to_node[i] = node
            self._uid_to_idx[node.uid] = i
        self.set_dirty_bit()

    def node_move_up(self, uid: str) -> None:
        """Move towards start of pipeline

        Args:
            uid (str): uuid of node to be moved
        """
        j = self._uid_to_idx[uid]
        node = self._idx_to_node[j]
        assert uid == node.uid
        if j > 0:
            i = j - 1
            prev_node = self._idx_to_node[i]
            self._idx_to_node[i] = node
            self._uid_to_idx[node.uid] = i
            self._idx_to_node[j] = prev_node
            self._uid_to_idx[prev_node.uid] = j
        self.set_dirty_bit()

    def node_move_down(self, uid: str) -> None:
        """Move towards end of pipeline

        Args:
            uid (str): uuid node to be moved
        """
        i = self._uid_to_idx[uid]
        node = self._idx_to_node[i]
        assert uid == node.uid
        j = i + 1
        if j < self.num_nodes:
            next_node = self._idx_to_node[j]
            self._idx_to_node[j] = node
            self._uid_to_idx[node.uid] = j
            self._idx_to_node[i] = next_node
            self._uid_to_idx[next_node.uid] = i
        self.set_dirty_bit()

    def node_replace(self, i: int, node: ModelNode) -> None:
        """Replace node at given position index, overwrite existing data

        Args:
            i (int): node position index
            node (ModelNode): new node to replace existing
        """
        assert 0 <= i < self.num_nodes
        old_node = self._idx_to_node[i]
        self._uid_to_idx.pop(old_node.uid)  # remove old node
        self._idx_to_node[i] = node
        self._uid_to_idx[node.uid] = i  # add new node
        self.set_dirty_bit()

    def get_user_config(self, uid: str) -> List:
        """Return user config of given node uuid

        Args:
            uid (str): uuid of node to query user config

        Returns:
            List: user config of the node
        """
        node = self.get_node_by_uid(uid)
        return node.user_config

    def set_user_config(self, uid: str, key: str, val: Any) -> None:
        """Set user config key:val for given node uuid

        Args:
            uid (str): uuid of node to update
            key (str): user config key
            val (Any): user config value
        """
        node = self.get_node_by_uid(uid)
        node.set_user_config(key, val)
        self.set_dirty_bit()

    def pop_user_config(self, uid: str, key: str) -> None:
        """Delete user config with given key

        Args:
            uid (str): uuid of node to update
            key (str): key of user config to delete
        """
        node = self.get_node_by_uid(uid)
        node.pop_user_config(key)
        self.set_dirty_bit()


def main():
    """Quick and dirty test of ModelPipeline and ModelNodes"""
    data = {
        "nodes": [
            {"input.visual": {"source": 0}},
            {"model.yolo": {"model_type": "v4"}},
            "draw.bbox",
            "output.screen",
        ]
    }
    pipeline = ModelPipeline()
    pipeline.parse_pipeline(data)

    n = len(pipeline)
    print(f"Pipeline has {n} nodes")
    print(pipeline)
    pipeline.node_insert(n)

    n = len(pipeline)
    print(f"Pipeline has {n} nodes")
    print(pipeline)
    node = pipeline.get_node_by_index(n - 1)
    pipeline.node_move_up(node.uid)

    print("after move up:")
    print(pipeline)


if __name__ == "__main__":
    main()
