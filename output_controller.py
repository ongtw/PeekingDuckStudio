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
from peekingduck.declarative_loader import DeclarativeLoader
from peekingduck.pipeline.pipeline import Pipeline
from config_parser import NodeConfigParser
from pipeline_model import ModelPipeline
from gui_widgets import Output

PLAYBACK_INTERVAL = 1 / 60
ZOOMS = [0.5, 0.75, 1.0, 1.25, 1.50, 2.00]
# Test unicode glyphs for zoom factors
# ZOOM_TEXT = ["\u00BD", "\u00BE", "1.0", "1\u00BC", "1\u00BD", "2.0"]
ZOOM_TEXT = ["0.5", "0.75", "1.0", "1.25", "1.50", "2.0"]


class OutputController:
    def __init__(self, config_parser: NodeConfigParser, pkd_view) -> None:
        self.config_parser: NodeConfigParser = config_parser
        self.pipeline_model: ModelPipeline = None
        self.output_header = pkd_view.ids["pkd_header"]
        self.output_layout: Output = pkd_view.ids["pkd_output"]
        self.controls = pkd_view.ids["pkd_controls"]
        self.play_stop_btn_parent = self.controls.ids["btn_play_stop"]
        self.output = self.output_layout.ids["image"]
        self.progress = None
        self.slider = self.output_layout.ids["slider"]
        self.zoom = self.output_layout.ids["zoom"]
        # make output display black (else it will be white by default)
        black_frame = np.empty((768, 1024, 3))
        self.blitz_texture(black_frame)
        self.zoom_idx = 2  # default 100% zoom
        # pipeline control vars
        self.pipeline_model: ModelPipeline = None
        self.frames = None
        self._pipeline_running = False
        self._output_playback = False

    @property
    def pipeline_running(self) -> bool:
        return self._pipeline_running

    def output_playback(self) -> bool:
        return self._output_playback

    def set_output_header(self, text: str) -> None:
        self.output_header.header_text = text

    def set_pipeline_model(self, pipeline_model: ModelPipeline) -> None:
        self.pipeline_model = pipeline_model

    #####################
    # Output playback
    #####################
    def play_stop(self) -> None:
        tag = self.play_stop_btn_parent.tag
        print(f"play_stop: tag={tag}")
        if tag == "play":
            self.set_play_stop_btn_to_stop()
            if self.pipeline_model.dirty:
                # play modified pipeline
                pipeline_str = self.config_parser.get_string_representation(
                    self.pipeline_model.node_list, self.pipeline_model.node_config
                )
                self.run_pipeline_start(pipeline_str)
                self.pipeline_model.clear_dirty_bit()
            else:
                # play last unmodified pipeline
                self.do_playback()
        else:
            self.set_play_stop_btn_to_play()
            if self._pipeline_running:
                self.stop_running_pipeline()
            elif self._output_playback:
                self.stop_playback()

    def do_playback(self, *args) -> None:
        self._output_playback = True
        if self._forward_one_frame():
            self.forward_one_frame_held = Clock.schedule_once(
                self.do_playback, PLAYBACK_INTERVAL
            )
        else:
            self.stop_playback()

    def _forward_one_frame(self) -> bool:
        if self.frame_idx + 1 < len(self.frames):
            self.frame_idx += 1
            self.show_frame()
            return True
        else:
            return False

    def _backward_one_frame(self) -> bool:
        if self.frame_idx > 0:
            self.frame_idx -= 1
            self.show_frame()
            return True
        else:
            return False

    def stop_playback(self) -> None:
        if hasattr(self, "forward_one_frame_held"):
            self.forward_one_frame_held.cancel()
        self._output_playback = False
        self.set_play_stop_btn_to_play()

    def set_play_stop_btn_to_play(self) -> None:
        self.play_stop_btn_parent.tag = "play"

    def set_play_stop_btn_to_stop(self) -> None:
        self.play_stop_btn_parent.tag = "stop"

    def forward_one_frame(self) -> bool:
        if self._pipeline_running or self._output_playback or self.frames is None:
            return False
        return self._forward_one_frame()

    def backward_one_frame(self) -> bool:
        if self._pipeline_running or self._output_playback or self.frames is None:
            return False
        return self._backward_one_frame()

    def goto_first_frame(self) -> None:
        if self._pipeline_running or self._output_playback or self.frames is None:
            return
        self.frame_idx = 0
        self.show_frame()

    def goto_last_frame(self) -> None:
        if self._pipeline_running or self._output_playback or self.frames is None:
            return
        self.frame_idx = len(self.frames) - 1
        self.show_frame()

    def enable_progress(self) -> None:
        self.progress = self.output_layout.ids["progress"]
        self.progress.max = self.num_frames
        self.progress.value = 0
        print(f"enable_progress: max={self.progress.max}")

    def disable_slider(self) -> None:
        self.slider.opacity = 0.0

    def enable_slider(self) -> None:
        self.slider = self.output_layout.ids["slider"]
        self.slider.opacity = 1.0
        self.slider.min = 1
        self.slider.max = len(self.frames)
        self.slider.step = 1
        self.slider.value = self.frame_idx
        self.slider.value_track = True
        self.slider.bind(value=self.slider_value_changed)

    def slider_value_changed(self, instance, value) -> None:
        # print(f"slider_value_changed: value={value}")
        self.frame_idx = value - 1
        self.show_frame()

    def disable_zoom(self) -> None:
        self.zoom.opacity = 0.0

    def enable_zoom(self) -> None:
        self.zoom.opacity = 1.0

    ####################
    # Pipeline execution
    ####################
    def run_pipeline_start(
        self, pipeline_str: str, custom_nodes_parent_subdir=None
    ) -> None:
        self.load_pipeline(pipeline_str, custom_nodes_parent_subdir)
        self.frames = []
        self.frame_idx = -1
        self.disable_slider()
        self.output_layout.install_progress_bar()
        self.enable_zoom()
        Clock.schedule_once(self.run_one_pipeline_iteration, PLAYBACK_INTERVAL)

    def run_pipeline_done(self, *args) -> None:
        # clean up nodes with threads
        for node in self.pipeline.nodes:
            if node.name.endswith(".visual"):
                node.release_resources()
        self.set_play_stop_btn_to_play()
        self._pipeline_running = False
        self.output_layout.install_slider()
        self.enable_slider()

    def run_one_pipeline_iteration(self, *args) -> None:
        self._pipeline_running = True
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
                # intercept screen output to Kivy
                img = self.pipeline.data["img"]
                # opencv top-left = (0,0), kivy bottom-left = (0,0)
                frame = cv2.flip(img, 0)  # flip around x-axis
                self.frames.append(frame)  # save frame for playback
                self.frame_idx += 1
                self.show_frame()
            else:
                outputs = node.run(inputs)
                self.pipeline.data.update(outputs)
            # check for FPS on first iteration
            if self.frame_idx == 0 and node.name.endswith("input.visual"):
                num_frames = node.total_frame_count
                if num_frames > 0:
                    self.num_frames = num_frames
                    self.enable_progress()
                else:
                    self.num_frames = 0
                    self.progress = None

        if self.progress:
            self.progress.value += 1

        if not self.pipeline.terminate:
            Clock.schedule_once(self.run_one_pipeline_iteration, PLAYBACK_INTERVAL)
        else:
            Clock.schedule_once(self.run_pipeline_done, PLAYBACK_INTERVAL)

    def stop_running_pipeline(self) -> None:
        self.pipeline.terminate = True

    def show_frame(self) -> None:
        frame = self.frames[self.frame_idx]
        frame = self.apply_zoom(frame)
        self.blitz_texture(frame)
        # mimic an observer pattern-like behavior...
        # not as cool as binding slider.value directly to self.frame_idx :(
        self.slider.value = self.frame_idx + 1

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
            self.update_zoom_text()

    def zoom_out(self) -> None:
        if self.zoom_idx > 0:
            self.zoom_idx -= 1
            self.update_zoom_text()

    def update_zoom_text(self) -> None:
        glyph = ZOOM_TEXT[self.zoom_idx]
        self.zoom.text = f"Zoom: {glyph}"
        self.show_frame()
