#
# PeekingDuck Studio Controller for Node Config
#
from typing import List
from kivy.clock import Clock
from kivy.metrics import Metrics
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
import ast
from peekingduck_studio.colors import BLACK, WHITE, GUI_COLOR
from peekingduck_studio.gui_utils import (
    CUSTOM_NODES,
    NODE_CONFIG_READONLY_KEYS,
    NODE_CONFIG_RESERVED_KEYS,
    NODE_RGBA_COLOR,
    get_node_name,
    get_node_type,
    guess_config_type,
    shake_widget,
    make_logger,
)
from peekingduck_studio.gui_widgets import NodeConfig, NODE_HEIGHT, NODE_PADDING
from peekingduck_studio.config_parser import NodeConfigParser
from peekingduck_studio.model_pipeline import ModelPipeline

NODE_TEXT_INPUT_DELAY = 0.5  # half second

logger = make_logger(__name__)


class ConfigController:
    def __init__(self, config_parser, pipeline_view, capture_keyboard_callback) -> None:
        self.pipeline_view = pipeline_view
        self.config_header = pipeline_view.ids["pipeline_config_header"]
        self.pipeline_config = pipeline_view.ids["pipeline_config"]
        self.config_layout = self.pipeline_config.ids["config_layout"]
        self.config_parser: NodeConfigParser = config_parser
        self.pipeline_model: ModelPipeline = None
        self.overlay: BoxLayout = None
        self._node_height: int = NODE_HEIGHT
        self.app_capture_keyboard_cb = capture_keyboard_callback

    @property
    def node_height(self) -> int:
        return self._node_height

    @node_height.setter
    def node_height(self, height: int) -> None:
        self._node_height = max(80, height)
        self.update_nodes()

    def set_pipeline_model(self, pipeline_model: ModelPipeline) -> None:
        """Cache ModelPipeline object within self and init node type spinner values

        Args:
            pipeline_model (ModelPipeline): the pipeline model
        """
        self.pipeline_model = pipeline_model
        # set node type spinner values once since it's invariant
        # don't set in __init__ 'coz pipeline not loaded and it can cause
        # spurious user selection
        spinner_node_type = self.config_header.ids["spinner_node_type"]
        self.all_node_types = self.config_parser.get_all_node_types()
        spinner_node_type.values = self.all_node_types

    def clear_node_configs(self) -> None:
        """Remove all node config widgets"""
        self.config_layout.clear_widgets()
        self.set_node_config_header("Node.Config")

    def config_double_tap(self, instance, *args) -> None:
        """Create text input overlay on double tapping widget

        Args:
            instance (Widget): the config instance to overlay upon
        """
        logger.debug(f"{type(instance)}: key={instance.config_key}")
        # Move scrollview so that config instance is fully visible,
        # but don't scroll if boxlayout.height < scrollview.height
        # 'coz nodes will flush towards bottom of scrollview and look weird
        parent = self.config_layout.parent
        if self.config_layout.height > parent.height:
            self.pipeline_config.scroll_to(instance)

        # instance.debug()
        overlay = instance.the_overlay
        key = instance.config_key
        val = instance.config_value
        logger.debug(f"instance: {type(instance)} {instance.size}")
        logger.debug(f"key: {key}, val: {val}, overlay: {overlay.pos} {overlay.size}")

        if key in NODE_CONFIG_READONLY_KEYS:
            shake_widget(instance)
            return
        if self.overlay:
            logger.debug("overlay present, exiting")
            return

        # configure TextInput overlay
        # logger.debug(f"instance ids: {instance.ids}")
        btn_config_val = instance.ids["id_btn_config"]
        text_input = TextInput(
            multiline=False,
            pos=overlay.pos,
            size=overlay.size,
            # font_size=18 * Metrics.sp,
            font_size=btn_config_val.font_size * 1.2,
            halign="center",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            text=val,
        )
        text_input.bind(on_text_validate=self.text_input_on_enter)
        text_input.bind(focus=self.text_input_on_focus)
        # to simulate valign="center" since it's not available for TextInput
        # padding = [left, top, right, bottom]
        top_padding = (
            text_input.height - 2 * NODE_PADDING - text_input.line_height
        ) // 2.0
        text_input.padding = [
            Metrics.dp * i
            for i in [NODE_PADDING, top_padding, NODE_PADDING, NODE_PADDING]
        ]
        logger.debug(
            f"text_input: height={text_input.height}, line_height={text_input.line_height}"
            f", padding: {text_input.padding}"
        )
        overlay.add_widget(text_input)
        self.overlay = overlay
        # dotw: trick to get text input overlay working...
        #       doing a TextInput(..., focus=True) does not work 'coz widget will get
        #       focus but cannot type, so let overlay widget refresh itself, then
        #       trigger a focus on the TextInput widget.
        Clock.schedule_once(self.do_focus_on_text_input, NODE_TEXT_INPUT_DELAY)

    def do_focus_on_text_input(self, *args):
        """To autofocus on the overlay text input widget so that user can
        begin keyboard data entry.

        Args:
            args (_type_): clock scheduler args
        """
        logger.debug(f"args={args}")
        self.overlay.children[0].focus = True

    def text_input_on_enter(self, instance, *args):
        """Handle text input on_enter event

        Args:
            instance (_type_): the text input widget
        """
        logger.debug(f"instance={instance} args={args}")
        logger.debug(f"text={instance.text}")

    def text_input_on_focus(self, instance, value, *args):
        """Handle text input on_focus event.
        If lose focus, update node config with text input values

        Args:
            instance (_type_): the text input widget
            value (_type_): whether in or out of focus
        """
        logger.debug(f"focus={value} instance={instance} args={args}")
        if not value:
            # out of focus, disable overlay TextInput
            assert self.overlay
            great_grandparent = instance.parent.parent.parent
            # logger.debug(f"great_grandparent: {great_grandparent}")
            val = instance.text
            great_grandparent.config_value = val
            key = great_grandparent.config_key
            # logger.debug(f"key={key} val={val} node_configs={self.node.user_config}")

            # check user input type matches default config type
            try:
                val_eval = ast.literal_eval(val)
            except:
                val_eval = val
            node = self.pipeline_model.get_node_by_uid(self.node_uid)
            node_title = node.node_title
            default_type = self.config_parser.get_default_config_type(node_title, key)
            val_type = guess_config_type(key, val_eval)
            logger.debug(
                f"Check '{key}' type: default {default_type} =? user_input {val_type}"
            )
            if default_type != val_type:
                logger.debug("** NOT EQUAL **")
            self.set_node_config(key, val)
            self.overlay.clear_widgets()
            self.overlay = None

            # restore main app's ability to intercept keyboard
            self.app_capture_keyboard_cb()

            # refresh config display
            self.show_node_configs(self.node_uid, focus_on_config=key)

    def get_config_header_node_title(self) -> str:
        """Get current config header node title

        Returns:
            str: node title desired
        """
        header = self.config_header
        node_title = f"{header.node_type}.{header.node_name}"
        if self.config_parser.is_custom_node(node_title):
            node_title = f"{CUSTOM_NODES}.{node_title}"
        return node_title

    def set_node_config_header(
        self,
        node_title: str,
    ) -> None:
        """Set config header to given node title

        Args:
            node_title (str): new node title for config header
        """
        logger.debug(f"node_title: {node_title}")
        node_type = get_node_type(node_title)
        node_name = get_node_name(node_title)
        # NB: set new list of node names _before_ setting node type and name
        self.set_node_names(node_type)
        self.set_node_type_and_name_no_callback(node_type, node_name)
        self.set_config_header_colors(node_type)

    def set_node_type_and_name_no_callback(
        self, node_type: str = None, node_name: str = None
    ) -> None:
        """Change config header node type and/or node name without triggering callbacks

        Args:
            node_type (str, optional): the node type. Defaults to None.
            node_name (str, optional): the node name. Defaults to None.
        """
        header = self.config_header
        header.state = "disabled"  # disable callbacks when setting node type and name
        if node_type:
            header.node_type = node_type
        if node_name:
            header.node_name = node_name
        header.state = "enabled"

    def set_config_header_colors(self, node_type: str) -> None:
        """Set config header to color determined by node type

        Args:
            node_type (str): the node type to choose color
        """
        header = self.config_header
        if node_type == "Node":  # set GUI colors
            header.header_color = GUI_COLOR
            header.font_color = WHITE
        else:  # set colors according to selected node
            node_color = NODE_RGBA_COLOR[node_type]
            header.header_color = node_color
            header.font_color = BLACK

    def set_node_names(self, node_type: str) -> None:
        """Set node name spinner values dynamically based on given node type

        Args:
            node_type (str): given node type
        """
        if node_type not in self.all_node_types:
            # ignore "Node.Config"
            return
        all_node_titles = self.config_parser.get_all_node_titles(node_type)
        all_node_names = [get_node_name(node_title) for node_title in all_node_titles]
        spinner_node_names = self.config_header.ids["spinner_node_name"]
        spinner_node_names.values = all_node_names
        self.set_node_type_and_name_no_callback(node_name=all_node_names[0])
        self.set_config_header_colors(node_type)

    def set_node_config(self, key: str, val: str) -> None:
        """Update node config with given key to given value

        Args:
            key (str): config key to update
            val (str): new config value to replace old value
        """
        # ast.literal_eval will crash on strings (e.g. "v4tiny"),
        # so need to catch exception and assume string as baseline
        try:
            val_eval = ast.literal_eval(val)
        except:
            val_eval = val
        logger.debug(f"val: {type(val)} {val}")

        node = self.pipeline_model.get_node_by_uid(self.node_uid)
        default_val = self.config_parser.get_default_value(node.node_title, key)
        logger.debug(
            f"Check {val_eval} {type(val_eval)} =? {default_val} {type(default_val)}"
        )

        for i, config in enumerate(node.user_config):
            if key in config:
                # if user value == default value, remove config[key]
                if val_eval == default_val:
                    logger.debug(f"remove {i} {config}")
                    self.pipeline_model.pop_user_config(node.uid, key)
                else:
                    logger.debug(f"different, change {i} config[{key}]")
                    self.pipeline_model.set_user_config(node.uid, key, val_eval)
                return  # always return since something is updated
        # if different from default value, add as new user config
        if val_eval != default_val:
            logger.debug(f"add new user config {key}")
            self.pipeline_model.set_user_config(node.uid, key, val_eval)

    def reset_node_config_to_default(self, key: str) -> None:
        """Reset node config with given key to default value

        Args:
            key (str): config key to reset
        """
        node = self.pipeline_model.get_node_by_uid(self.node_uid)
        default_val = self.config_parser.get_default_value(node.node_title, key)
        self.set_node_config(key, default_val)
        # refresh config display
        self.show_node_configs(self.node_uid, focus_on_config=key)

    def show_node_configs(self, uid: str = None, focus_on_config: str = None) -> None:
        """Show configuration for given node

        Args:
            uid (str): uuid of node
            focus_on_config (str): node configuration entry to focus on
        """
        user_config: List = []
        # reference to current node
        self.node_uid = uid
        if uid:
            node = self.pipeline_model.get_node_by_uid(uid)
            user_config = node.user_config
            logger.debug(f"user_config={user_config}")
            node_title = node.node_title
            self.set_node_config_header(node_title)
        else:
            node_title = self.get_config_header_node_title()
            # to deal with no selected nodes, i.e. no node config
            if node_title.startswith("Node."):
                return

        config_layout = self.config_layout
        config_layout.clear_widgets()
        # need to make a copy else configs will get overridden by user updates
        default_config = self.config_parser.get_default_configs(node_title).copy()
        # replace default with user config
        user_config_keys = set()
        for config in user_config:
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
                    the_type = self.config_parser.get_default_config_type(node_title, k)
                    config = NodeConfig(
                        config_key=str(k),
                        config_type=the_type,
                        config_value=str(v).replace("'", '"'),
                        config_set=tick,
                        config_readonly=k in NODE_CONFIG_READONLY_KEYS,
                        callback_double_tap=self.config_double_tap,
                        # has_tooltip=True,
                        height=self.node_height,
                    )
                    config_layout.add_widget(config)
                    # logger.debug(f"draw_config: {k}: {the_type} = {v}")
                    no_config = False
                if k == focus_on_config:
                    config_to_focus = config  # save for later focus
        if no_config:
            # add dummy widget showing "No Config" message
            config = NodeConfig(
                config_key="",
                config_type="nonetype",
                config_value="No user defined configurations",
                config_set=False,
                callback_double_tap=None,
                height=self.node_height,
            )
            config_layout.add_widget(config)

        if focus_on_config:
            parent = self.config_layout.parent
            if self.config_layout.height > parent.height:
                self.pipeline_config.scroll_to(config_to_focus)
        else:
            self.pipeline_config.scroll_y = 1.0  # move scrollview to top

        # config.debug()

    def update_nodes(self):
        """Update properties of all existing GUI config nodes"""
        for child in self.config_layout.children:
            child.update(height=self.node_height)
        self.config_header.height = self.node_height // 2
        self.config_header.parent.height = self.config_header.height
