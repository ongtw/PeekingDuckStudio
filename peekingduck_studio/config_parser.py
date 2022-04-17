#
# PeekingDuck Studio Parser for Node Configuration
#
from typing import Any, Dict, List
from peekingduck_studio.gui_utils import (
    CUSTOM_NODES,
    get_peekingduck_path,
    find_config_dirs,
    parse_configs,
    guess_config_value_types,
    make_logger,
)
from peekingduck_studio.model_node import ModelNode
from peekingduck_studio.model_pipeline import ModelPipeline

logger = make_logger(__name__)


class NodeConfigParser:
    def __init__(self) -> None:
        self.pkd_path = get_peekingduck_path()
        self.config_path = self.pkd_path / "configs"
        self.config_dirs = find_config_dirs(self.config_path)
        logger.debug(f"config_dirs: {self.config_dirs}")
        self.nodes_by_type, self.default_config_map = parse_configs(self.config_dirs)
        self.default_config_types = guess_config_value_types(self.default_config_map)
        self.pipeline_model: ModelPipeline = None

    def get_default_configs(self, node_title: str) -> Dict:
        """Return the default set of configuration for given node

        Args:
            node_title (str): the node to get default config for

        Returns:
            Dict: the node's default configurations
        """
        logger.debug(f"node_title: {node_title}")
        return (
            self.pipeline_model.custom_nodes_default_config_map[
                node_title[1 + len(CUSTOM_NODES) :]
            ]
            if node_title.startswith(CUSTOM_NODES)
            else self.default_config_map[node_title]
        )

    def get_default_config_type(self, node_title: str, config_key: str) -> str:
        """Return the type for given node title's config key based on its default value

        Args:
            node_title (str): given node title
            config_key (str): config key to get type

        Returns:
            str: the default type
        """
        logger.debug(f"node_title: {node_title} config_key: {config_key}")
        default_types = (
            self.pipeline_model.custom_nodes_default_config_types[
                node_title[1 + len(CUSTOM_NODES) :]
            ]
            if node_title.startswith(CUSTOM_NODES)
            else self.default_config_types[node_title]
        )
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
        logger.debug(f"node_title: {node_title} config_key: {config_key}")
        default_config = (
            self.pipeline_model.custom_nodes_default_config_map[
                node_title[1 + len(CUSTOM_NODES) :]
            ]
            if node_title.startswith(CUSTOM_NODES)
            else self.default_config_map[node_title]
        )
        default_val = default_config[config_key]
        logger.debug(f"default_val: {default_val}")
        return default_val

    def get_all_config_keys(self, node_title: str) -> List[str]:
        """Return a list of config keys for given node title

        Args:
            node_title (str): given node title

        Returns:
            List[str]: list of config keys
        """
        logger.debug(f"node_title: {node_title}")
        default_config = (
            self.pipeline_model.custom_nodes_default_config_map[
                node_title[1 + len(CUSTOM_NODES) :]
            ]
            if node_title.startswith(CUSTOM_NODES)
            else self.default_config_map[node_title]
        )
        keys = list(default_config.keys())
        logger.debug(f"keys: {keys}")
        return keys

    def get_all_node_types(self) -> List[str]:
        """Return list of all node types
        NB: no custom nodes, just the default PeekingDuck node types

        Returns:
            List[str]: list of all node types
        """
        return list(self.nodes_by_type.keys())

    def get_all_node_titles(self, node_type: str) -> List[str]:
        """Return list of all node titles for given node type
        NB: include custom nodes, if any, prefix with `custom_nodes.`

        Args:
            node_type (str): given node type

        Returns:
            List[str]: list of all node titles
        """
        # make a copy 'coz list is mutated by custom nodes, if any
        all_node_titles = self.nodes_by_type[node_type].copy()
        if self.pipeline_model and self.pipeline_model.has_custom_nodes:
            if node_type in self.pipeline_model.custom_nodes_by_type:
                all_node_titles.extend(
                    [
                        f"{CUSTOM_NODES}.{x}"
                        for x in self.pipeline_model.custom_nodes_by_type[node_type]
                    ]
                )
        logger.debug(f"node_type: {node_type} all_node_titles: {all_node_titles}")
        return all_node_titles

    def is_custom_node(self, node_title: str) -> bool:
        """Query if given node_title is a custom node

        Args:
            node_title (str): node title to query

        Returns:
            bool: True if is custom node, False otherwise
        """
        logger.debug(f"node_title: {node_title}")
        if self.pipeline_model and self.pipeline_model.has_custom_nodes:
            return node_title in self.pipeline_model.custom_nodes_default_config_map
        return False

    def set_pipeline_model(self, pipeline_model: ModelPipeline) -> None:
        """Cache ModelPipeline object within self

        Args:
            pipeline_model (ModelPipeline): the pipeline model
        """
        self.pipeline_model = pipeline_model

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
                logger.debug(f"verifying {node_title}...")
                if node_title.startswith("custom_nodes."):
                    logger.debug("skipping custom node")
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
                            logger.debug(f"data_types: {data_types_available}")
                            logger.debug(f"'{the_input}' not available")
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
            logger.debug(f"node_type={node_type}")

            for node_title in node_list:
                node_name = node_title.split(".")[1]
                node_config = self.default_config_map[node_title]
                logger.debug(f"node_title={node_title}, node_name={node_name}")
                logger.debug(node_config)


def main():
    config_parser = NodeConfigParser()
    # config_parser.guess_config_value_types()
    # config_parser.debug_configs()
    # all_node_types = config_parser.get_all_node_types()
    # logger.debug(f"all node types: {all_node_types}")
    # for node_type in all_node_types:
    #     all_node_names = config_parser.get_all_node_titles(node_type)
    #     logger.debug(f"{node_type}: {all_node_names}")


if __name__ == "__main__":
    main()
