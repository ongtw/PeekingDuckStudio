#
# PeekingDuck Studio Parser for Node Configuration
#
from typing import Any, Dict, List
import peekingduck
import yaml
from pathlib import Path
from peekingduck_studio.pipeline_model import ModelNode

NODE_CONFIG_READONLY_KEYS = {"input", "output", "model_size"}
NODE_CONFIG_RESERVED_KEYS = {"MODEL_NODES", "weights", "weights_parent_dir"}


def get_peekingduck_path() -> Path:
    pkd_path = peekingduck.__path__[0]
    return Path(pkd_path)


class NodeConfigParser:
    def __init__(self) -> None:
        self.pkd_path = get_peekingduck_path()
        self.config_path = self.pkd_path / "configs"
        self.find_config_dirs()
        self.parse_default_configs()
        self.guess_default_config_value_types()

    def find_config_dirs(self) -> None:
        """Get directories containing PeekingDuck configs"""
        files = self.config_path.glob("*")
        self.config_dirs = sorted([file for file in files if file.is_dir()])
        print("config_dirs:", self.config_dirs)

    def get_default_configs(self, node_title: str) -> Dict:
        """Return the default set of configuration for given node

        Args:
            node_title (str): the node to get default config for

        Returns:
            Dict: the node's default configurations
        """
        return self.default_config_map[node_title]

    def get_default_config_type(self, node_title: str, config_key: str) -> str:
        """Return the type for given node title's config key based on its default value

        Args:
            node_title (str): given node title
            config_key (str): config key to get type

        Returns:
            str: the default type
        """
        default_types = self.default_config_types[node_title]
        config_type = default_types[config_key]
        return config_type

    def get_default_value(self, node_title: str, config_key: str) -> Any:
        """Return the default value for given node title's config key

        Args:
            node_title (str): given node title
            config_key (str): config key to get value

        Returns:
            Any: the default value
        """
        default_config = self.default_config_map[node_title]
        default_val = default_config[config_key]
        return default_val

    def get_all_config_keys(self, node_title: str) -> List[str]:
        """Return a list of config keys for given node title

        Args:
            node_title (str): given node title

        Returns:
            List[str]: list of config keys
        """
        default_config = self.default_config_map[node_title]
        keys = list(default_config.keys())
        return keys

    def get_all_node_types(self) -> List[str]:
        """Return list of all node types

        Returns:
            List[str]: list of all node types
        """
        return list(self.nodes_by_type.keys())

    def get_all_node_titles(self, node_type: str) -> List[str]:
        """Return list of all node titles for given node type

        Args:
            node_type (str): given node type

        Returns:
            List[str]: list of all node titles
        """
        return self.nodes_by_type[node_type]

    def guess_config_type(self, key: str, val: Any) -> str:
        """Guesstimate the type for given config key based on given value

        Args:
            key (str): given config key
            val (Any): given value

        Returns:
            str: the type
        """
        # guesstimate value type
        the_type: str = "str"
        if key in NODE_CONFIG_READONLY_KEYS:
            the_type = "readonly"
        elif isinstance(val, bool):
            the_type = "bool"
        elif isinstance(val, int):
            the_type = "int"
        elif isinstance(val, float):
            if 0 <= val <= 1.0 and key.endswith(("_factor", "_threshold")):
                the_type = "float_01"
            else:
                the_type = "float"
        elif isinstance(val, dict):
            if len(val) == 2 and key.endswith("resolution"):
                the_type = "dict_wh"
            else:
                the_type = "dict"
        elif isinstance(val, list):
            if len(val) == 2 and key.endswith("resolution"):
                the_type = "list_wh"
            elif len(val) == 3 and key.endswith("_color"):
                the_type = "list_bgr"
            else:
                the_type = "list"
        elif isinstance(val, str):
            if key.endswith("_path"):
                the_type = "str_path"
            else:
                the_type = "str"
        else:
            the_type = "nonetype"
        return the_type

    def guess_default_config_value_types(self) -> None:
        """Guesstimate and store all default config value types"""
        default_config_types = {}  # map node_title -> { config_key -> config_type }
        for node_title, default_config in self.default_config_map.items():
            print(f"{node_title}")
            config_type_map = {}  # map config_key -> config_type
            for k, v in default_config.items():
                # skip reserved keys
                if k in NODE_CONFIG_RESERVED_KEYS:
                    continue
                config_type = self.guess_config_type(k, v)
                print(f"  {k}: {config_type} = {v}")
                config_type_map[k] = config_type
            default_config_types[node_title] = config_type_map
        # print(default_config_types)
        self.default_config_types = default_config_types

    def parse_default_configs(self) -> None:
        """Parse PeekingDuck node default configurations"""
        # map node type -> list of node titles
        self.nodes_by_type: Dict[str, List[str]] = dict()
        # map node title -> node config
        self.default_config_map: Dict[str, Dict[str, Any]] = dict()

        for config in self.config_dirs:
            node_type = config.name
            # print(f"** node_type={node_type}")
            files = sorted(config.glob("*.yml"))
            # working data structures
            node_title_list = []

            for config_file in files:
                node_name = config_file.name[:-4]
                node_title = f"{node_type}.{node_name}"
                # print("  ", node_name)
                with open(config_file) as file:
                    node_config = yaml.safe_load(file)
                # print(f"-- {node_title} config:{type(node_config)}")
                # print(node_config)

                self.default_config_map[node_title] = node_config
                node_title_list.append(node_title)

            self.nodes_by_type[node_type] = node_title_list

    def verify_config(self, idx_to_node: List[ModelNode]) -> List:
        """Return a list of pipeline errors, if any

        Args:
            idx_to_node (List[str]): list of node titles

        Returns:
            List: list of pipeline errors
        """
        pipeline_errors = []

        if idx_to_node:
            data_types_available = set()
            for i, node in enumerate(idx_to_node):
                node_title = node.node_title
                print(f"verifying {node_title}...")
                if node_title.startswith("custom_nodes."):
                    print("skipping custom node")
                    continue  # ignore custom nodes for now...
                # todo: support custom nodes
                node_config = self.default_config_map[node_title]
                node_input = node_config["input"]
                node_output = node_config["output"]
                # check input
                node_error = []
                for the_input in node_input:
                    if the_input not in ["all", "none"]:
                        if the_input not in data_types_available:
                            print(f"data_types: {data_types_available}")
                            print(f"'{the_input}' not available")
                            node_error.append(the_input)
                if node_error:
                    pipeline_errors.append([i, node_error])
                # check output
                for the_output in node_output:
                    if the_output != "none":
                        data_types_available.add(the_output)

        return pipeline_errors

    def debug_configs(self):
        for node_type, node_list in self.nodes_by_type.items():
            print(f"node_type={node_type}")

            for node_title in node_list:
                node_name = node_title.split(".")[1]
                node_config = self.default_config_map[node_title]
                print(f"node_title={node_title}, node_name={node_name}")
                print(node_config)


def main():
    config_parser = NodeConfigParser()
    # config_parser.guess_config_value_types()
    # config_parser.debug_configs()
    # all_node_types = config_parser.get_all_node_types()
    # print(f"all node types: {all_node_types}")
    # for node_type in all_node_types:
    #     all_node_names = config_parser.get_all_node_titles(node_type)
    #     print(f"{node_type}: {all_node_names}")


if __name__ == "__main__":
    main()
