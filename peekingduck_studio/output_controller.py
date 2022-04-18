#
# PeekingDuck Studio Controller for Output Playback
#

from typing import Tuple
from contextlib import redirect_stderr
from pathlib import Path
import copy
import cv2
from io import StringIO
import numpy as np
import os
import yaml
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from tempfile import TemporaryDirectory
from peekingduck.declarative_loader import DeclarativeLoader
from peekingduck.pipeline.pipeline import Pipeline
from peekingduck_studio.colors import RED, GREEN, WHITE
from peekingduck_studio.config_parser import NodeConfigParser
from peekingduck_studio.model_pipeline import ModelPipeline
from peekingduck_studio.gui_widgets import Output, MsgBox, NODE_HEIGHT
from peekingduck_studio.gui_utils import make_logger

PLAYBACK_INTERVAL = 1 / 60
ZOOMS = [0.5, 0.75, 1.0, 1.25, 1.50, 2.00, 2.50, 3.00]  # > 3x is slow!
# Test unicode glyphs for zoom factors
# ZOOM_TEXT = ["\u00BD", "\u00BE", "1.0", "1\u00BC", "1\u00BD", "2.0"]
ZOOM_TEXT = ["0.5x", "0.75x", "1x", "1.25x", "1.5x", "2x", "2.5x", "3x"]

logger = make_logger(__name__)


