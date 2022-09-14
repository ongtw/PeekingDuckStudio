#
# PeekingDuck Studio Controller for Output Playback
#

from typing import List, Tuple
from contextlib import redirect_stderr
from datetime import datetime
from pathlib import Path
import copy
import cv2
from io import StringIO
import numpy as np
import os
import traceback
import yaml
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from tempfile import TemporaryDirectory
from peekingduck.declarative_loader import DeclarativeLoader
from peekingduck.pipeline.pipeline import Pipeline
from peekingduck_studio.colors import RED, GREEN, WHITE
from peekingduck_studio.model_pipeline import ModelPipeline
from peekingduck_studio.gui_widgets import Output, MsgBox, NODE_HEIGHT
from peekingduck_studio.gui_utils import make_logger

PLAYBACK_INTERVAL = 1 / 60
ZOOMS = [0.5, 0.75, 1.0, 1.25, 1.50, 2.00, 2.50, 3.00]  # > 3x is slow!
# Test unicode glyphs for zoom factors
# ZOOM_TEXT = ["\u00BD", "\u00BE", "1.0", "1\u00BC", "1\u00BD", "2.0"]
ZOOM_TEXT = ["0.5x", "0.75x", "1x", "1.25x", "1.5x", "2x", "2.5x", "3x"]

logger = make_logger(__name__)


def parse_streams(strio: StringIO) -> str:
    """Helper method to parse I/O streams.
    Used to capture errors/exceptions from PeekingDuck.

    Args:
        strio (StringIO): the I/O stream to parse

    Returns:
        str: parsed stream
    """
    msg = strio.getvalue()
    msg = os.linesep.join([s for s in msg.splitlines() if s])
    return msg


