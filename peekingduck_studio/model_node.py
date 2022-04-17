#
# PeekingDuck Studio Model Node for Pipeline
# By DOTW (c) 2022
#
from typing import Any, Dict, List, Optional
import uuid

NO_USER_CONFIG = [{"None": "No Config"}]


class ModelNode:
    def __init__(
        self, node_title: str, user_config: Optional[List[Dict[str, Any]]] = None
    ) -> None:
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
    def user_config(self) -> List[Dict[str, Any]]:
        return self._user_config

    @user_config.setter
    def user_config(self, user_config: List[Dict[str, Any]]) -> None:
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