class OutputController:
    def __init__(self, config_parser: NodeConfigParser, pkd_view) -> None:
        self.config_parser: NodeConfigParser = config_parser
        self.pipeline_model: ModelPipeline = None
        self.output_header = pkd_view.ids["pkd_header"]
        self.output_layout: Output = pkd_view.ids["pkd_output"]
        self.controls = pkd_view.ids["pkd_controls"]
        self.play_stop_btn_parent = self.controls.ids["btn_play_stop"]
        self.output_image = self.output_layout.ids["image"]
        self.progress = None
        self.slider = self.output_layout.ids["slider"]
        self.frame_counter = self.output_layout.ids["frame_counter"]
        self.zoom = self.output_layout.ids["zoom"]
        # make output display black (else it will be white by default)
        black_frame = np.empty((768, 1024, 3))
        self.zoom_idx = 2  # default 100% zoom
        self.blitz_texture(black_frame)
        # pipeline control vars
        self.pipeline_model: ModelPipeline = None
        self.frames = None
        self._pipeline_running = False
        self._output_playback = False
        self._node_height: int = NODE_HEIGHT

    @property
    def node_height(self) -> int:
        return self._node_height

    @node_height.setter
    def node_height(self, height: int) -> None:
        self._node_height = max(80, height)
        self.update_nodes()

    @property
    def pipeline_running(self) -> bool:
        return self._pipeline_running

    def output_playback(self) -> bool:
        return self._output_playback

    def set_output_header(self, text: str, color: Tuple = None) -> None:
        self.output_header.header_text = text
        if color:
            self.output_header.font_color = color

    def set_pipeline_model(self, pipeline_model: ModelPipeline) -> None:
        self.pipeline_model = pipeline_model

    #####################
    # Output playback
    #####################
    def replay(self) -> None:
        self.pipeline_model.set_dirty_bit()
        self.play_stop()

    def play_stop(self) -> None:
        tag = self.play_stop_btn_parent.tag
        logger.debug(f"tag={tag}")
        if tag == "play":
            self.set_play_stop_btn_to_stop()
            if self.pipeline_model.dirty:
                self.set_output_header(
                    f"Running {self.pipeline_model.filename}", color=RED
                )
                self.run_pipeline_start()  # play modified pipeline
            else:
                self.set_output_header(
                    f"Replaying {self.pipeline_model.filename}", color=GREEN
                )
                self.do_playback()  # play last unmodified pipeline
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
        return False

    def _backward_one_frame(self) -> bool:
        if self.frame_idx > 0:
            self.frame_idx -= 1
            self.show_frame()
            return True
        return False

    def stop_playback(self) -> None:
        if hasattr(self, "forward_one_frame_held"):
            self.forward_one_frame_held.cancel()
        self._output_playback = False
        self.set_play_stop_btn_to_play()

    def set_play_stop_btn_to_play(self) -> None:
        self.play_stop_btn_parent.tag = "play"
        self.set_output_header(self.pipeline_model.filename, color=WHITE)

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

    # Progress/Slider, Zoom
    def disable_progress(self) -> None:
        pass

    def enable_progress(self) -> None:
        self.progress = self.output_layout.ids["progress"]
        self.progress.max = self.num_frames
        self.progress.value = 0
        logger.debug(f"max={self.progress.max}")
        self.frame_counter.opacity = 1.0

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
        self.frame_counter.opacity = 1.0

    def slider_value_changed(self, instance, value) -> None:
        # logger.debug(f"value={value}")
        self.frame_idx = value - 1
        self.show_frame()

    def disable_zoom(self) -> None:
        self.zoom.opacity = 0.0

    def enable_zoom(self) -> None:
        self.zoom.opacity = 1.0

    ####################
    # Pipeline execution
    ####################
    def run_pipeline_start(self, custom_nodes_parent_subdir="src") -> None:
        def parse_streams(strio: StringIO) -> str:
            msg = strio.getvalue()
            msg = os.linesep.join([s for s in msg.splitlines() if s])
            return msg

        exc_msg: str = ""
        # _out = StringIO()
        _err = StringIO()
        # with redirect_stderr(_err), redirect_stdout(_out):
        with redirect_stderr(_err):
            try:
                pipeline_str = self.pipeline_model.get_string_representation()
                working_dir = self.pipeline_model.fileparent
                self.load_pipeline(
                    pipeline_str, working_dir, custom_nodes_parent_subdir
                )
                self.frames = []
                self.frame_idx = -1
                self.disable_slider()
                self.output_layout.install_progress_bar()
                self.enable_zoom()
                Clock.schedule_once(self.run_one_pipeline_iteration, PLAYBACK_INTERVAL)
            except BaseException as e:
                self.set_play_stop_btn_to_play()
                logger.exception("PeekingDuck Error!")
                # exc_msg = str(e)
                # logger.debug(f"exc_msg: {len(exc_msg)}")
                # logger.debug(exc_msg)

        err_msg = parse_streams(_err)
        # out_msg = parse_streams(_out)
        logger.debug(f"err_msg: {len(err_msg)}")
        logger.debug(err_msg)
        logger.debug(f"exc_msg: {len(exc_msg)}")
        logger.debug(exc_msg)
        # logger.debug(f"out_msg: {len(out_msg)}")
        # logger.debug(out_msg)

        if exc_msg:
            the_msg = err_msg if err_msg else exc_msg
            msgbox = MsgBox("PeekingDuck Runtime Error", the_msg, "Ok")
            msgbox.show()

    def run_pipeline_done(self, *args) -> None:
        # clean up nodes with threads
        for node in self.pipeline.nodes:
            if node.name.endswith("input.visual"):
                node.release_resources()
        self.set_play_stop_btn_to_play()
        self._pipeline_running = False
        self.output_layout.install_slider()
        self.enable_slider()
        self.pipeline_model.clear_dirty_bit()  # only if all ends well

    def run_one_pipeline_iteration(self, *args) -> None:
        # todo: capture runtime error msgs here
        try:
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
                    # (0,0) == opencv top-left == kivy bottom-left
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
        except BaseException as e:
            logger.exception("PeekingDuck Error!")
            # logger.debug(e)
            self.run_pipeline_done()
            self.disable_slider()
            self.pipeline_model.set_dirty_bit()  # but all is not well

    def stop_running_pipeline(self) -> None:
        self.pipeline.terminate = True

    def show_frame(self) -> None:
        if self.frames:
            frame = self.frames[self.frame_idx]
            frame = self.apply_zoom(frame)  # note: can speed up zoom?
            self.blitz_texture(frame)
            # mimic an observer pattern-like behavior...
            # not as cool as binding slider.value directly to self.frame_idx :(
            frame_count = self.frame_idx + 1
            self.slider.value = frame_count
            self.frame_counter.text = str(frame_count)

    def apply_zoom(self, frame: np.ndarray) -> np.ndarray:
        # logger.debug(f"zoom_idx={self.zoom_idx}")
        if self.zoom_idx != 2:
            # zoom image
            zoom = ZOOMS[self.zoom_idx]
            # logger.debug(f"img.shape = {img.shape}, zoom = {zoom}")
            new_size = (
                int(frame.shape[0] * zoom),
                int(frame.shape[1] * zoom),
                frame.shape[2],
            )
            # logger.debug(f"zoom image to {new_size}")
            # note: opencv is faster than scikit-image!
            frame = cv2.resize(frame, (new_size[1], new_size[0]))
        return frame

    def blitz_texture(self, frame: np.ndarray) -> None:
        # the good ol' graphics framebuffer bit blitz
        framebuffer = bytes(frame)
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt="bgr")
        texture.blit_buffer(framebuffer, colorfmt="bgr", bufferfmt="ubyte")
        self.output_image.texture = texture

        # # apply built-in zoom (experimental)
        # # dotw: doesn't work well 'coz image texture is rendered first on-screen, then
        # #       moved to its correct position, i.e. results in bad flicker!
        # zoom = ZOOMS[self.zoom_idx]
        # new_size = (int(frame.shape[1] * zoom), int(frame.shape[0] * zoom))
        # parent = self.output_image.parent
        # parent_size = parent.size
        # image_size = (
        #     min(new_size[0], parent_size[0]),
        #     min(new_size[1], parent_size[1]),
        # )
        # self.output_image.size = image_size
        # # logger.debug(f"image size: {self.output_image.size} in {type(parent)} {parent_size}")

    def load_pipeline(
        self, pipeline_str: str, working_dir: str, custom_nodes_parent_subdir: str
    ) -> None:
        """Convert YAML pipeline into internal Pipeline object by saving it into a temp
        'pipeline.yml' file and loading that using PeekingDuck's DeclarativeLoader class.

        Args:
            pipeline_str (str): YAML representation of pipeline
            working_dir (str): pipeline working directory
            custom_nodes_parent_subdir (str): folder containing custom nodes
        """
        if working_dir != ".":
            os.chdir(working_dir)
        else:
            working_dir = str(Path.home())
        # logger.debug(f"pipeline={pipeline_str}")
        # logger.debug(f"working_dir={working_dir}, cwd={os.getcwd()}")

        with TemporaryDirectory(dir=working_dir) as tempdir:
            logger.debug(f"tempdir={tempdir}")
            pipeline_path = os.path.join(tempdir, "pipeline.yml")
            with open(pipeline_path, "w") as tempfile:
                tempfile.writelines(pipeline_str)
            # # debug tempfile contents
            # logger.debug("tempfile:")
            # with open(pipeline_path, "r") as tempfile:
            #     logger.debug(tempfile.readline())
            # logger.debug("----------")
            # yaml safe load
            logger.debug("yaml")
            with open(pipeline_path, "r") as tempfile:
                the_yaml = yaml.safe_load(tempfile)
            logger.debug(the_yaml)
            logger.debug("-----")
            ss = yaml.dump(the_yaml, default_flow_style=None)
            logger.debug(ss)
            logger.debug("-----")
            self.node_loader = DeclarativeLoader(
                pipeline_path, "None", custom_nodes_parent_subdir
            )
            self.pipeline: Pipeline = self.node_loader.get_pipeline()
            logger.debug(f"self.pipeline: {self.pipeline}")

    def update_nodes(self) -> None:
        """Update UI properties of playback screen"""
        self.output_header.height = self.node_height // 2
        self.output_header.parent.height = self.output_header.height
