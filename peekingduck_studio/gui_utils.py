#
# PeekingDuck Studio General Utilities
#
from typing import Any, Dict, List, Tuple
import logging
import os
from pathlib import Path
import platform
import yaml
from kivy.animation import Animation
from kivy.uix.widget import Widget
import peekingduck

NODE_RGBA_COLOR = {
    "augment": (142 / 255, 142 / 255, 142 / 255, 1),
    "dabble": (109 / 255, 106 / 255, 180 / 255, 1),
    "draw": (238 / 255, 103 / 255, 71 / 255, 1),
    "input": (238 / 255, 220 / 255, 146 / 255, 1),
    "model": (167 / 255, 226 / 255, 238 / 255, 1),
    "output": (150 / 255, 101 / 255, 86 / 255, 1),
    # "custom_nodes": (250 / 255, 240 / 255, 110 / 255, 1),
}
NODE_COLOR_SELECTED = (0.8, 0.8, 0.8, 0.3)
NODE_COLOR_CLEAR = (0, 0, 0, 0)
CONFIG_COLOR_SELECTED = (0.8, 0.8, 0.8, 0.3)
CONFIG_COLOR_CLEAR = (0, 0, 0, 0)
NODE_CONFIG_READONLY_KEYS = {"input", "output"}
NODE_CONFIG_RESERVED_KEYS = {
    "MODEL_NODES",
    "model_size",
    "weights",
    "weights_parent_dir",
}
CUSTOM_NODES = "custom_nodes"


def _get_path(filename: str):
    name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]

    if platform.system() == "Darwin":
        from AppKit import NSBundle

        file = NSBundle.mainBundle().pathForResource_ofType_(name, ext)
        return file or os.path.realpath(filename)
    return os.path.realpath(filename)


USER_HOME = Path.home()

#
# Helper method to make a Logger object
#
LOG_FILE = _get_path(f"{USER_HOME}/peekingduckstudio_log.txt")
# print(f"LOG_FILE={LOG_FILE}")
LOG_FORMAT_FILE = "%(filename)s:%(lineno)s - %(funcName)s() - %(message)s"
LOG_FORMAT_IO = "%(name)s - %(levelname)s - %(message)s"


def make_logger(name: str) -> logging.Logger:
    """Create and configure logger with given name

    Args:
        name (str): name of logger required

    Returns:
        logging.Logger: the named logger
    """
    logger = logging.getLogger(name)
    io_handler = logging.StreamHandler()
    io_handler.setLevel(logging.INFO)
    io_format = logging.Formatter(LOG_FORMAT_IO)
    io_handler.setFormatter(io_format)
    logger.addHandler(io_handler)
    fi_handler = logging.FileHandler(LOG_FILE)
    fi_handler.setLevel(logging.DEBUG)
    fi_format = logging.Formatter(LOG_FORMAT_FILE)
    fi_handler.setFormatter(fi_format)
    logger.addHandler(fi_handler)
    logger.setLevel(logging.DEBUG)
    return logger


# Make logger for this module
logger = make_logger(__name__)


#
# Helper methods for node configuration
#
def find_config_dirs(config_path: Path) -> List[Path]:
    """Get directories containing PeekingDuck configs"""
    files = config_path.glob("*")
    config_dirs = sorted([file for file in files if file.is_dir()])
    return config_dirs


def get_peekingduck_path() -> Path:
    """Return PeekingDuck full path"""
    pkd_path = peekingduck.__path__[0]
    return Path(pkd_path)


def guess_config_type(key: str, val: Any) -> str:
    """Guesstimate the type for given config key based on given value

    Args:
        key (str): given config key
        val (Any): given value

    Returns:
        str: the type
    """
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
        the_type = "str_path" if key.endswith("_path") else "str"
    else:
        the_type = "nonetype"
    return the_type


def guess_config_value_types(
    config_map: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, str]]:
    """Guesstimate and store all config value types

    Args:
        config_map (Dict[str, Dict[str, Any]]): the config map to parse

    Returns:
        Dict[str, Dict[str, str]]: map of node_title -> { config_key -> config_type }
    """
    # map node_title -> { config_key -> config_type }
    default_config_types: Dict[str, Dict[str, str]] = {}
    for node_title, default_config in config_map.items():
        logger.debug(f"{node_title}")
        config_type_map = {}  # map config_key -> config_type
        for k, v in default_config.items():
            if k in NODE_CONFIG_RESERVED_KEYS:
                continue  # skip reserved keys
            config_type = guess_config_type(k, v)
            logger.debug(f"  {k}: {config_type} = {v}")
            config_type_map[k] = config_type
        default_config_types[node_title] = config_type_map
    return default_config_types


