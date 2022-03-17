import peekingduck
import yaml
from pathlib import Path


def get_peekingduck_path() -> Path:
    pkd_path = peekingduck.__path__[0]
    return Path(pkd_path)


class ConfigParser:
    def __init__(self) -> None:
        self.pkd_path = get_peekingduck_path()
        self.config_path = self.pkd_path / "configs"
        self.find_config_files()
        self.parse_configs()

    def find_config_files(self):
        files = self.config_path.glob("*")
        self.configs = sorted([file for file in files if file.is_dir()])
        # print("configs:", self.configs)

    def parse_configs(self):
        self.nodes_list = []
        self.nodes_by_type = dict()
        self.title_config_map = dict()
        self.pkd_config = dict()

        for config in self.configs:
            node_type = config.name
            # print(node_type)
            nodelist = []

            name_config_map = dict()
            files = sorted(config.glob("*.yml"))

            for config_file in files:
                node_name = config_file.name[:-4]
                # print(node_name)
                with open(config_file) as file:
                    node_config = yaml.safe_load(file)
                # print(node_config)
                name_config_map[node_name] = node_config
                node_title = f"{node_type}.{node_name}"

                self.title_config_map[node_title] = node_config
                nodelist.append(node_title)

            self.pkd_config[node_type] = name_config_map
            self.nodes_by_type[node_type] = nodelist
            self.nodes_list.extend(nodelist)

    def debug_configs(self):
        for node_type in self.pkd_config:
            print(f"{node_type}")

            nodes_map = self.pkd_config[node_type]
            for node_name in nodes_map:
                print(f"{node_type}.{node_name}")

                node_config = nodes_map[node_name]
                print(node_config)


def main():
    config_parser = ConfigParser()
    # config_parser.debug_configs()
    print(config_parser.nodes_list)
    print(config_parser.nodes_by_type)
    print(config_parser.title_config_map)


if __name__ == "__main__":
    main()