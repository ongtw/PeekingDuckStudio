#
# PeekingDuck Studio Controller for Pipeline Nodes
#

from typing import List, Union
from peekingduck_studio.gui_utils import NODE_COLOR_SELECTED, make_logger
from peekingduck_studio.gui_widgets import Node, NODE_HEIGHT
from peekingduck_studio.model_node import ModelNode
from peekingduck_studio.model_pipeline import ModelPipeline

logger = make_logger(__name__)


class PipelineController:
    def __init__(self, pipeline_view) -> None:
        self.pipeline_view = pipeline_view
        self.pipeline_header = self.pipeline_view.ids["pipeline_header"]
        self.nodes_view = self.pipeline_view.ids["pipeline_nodes"]
        self.nodes_layout = self.nodes_view.ids["pipeline_layout"]
        self.pipeline_model: ModelPipeline = None
        self._node_height: int = NODE_HEIGHT

    @property
    def node_height(self) -> int:
        return self._node_height

    @node_height.setter
    def node_height(self, height: int) -> None:
        self._node_height = max(80, height)
        self.update_nodes()

    def add_node(self, idx: int) -> Node:
        """Add new node at pipeline position idx

        Args:
            idx (int): position index of new node to add

        Returns:
            Node: the GUI node associated with the new node
        """
        logger.debug(f"at index {idx}")
        self.pipeline_model.node_insert(idx)
        node = self.pipeline_model.get_node_by_index(idx)
        gui_node = self.draw_nodes(node.uid)
        return gui_node

    def delete_node(self, idx: int) -> None:
        """Delete node at pipeline position idx

        Args:
            idx (int): position index of node to delete
        """
        logger.debug(f"at index {idx}")
        self.pipeline_model.node_delete(idx)
        self.draw_nodes()

    def focus_on_node(self, node: Node) -> None:
        """Scroll the nodes layout scroll view so that given GUI node is visible

        Args:
            node (Node): the GUI node to focus on
        """
        logger.debug(f"node: {node.node_text}")
        parent = self.nodes_layout.parent
        if self.nodes_layout.height > parent.height:
            self.nodes_view.scroll_to(node)
        else:
            self.nodes_view.scroll_y = 1.0

    def move_node(self, node: Node, direction: str) -> Node:
        """Shift given GUI node in specified direction

        Args:
            node (Node): given GUI node
            direction (str): either "up" or "down"

        Raises:
            ValueError: if direction is neither "up" nor "down"

        Returns:
            Node: the new GUI node of the moved old GUI node (see technote below)
        """
        logger.debug(f"node: {node.node_text} direction: {direction}")
        if direction == "up":
            self.pipeline_model.node_move_up(node.node_id)
        elif direction == "down":
            self.pipeline_model.node_move_down(node.node_id)
        else:
            raise ValueError(f"move_node: unknown direction {direction}")
        # Technote: as self.draw_nodes() clears all widgets and makes new ones,
        # need to get the new_node equivalent of current node in order to move
        # scrollview to the new_node
        new_node = self.draw_nodes(node.node_id)
        new_node.select_color = NODE_COLOR_SELECTED
        parent = self.nodes_layout.parent
        if self.nodes_layout.height > parent.height:
            self.nodes_view.scroll_to(new_node)
        else:
            self.nodes_view.scroll_y = 1.0
        return new_node

    def replace_with_new_node(self, i: int, new_node_title: str) -> Node:
        """Replace existing node at pipeline position i with new node
        created of 'new_node_title' (e.g. input.visual)

        Args:
            i (int): index of node to be replaced
            new_node_title (str): title of new node to be created
        """
        logger.debug(f"index {i} with {new_node_title}")
        new_node = ModelNode(new_node_title)
        self.pipeline_model.node_replace(i, new_node)
        gui_node = self.draw_nodes(new_node.uid)
        return gui_node

    def set_pipeline_header(self, text: str) -> None:
        """Set pipeline header to given text

        Args:
            text (str): new pipeline header text
        """
        self.pipeline_header.header_text = text

    def set_pipeline_model(self, pipeline_model: ModelPipeline) -> None:
        """Set pipeline model working var to given ModelPipeline

        Args:
            pipeline_model (ModelPipeline): the new ModelPipeline
        """
        self.pipeline_model = pipeline_model

    def toggle_config_state(self) -> None:
        """Toggle show all or only user-defined configurations"""
        if self.pipeline_view.config_state == "expand":
            self.pipeline_view.config_state = "contract"
        else:
            self.pipeline_view.config_state = "expand"

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
    def draw_nodes(self, return_uid: str = None) -> Union[Node, None]:
        """Draw/redraw pipeline nodes layout, with option to return
        a GUI node of interest back to caller.

        Args:
            return_uid (str, optional):
                uuid of node of interest to return. Defaults to None.

        Returns:
            Union[Node, None]: GUI node of interest
        """
        logger.debug(f"return_uid: {return_uid}")
        self.nodes_layout.clear_widgets()
        gui_node_to_return = None
        n = self.pipeline_model.num_nodes
        self.set_pipeline_header(f"Pipeline: {n} nodes")
        for i in range(n):
            node = self.pipeline_model.get_node_by_index(i)
            node_num = i + 1
            gui_node = Node(
                node.uid, node.node_title, node_num, height=self.node_height
            )
            logger.debug(f"node_num: {node_num} node_title: {node.node_title}")
            self.nodes_layout.add_widget(gui_node)

            if return_uid == node.uid:
                gui_node_to_return = gui_node
        return gui_node_to_return

    def update_nodes(self) -> None:
        """Update properties of all existing GUI nodes"""
        for child in self.nodes_layout.children:
            child.update(height=self.node_height)
        self.pipeline_header.height = self.node_height // 2