def has_custom_nodes(cust_node_config_path: Path) -> bool:
    """Check if given path contains custom nodes config files

    Args:
        cust_node_config_path (Path): the path to check

    Returns:
        bool: True if has custom nodes config files, otherwise False
    """
    return cust_node_config_path.is_dir() and any(cust_node_config_path.iterdir())


def parse_configs(
    config_dirs: List[Path],
) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, Any]]]:
    """Parse PeekingDuck default node configurations.

    Args:
        config_dirs (List[Path]): List of node config directory paths

    Returns:
        Tuple[Dict, Dict]: map of node type -> list of node titles,
                            map of node title -> default node configs
    """
    # map node type -> list of node titles
    nodes_by_type: Dict[str, List[str]] = dict()
    # map node title -> node config
    default_config_map: Dict[str, Dict[str, Any]] = dict()
    for config in config_dirs:
        node_type = config.name
        logger.debug(f"node_type={node_type}")
        files = sorted(config.glob("*.yml"))
        # working data structures
        node_title_list = []
        for config_file in files:
            node_name = config_file.name[:-4]
            node_title = f"{node_type}.{node_name}"
            logger.debug(f"  node_name={node_name}, node_title={node_title}")
            with open(config_file) as file:
                node_config = yaml.safe_load(file)
            logger.debug(node_config)
            default_config_map[node_title] = node_config
            node_title_list.append(node_title)
        nodes_by_type[node_type] = node_title_list
    return nodes_by_type, default_config_map


#
# Helper methods for pipeline node management
#
def get_node_type(node_title: str) -> str:
    """Get node type from node title = *.node_type.node_name where * = 'CUSTOM_NODES'

    Args:
        node_title (str): the node title to parse

    Returns:
        str: the node type
    """
    tokens = node_title.split(".")
    node_type = tokens[1] if tokens[0] == CUSTOM_NODES else tokens[0]
    return node_type


def get_node_name(node_title: str) -> str:
    """Get node name from node title = *.node_type.node_name where * = 'CUSTOM_NODES'

    Args:
        node_title (str): the node title to parse

    Returns:
        str: the node name
    """
    tokens = node_title.split(".")
    return tokens[-1]


def get_node_color(node_title: str) -> Tuple:
    """Get node color from node title

    Args:
        node_title (str): the node title to get color for

    Returns:
        Tuple: the RGBA color codes
    """
    node_type = get_node_type(node_title)
    node_color = NODE_RGBA_COLOR[node_type]
    return node_color


#
# Some animations just for fun
#
def shake_widget(thing: Widget) -> None:
    """Main animation used by PeekingDuck Studio

    Args:
        thing (Widget): Kivy widget to shake
    """
    delay = 0.05
    orig_pos = (thing.x, thing.y)  # error to link direct to thing.pos! need a copy
    left_pos = (thing.x - 2, thing.y - 2)
    right_pos = (thing.x + 2, thing.y + 2)
    logger.debug(f"orig_pos: {orig_pos} left_pos: {left_pos} right_pos: {right_pos}")
    anim = Animation(pos=left_pos, duration=delay)
    anim += Animation(pos=right_pos, duration=delay)
    anim += Animation(pos=left_pos, duration=delay)
    anim += Animation(pos=right_pos, duration=delay)
    anim += Animation(pos=left_pos, duration=delay)
    anim += Animation(pos=right_pos, duration=delay)
    anim += Animation(pos=orig_pos, duration=delay)
    anim.start(thing)


def up_down_widget(thing: Widget) -> None:
    # experimental
    delay = 0.10
    orig_size = (thing.width, thing.height)  # error to link direct to thing.size!
    smaller_size = (thing.width * 0.95, thing.height * 0.95)
    anim = Animation(size=smaller_size, duration=delay)
    anim += Animation(size=orig_size, duration=delay)
    anim += Animation(size=smaller_size, duration=delay)
    anim += Animation(size=orig_size, duration=delay)
    anim += Animation(size=smaller_size, duration=delay)
    anim += Animation(size=orig_size, duration=delay)
    anim.start(thing)


def vanish_widget(thing: Widget) -> None:
    # experimental
    delay = 1.00
    anim = Animation(size=(0, 0), duration=delay)
    anim.start(thing)
