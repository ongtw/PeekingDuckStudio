#
# PeekingDuck GUI Controller for Output Playback
#

import copy
import os
import cv2
import numpy as np
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from tempfile import TemporaryDirectory
from peekingduck.declarative_loader import DeclarativeLoader, NodeList
from peekingduck.pipeline.pipeline import Pipeline

PLAYBACK_INTERVAL = 1 / 60
ZOOMS = [0.5, 0.75, 1.0, 1.25, 1.50, 2.00]


class OutputController:
    def __init__(self, output_image) -> None:
        self.output = output_image
        self._pipeline_is_running = False
        # make output display black (else it will be white by default)
        black_frame = np.empty((768, 1024, 3))
        self.blitz_texture(black_frame)
        self.zoom_idx = 2  # default 100% zoom

    @property
    def pipeline_running(self) -> bool:
        return self._pipeline_is_running

    def run_pipeline_start(
        self, pipeline_str: str, custom_nodes_parent_subdir=None
    ) -> None:
        self.load_pipeline(pipeline_str, custom_nodes_parent_subdir)
        self.frames = []
        self.frame_idx = -1
        if not self.pipeline.terminate:
            Clock.schedule_once(self.run_one_pipeline_iteration, PLAYBACK_INTERVAL)

    def run_pipeline_done(self, *args) -> None:
        # clean up nodes with threads
        for node in self.pipeline.nodes:
            if node.name.endswith(".visual"):
                node.release_resources()
        self._pipeline_is_running = False

    def run_one_pipeline_iteration(self, *args) -> None:
        self._pipeline_is_running = True
        for node in self.pipeline.nodes:
            if self.pipeline.data.get("pipeline_end", False):
                self.pipeline.terminate = True
                if "pipeline_end" not in node.inputs:
                    continue
            if "all" in node.inputs:
                inputs = copy.deepcopy(self.pipeline.data)
            else:
                inputs = {
                    key: self.pipeline.data[key]
                    for key in node.inputs
                    if key in self.pipeline.data
                }
            if hasattr(node, "optional_inputs"):
                for key in node.optional_inputs:
                    # The nodes will not receive inputs with the optional
                    # key if it's not found upstream
                    if key in self.pipeline.data:
                        inputs[key] = self.pipeline.data[key]
            if node.name.endswith("output.screen"):
                # print(f"intercept {node.name}")
                img = self.pipeline.data["img"]
                # opencv top-left = (0,0), kivy bottom-left = (0,0)
                frame = cv2.flip(img, 0)  # flip around x-axis
                self.frames.append(frame)  # save frame for playback
                self.frame_idx += 1
                frame = self.apply_zoom(frame)
                self.blitz_texture(frame)
            else:
                outputs = node.run(inputs)
                self.pipeline.data.update(outputs)

        if not self.pipeline.terminate:
            Clock.schedule_once(self.run_one_pipeline_iteration, PLAYBACK_INTERVAL)
        else:
            Clock.schedule_once(self.run_pipeline_done, PLAYBACK_INTERVAL)

    def stop_running_pipeline(self) -> None:
        self.pipeline.terminate = True

    def show_frame(self, idx: int) -> None:
        frame = self.frames[idx]
        frame = self.apply_zoom(frame)
        self.blitz_texture(frame)

    def forward_one_frame(self) -> bool:
        if self._pipeline_is_running:
            return False
        if self.frame_idx + 1 < len(self.frames):
            self.frame_idx += 1
            self.show_frame(self.frame_idx)
            return True
        else:
            return False

    def backward_one_frame(self) -> bool:
        if self._pipeline_is_running:
            return False
        if self.frame_idx > 0:
            self.frame_idx -= 1
            self.show_frame(self.frame_idx)
            return True
        else:
            return False

    def goto_first_frame(self) -> None:
        if self._pipeline_is_running:
            return
        self.frame_idx = 0
        self.show_frame(self.frame_idx)

    def goto_last_frame(self) -> None:
        if self._pipeline_is_running:
            return
        self.frame_idx = len(self.frames) - 1
        self.show_frame(self.frame_idx)

    def apply_zoom(self, frame: np.ndarray) -> np.ndarray:
        # print(f"zoom_idx={self.zoom_idx}")
        if self.zoom_idx != 2:
            # zoom image
            zoom = ZOOMS[self.zoom_idx]
            # print(f"img.shape = {img.shape}, zoom = {zoom}")
            new_size = (int(frame.shape[0] * zoom), int(frame.shape[1] * zoom))
            # print(f"zoom image to {new_size}")
            frame = cv2.resize(frame, (new_size[1], new_size[0]))
        return frame

    def blitz_texture(self, frame: np.ndarray) -> None:
        # the good ol' graphics framebuffer bit blitz
        framebuffer = bytes(frame)
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt="bgr")
        texture.blit_buffer(framebuffer, colorfmt="bgr", bufferfmt="ubyte")
        self.output.texture = texture

    def load_pipeline(self, pipeline_str: str, custom_nodes_parent_subdir: str) -> None:
        print(f"pipeline={pipeline_str}")
        with TemporaryDirectory() as tempdir:
            print(f"tempdir={tempdir}")
            pipeline_path = os.path.join(tempdir, "pipeline.yml")
            with open(pipeline_path, "w") as tempfile:
                tempfile.writelines(pipeline_str)
            # print("tempfile contents:")
            # with open(tempfilename, "r") as tempfile:
            #     print(tempfile.readline())
            self.node_loader = DeclarativeLoader(
                pipeline_path, "None", custom_nodes_parent_subdir
            )
            self.pipeline: Pipeline = self.node_loader.get_pipeline()
            print(f"self.pipeline: {self.pipeline}")

    def zoom_in(self) -> None:
        if self.zoom_idx + 1 < len(ZOOMS):
            self.zoom_idx += 1

    def zoom_out(self) -> None:
        if self.zoom_idx > 0:
            self.zoom_idx -= 1