class OutputController:
    def __init__(self, pkd_view) -> None:
        self._pipeline_model: ModelPipeline = None
        self.output_header = pkd_view.ids["pkd_header"]
        self.output_layout: Output = pkd_view.ids["pkd_output"]
        self.controls = pkd_view.ids["pkd_controls"]
        self.btn_play_stop = self.controls.ids["btn_play_stop"]
        self.btn_loop = self.controls.ids["btn_loop"]
        self.output_image = self.output_layout.ids["image"]
        self.progress = None
        self.slider = self.output_layout.ids["slider"]
        self.frame_counter = self.output_layout.ids["frame_counter"]
        self.zoom = self.output_layout.ids["zoom"]
        self.zoom_idx = 2  # default 100% zoom
        # make output display black (else it will be white by default)
        self._black_frame = np.empty((768, 1024, 3))
        self._blitz_texture(self._black_frame)
        # pipeline control vars
        self.frames: List = None
        self._pipeline_model: ModelPipeline = None
        self._pipeline_running: bool = False
        self._output_playback: bool = False
        self._node_height: int = NODE_HEIGHT

    @property
    def node_height(self) -> int:
        return self._node_height

    @node_height.setter
    def node_height(self, height: int) -> None:
        self._node_height = max(80, height)
        self._update_nodes()

    @property
    def pipeline_running(self) -> bool:
        return self._pipeline_running

    def _set_output_header(self, text: str, color: Tuple = None) -> None:
        """Set Output header text and optional color

        Args:
            text (str): new header text
            color (Tuple, optional): header text color.
                                     Defaults to None which uses preset color.
        """
        self.output_header.header_text = text
        if color:
            self.output_header.font_color = color

    #####################
    # External interfaces: called from outside of OutputController
    #####################
    def set_pipeline_model(self, pipeline_model: ModelPipeline) -> None:
        """Set internal pipeline model based on current pipeline

        Args:
            pipeline_model (ModelPipeline): the pipeline model
        """
        self._pipeline_model = pipeline_model

    def backward_one_frame(self) -> bool:
        """Move back one frame"""
        if self._pipeline_running or self._output_playback or self.frames is None:
            return False
        return self._backward_one_frame()

    def forward_one_frame(self) -> bool:
        """Move forward one frame"""
        if self._pipeline_running or self._output_playback or self.frames is None:
            return False
        return self._forward_one_frame()

    def goto_first_frame(self) -> None:
        """Goto first frame of playback"""
        if self._pipeline_running or self._output_playback or self.frames is None:
            return
        self.frame_idx = 0
        self._show_frame()

    def goto_last_frame(self) -> None:
        """Goto last frame of playback"""
        if self._pipeline_running or self._output_playback or self.frames is None:
            return
        self.frame_idx = len(self.frames) - 1
        self._show_frame()

    def play_stop(self) -> None:
        """Toggle play/stop button and play/stop output playback accordingly"""
        tag = self.btn_play_stop.tag
        logger.debug(f"current tag={tag}")
        if tag == "play":
            self._toggle_btn_play_stop(state="stop")
            if self._pipeline_model.dirty:
                self._set_output_header(
                    f"Running {self._pipeline_model.filename}", color=RED
                )
                self._run_pipeline_start()  # play modified pipeline
            else:
                self._set_output_header(
                    f"Replaying {self._pipeline_model.filename}", color=GREEN
                )
                self._do_playback()  # play last unmodified pipeline
        else:
            if self._pipeline_running:
                self._stop_running_pipeline()
            elif self._output_playback:
                self._stop_playback()

    def rerun_pipeline(self) -> None:
        """Cause PeekingDuck to rerun entire pipeline by setting its dirty bit"""
        self._pipeline_model.set_dirty_bit()
        self.play_stop()

    def toggle_btn_loop(self) -> None:
        self.btn_loop.depressed = not self.btn_loop.depressed

    def zoom_in(self) -> None:
        """Zoom in: make image larger"""
        if self.zoom_idx + 1 < len(ZOOMS):
            self.zoom_idx += 1
            self._update_zoom_text()

    def zoom_out(self) -> None:
        """Zoom out: make image smaller"""
        if self.zoom_idx > 0:
            self.zoom_idx -= 1
            self._update_zoom_text()

    ################
    # Internal methods: used within OutputController
    ################
    def _backward_one_frame(self) -> bool:
        """Internal method to move back one frame, can be called repeatedly"""
        if self.frame_idx > 0:
            self.frame_idx -= 1
            self._show_frame()
            return True
        return False

    def _forward_one_frame(self) -> bool:
        """Internal method to move forward one frame, can be called repeatedly"""
        if self.frame_idx + 1 < len(self.frames):
            self.frame_idx += 1
            self._show_frame()
            return True
        return False

    def _do_playback(self, *args) -> None:
        """Playback the output, called repeatedly by clock scheduler until stop"""
        self._output_playback = True
        if self._forward_one_frame():
            self.forward_one_frame_held = Clock.schedule_once(
                self._do_playback, PLAYBACK_INTERVAL
            )
        else:
            self._stop_playback()
            # print(f"btn_loop.depressed={self.btn_loop.depressed}")
            if self.btn_loop.depressed:  # auto loop video
                self.goto_first_frame()
                self.play_stop()

    def _stop_playback(self) -> None:
        """Stop output playback"""
        if hasattr(self, "forward_one_frame_held"):
            self.forward_one_frame_held.cancel()
        self._output_playback = False
        self._toggle_btn_play_stop(state="play")

    def _toggle_btn_play_stop(self, state: str) -> None:
        """Set Play/Stop button state to given state and perform any necessary
        housekeeping tasks.

        Args:
            state (str): either "play" / "stop"
        """
        assert state in ["play", "stop"]
        self.btn_play_stop.tag = state
        logger.debug(f"new state={self.btn_play_stop.tag}")
        if state == "play":
            self._set_output_header(self._pipeline_model.filename, color=WHITE)

    def _update_zoom_text(self) -> None:
        """Databinding for zoom -> image"""
        glyph = ZOOM_TEXT[self.zoom_idx]
        self.zoom.text = f"Zoom: {glyph}"
        self._show_frame()

    ####################
    # Output display widget management: hide/show progress/slider/zoom
    ####################
    # def disable_progress(self) -> None:
    #     pass  # not used

    def _enable_progress(self) -> None:
        """Make progress bar visible and reset its properties for playback"""
        self.progress = self.output_layout.ids["progress"]
        self.progress.max = self.num_frames
        self.progress.value = 0
        logger.debug(f"max={self.progress.max}")
        self.frame_counter.opacity = 1.0

    def _disable_slider(self) -> None:
        """Make slider invisible"""
        self.slider.opacity = 0.0

    def _enable_slider(self) -> None:
        """Make slider visible and reset its properties for playback"""
        self.slider = self.output_layout.ids["slider"]
        self.slider.opacity = 1.0
        self.slider.min = 1
        self.slider.max = len(self.frames)
        self.slider.step = 1
        self.slider.value = self.frame_idx
        self.slider.value_track = True
        self.slider.bind(value=self._slider_value_changed)
        self.frame_counter.opacity = 1.0

    def _slider_value_changed(self, instance, value: int) -> None:
        """Databinding for slider -> image

        Args:
            instance (Widget): slider instance
            value (int): slider value
        """
        # logger.debug(f"value={value}")
        self.frame_idx = value - 1
        self._show_frame()

    def _disable_zoom(self) -> None:
        """Make zoom widget invisible"""
        self.zoom.opacity = 0.0

    def _enable_zoom(self) -> None:
        """Make zoom widget visible"""
        self.zoom.opacity = 1.0

    ####################
    # Pipeline execution
    ####################
    def _run_pipeline_done(self, *args) -> None:
        """Called when pipeline execution is completed.
        To perform clean-up/housekeeping tasks to ensure system consistency"""
        for node in self.pipeline.nodes:
            if node.name.endswith("input.visual"):
                node.release_resources()  # clean up nodes with threads
        self._toggle_btn_play_stop(state="play")
        self._pipeline_running = False
        self.output_layout.install_slider()
        self._enable_slider()
        self._pipeline_model.clear_dirty_bit()  # only if all ends well

    def _run_pipeline_start(self, custom_nodes_parent_subdir="src") -> None:
        """Start pipeline execution by
        a) loading pipeline
        b) preparing Output widgets for playback
        c) starting clock scheduler for subsequent pipeline iterations
        d) capturing any PeekingDuck errors that arise from starting the pipeline

        Args:
            custom_nodes_parent_subdir (str, optional): custom nodes folder.
                                                        Defaults to "src".
        """
        exc_msg: str = ""
        # _out = StringIO()
        _err = StringIO()
        # with redirect_stderr(_err), redirect_stdout(_out):
        with redirect_stderr(_err):
            try:
                pipeline_str = self._pipeline_model.get_string_representation()
                working_dir = self._pipeline_model.fileparent
                self._load_pipeline(
                    pipeline_str, working_dir, custom_nodes_parent_subdir
                )
                self.frames = []
                self.frame_idx = -1
                self._disable_slider()
                self.output_layout.install_progress_bar()
                self._enable_zoom()
                Clock.schedule_once(self._run_one_pipeline_iteration, PLAYBACK_INTERVAL)
            except BaseException as e:
                self._toggle_btn_play_stop(state="play")
                logger.exception("PeekingDuck Error!")
                # exc_msg = str(e)
                exc_msg = traceback.format_exc()
                # logger.debug(f"exc_msg: {len(exc_msg)}")
                # logger.debug(exc_msg)

        # out_msg = parse_streams(_out)
        # logger.debug(f"out_msg: {len(out_msg)}")
        # logger.debug(out_msg)
        err_msg = parse_streams(_err)
        if err_msg:
            logger.debug(f"err_msg: {len(err_msg)}")
            logger.debug(err_msg)
        if exc_msg:
            logger.debug(f"exc_msg: {len(exc_msg)}")
            logger.debug(exc_msg)
            the_msg = err_msg if err_msg else exc_msg
            msgbox = MsgBox("PeekingDuck Runtime Error", the_msg, "Ok")
            msgbox.show()

    def _run_one_pipeline_iteration(self, *args) -> None:
        """Execute one iteration of the pipeline"""
        exc_msg: str = ""
        _err = StringIO()
        with redirect_stderr(_err):
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
                        self._show_frame()
                    else:
                        outputs = node.run(inputs)
                        self.pipeline.data.update(outputs)
                    # check for FPS on first iteration
                    if self.frame_idx == 0 and node.name.endswith("input.visual"):
                        num_frames = node.total_frame_count
                        if num_frames > 0:
                            self.num_frames = num_frames
                            self._enable_progress()
                        else:
                            self.num_frames = 0
                            self.progress = None

                if self.progress:
                    self.progress.value += 1

                if not self.pipeline.terminate:
                    Clock.schedule_once(
                        self._run_one_pipeline_iteration, PLAYBACK_INTERVAL
                    )
                else:
                    Clock.schedule_once(self._run_pipeline_done, PLAYBACK_INTERVAL)
            except BaseException as e:
                logger.exception("PeekingDuck Error!")
                # exc_msg = str(e)
                exc_msg = traceback.format_exc()
                self._run_pipeline_done()
                self._disable_slider()
                self._pipeline_model.set_dirty_bit()  # but all is not well

        err_msg = parse_streams(_err)
        if err_msg:
            logger.debug(f"err_msg: {len(err_msg)}")
            logger.debug(err_msg)
        if exc_msg:
            logger.debug(f"exc_msg: {len(exc_msg)}")
            logger.debug(exc_msg)
            the_msg = err_msg if err_msg else exc_msg
            msgbox = MsgBox("PeekingDuck Runtime Error", the_msg, "Ok")
            msgbox.show()

    def _stop_running_pipeline(self) -> None:
        """Signals pipeline execution to be stopped"""
        self.pipeline.terminate = True

    def _show_frame(self) -> None:
        """Renders image frame pointed to by the index self.frame_idx"""
        if self.frames:
            frame = self.frames[self.frame_idx]
            frame = self._apply_zoom(frame)  # note: can speed up zoom?
            self._blitz_texture(frame)
            # mimic an observer pattern-like behavior...
            # not as cool as binding slider.value directly to self.frame_idx :(
            frame_count = self.frame_idx + 1
            self.slider.value = frame_count
            self.frame_counter.text = str(frame_count)

    def _apply_zoom(self, frame: np.ndarray) -> np.ndarray:
        """Zoom output image in real-time

        Args:
            frame (np.ndarray): image frame data to be zoomed

        Returns:
            np.ndarray: the zoomed image
        """
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

    def _blitz_texture(self, frame: np.ndarray) -> None:
        """The good ol' graphics framebuffer bit blitz

        Args:
            frame (np.ndarray): image frame data to be blitz'd
        """
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

    def _load_pipeline(
        self, pipeline_str: str, working_dir: str, custom_nodes_parent_subdir: str
    ) -> None:
        """Convert YAML pipeline into internal Pipeline object by saving it into a temp
        working pipeline file and loading that using PeekingDuck's DeclarativeLoader class.

        Args:
            pipeline_str (str): YAML representation of pipeline
            working_dir (str): pipeline working directory
            custom_nodes_parent_subdir (str): folder containing custom nodes
        """
        if working_dir != ".":
            os.chdir(working_dir)
        else:
            working_dir = str(Path.home())

        logger.debug(f"pipeline_data={pipeline_str}")
        logger.debug(f"working_dir={working_dir}, cwd={os.getcwd()}")

        # create temp working file
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        tmp_filename = f"pkds_pipeline_{now_str}.yml"
        pipeline_path = os.path.join(working_dir, tmp_filename)
        logger.debug(f"pipeline_path={pipeline_path}")
        with open(pipeline_path, "w") as tempfile:
            tempfile.writelines(pipeline_str)
        # read yaml and show debug info
        logger.debug("yaml")
        with open(pipeline_path, "r") as tempfile:
            the_yaml = yaml.safe_load(tempfile)
        logger.debug(the_yaml)
        logger.debug("-----")
        ss = yaml.dump(the_yaml, default_flow_style=None)
        logger.debug(ss)
        logger.debug("-----")
        # load temp working file into pipeline object
        self.node_loader = DeclarativeLoader(
            Path(pipeline_path), "None", custom_nodes_parent_subdir
        )
        self.pipeline: Pipeline = self.node_loader.get_pipeline()
        logger.debug(f"self.pipeline: {self.pipeline}")
        # clean up by removing temp file
        if os.path.isfile(pipeline_path):
            logger.debug(f"delete {pipeline_path}")
            os.remove(pipeline_path)

    def _update_nodes(self) -> None:
        """Update UI properties of playback screen"""
        self.output_header.height = self.node_height // 2
        self.output_header.parent.height = self.output_header.height
