from typing import Any, Dict, List
import peekingduck
import yaml
from pathlib import Path


def get_peekingduck_path() -> Path:
    pkd_path = peekingduck.__path__[0]
    return Path(pkd_path)


class NodeConfigParser:
    def __init__(self) -> None:
        self.pkd_path = get_peekingduck_path()
        self.config_path = self.pkd_path / "configs"
        self.find_config_dirs()
        self.parse_default_configs()

    def find_config_dirs(self) -> None:
        """Get directories containing PeekingDuck configs"""
        files = self.config_path.glob("*")
        self.config_dirs = sorted([file for file in files if file.is_dir()])
        print("config_dirs:", self.config_dirs)

    def get_default_configs(self, node_title: str):
        return self.default_config_map[node_title]

    def get_default_value(self, node_title: str, config_key: str):
        default_config = self.default_config_map[node_title]
        default_val = default_config[config_key]
        return default_val

    def get_string_representation(
        self, node_list: List[str], node_to_config: Dict[str, Any]
    ) -> str:
        if node_list is None:
            return ""

        pipeline_nodes = []

        for node_title in node_list:
            node_config = node_to_config[node_title]
            # print(f"{node_title}")
            # print(f"-> {node_config}")

            if "None" in node_config[0]:
                # print(f"append {node_title}")
                pipeline_nodes.append(node_title)
            else:
                configs = {k: v for dd in node_config for k, v in dd.items()}
                node_dict = {node_title: configs}
                # print(f"append {node_dict}")
                pipeline_nodes.append(node_dict)

        pipeline = {"nodes": pipeline_nodes}
        res = f"{pipeline}"
        print("res:", res)
        return res

    def parse_default_configs(self) -> None:
        """Parse PeekingDuck node default configuration"""
        self.nodes_by_type = dict()  # map node type -> list of nodes
        self.default_config_map = dict()  # map node title -> node config

        for config in self.config_dirs:
            node_type = config.name
            # print(f"parsing node_type={node_type}")
            files = sorted(config.glob("*.yml"))
            # working data structures
            node_list = []

            for config_file in files:
                node_name = config_file.name[:-4]
                node_title = f"{node_type}.{node_name}"
                # print("  ", node_name)
                with open(config_file) as file:
                    node_config = yaml.safe_load(file)
                # print(f"--{node_title} config:{type(node_config)}--")
                # print(node_config)

                self.default_config_map[node_title] = node_config
                node_list.append(node_title)

            self.nodes_by_type[node_type] = node_list

    def verify_config(self, idx_to_node: List[str]) -> List:
        """Return a list of pipeline errors, if any

        Args:
            idx_to_node (List[str]): list of node titles

        Returns:
            List: list of pipeline errors
        """
        pipeline_errors = []

        if idx_to_node:
            data_types_available = set()
            for i, node_title in enumerate(idx_to_node):
                print(f"verifying {node_title}...")
                if node_title.startswith("custom_nodes."):
                    print("skipping custom node")
                    continue  # ignore custom nodes for now... todo
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
    # config_parser.debug_configs()
    # print(config_parser.nodes_list)
    # print(config_parser.nodes_by_type)
    # print(config_parser.node_config_map)


if __name__ == "__main__":
    main()
