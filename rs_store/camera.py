import pathlib
import threading
from collections import Callable

import cv2
from raytils.display import OpenCVDisplay

from rs_store.config import Config
from rs_store.save import log
import pyrealsense2 as rs
import numpy as np
import time
from tqdm import tqdm


def rs2dict(obj):
    return {k: getattr(obj, k, None) for k in dir(obj) if "__" not in k and not k.startswith("_")}


def to3d(im):
    return np.dstack((im, im, im))


class RealsenseData:
    def __init__(self, colour=None, depth=None, aligned_depth=None, aligned_depth_cm=None, ir_left=None, ir_right=None,
                 meta=None):
        self.colour = colour
        self.depth = depth
        self.aligned_depth = aligned_depth
        self.aligned_depth_cm = aligned_depth_cm
        self.ir_left = ir_left
        self.ir_right = ir_right
        self.meta = meta

    def __bool__(self):
        return any([
            self.colour is not None,
            self.depth is not None,
            self.aligned_depth is not None,
            self.aligned_depth_cm is not None,
            self.ir_left is not None,
            self.ir_right is not None,
            self.meta is not None,
        ])


class RealsenseD400Camera():
    def __init__(self, config_path=None, visualise=False):
        self.device = None
        self.advanced_mode = None
        self.pipeline = rs.pipeline()
        self.rs_config = rs.config()
        if config_path is None:
            config_path = pathlib.Path(__file__).parent.parent / "configs/default.yaml"
        self.config = Config(config_path)
        self._configure_rs()
        self.profile = self.pipeline.start(self.rs_config)
        self.colorizer = rs.colorizer()
        self.frames = RealsenseData()

        self.depth_sensor = self.profile.get_device().first_depth_sensor()
        self.depth_scale = self.depth_sensor.get_depth_scale()
        log("Depth Scale is: ", self.depth_scale)

        self.align_to = rs.stream.color
        self.align = rs.align(self.align_to)

        self.visualise = visualise
        self.display = None
        if self.visualise:
            self.display = OpenCVDisplay("Realsense Saver")

    def _configure_rs(self):
        ds5_product_ids = ["0AD1", "0AD2", "0AD3", "0AD4", "0AD5", "0AF6", "0AFE", "0AFF", "0B00", "0B01", "0B03",
                           "0B07", "0B3A", "0B5C"]

        def find_device_that_supports_advanced_mode():
            ctx = rs.context()
            devices = ctx.query_devices()
            try:
                for t_device in devices:
                    if t_device.supports(rs.camera_info.product_id) and str(
                            t_device.get_info(rs.camera_info.product_id)) in ds5_product_ids:
                        if t_device.supports(rs.camera_info.name):
                            log("Found device that supports advanced mode: {} ({})".format(
                                t_device.get_info(rs.camera_info.name),
                                t_device.get_info(rs.camera_info.serial_number),
                            ))
                        return t_device
            except Exception as e:
                log("Error finding camera:", e)
            raise Exception("No D400 product line device that supports advanced mode was found")

        self.device = find_device_that_supports_advanced_mode()
        self.advanced_mode = rs.rs400_advanced_mode(self.device)
        log("Advanced mode is", "enabled" if self.advanced_mode.is_enabled() else "disabled")

        # Loop until we successfully enable advanced mode
        while not self.advanced_mode.is_enabled():
            log("Trying to enable advanced mode")
            self.advanced_mode.toggle_advanced_mode(True)
            # At this point the device will disconnect and re-connect.
            for _ in tqdm(range(5), desc="Sleeping while camera reconnects"):
                time.sleep(1)
            # The 'dev' object will become invalid and we need to initialize it again
            self.device = find_device_that_supports_advanced_mode()
            self.advanced_mode = rs.rs400_advanced_mode(self.device)
            log("Advanced mode is", "enabled" if self.advanced_mode.is_enabled() else "disabled")

        self.advanced_mode.load_json(self.config.rs_str)
        width, height = int(self.config["stream-width"]), int(self.config["stream-height"])
        fps = int(self.config["stream-fps"])
        color_width, colour_height, colour_fps = self.config.rgb_width, self.config.rgb_height, self.config.rgb_fps

        self.rs_config.enable_device(self.device.get_info(rs.camera_info.serial_number))
        log("Enabling colour: {}x{}@{} - {}".format(color_width, colour_height, colour_fps, str(rs.format.bgr8)))
        self.rs_config.enable_stream(rs.stream.color, color_width, colour_height, rs.format.bgr8, colour_fps)
        log("Enabling depth: {}x{}@{} - {}".format(width, height, fps, str(rs.format.z16)))
        self.rs_config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)

        if self.config.ir_enabled:
            log("Enabling infrared: {}x{}@{} - {}".format(width, height, fps, str(rs.format.y8)))
            self.rs_config.enable_stream(rs.stream.infrared, 1, width, height, rs.format.y8, fps)
            self.rs_config.enable_stream(rs.stream.infrared, 2, width, height, rs.format.y8, fps)

    def warmup(self, n=100):
        for _ in range(n):
            self.get_frames()

    def get_frames(self):
        while True:
            frames = self.pipeline.wait_for_frames()
            aligned_frames = self.align.process(frames)

            ir_left = frames.get_infrared_frame(1)
            ir_right = frames.get_infrared_frame(2)
            depth = frames.get_depth_frame()
            aligned_depth = aligned_frames.get_depth_frame()
            colour = aligned_frames.get_color_frame()

            if any([not x for x in [ir_left, ir_right, depth, aligned_depth, colour]]):
                log("Invalid frames skipping this frame set")
                continue

            # Render
            ir_left_image = None
            ir_right_image = None
            if self.config.ir_enabled:
                ir_left_image = np.asanyarray(ir_left.get_data())
                ir_right_image = np.asanyarray(ir_right.get_data())
            depth_image = np.asanyarray(depth.get_data())
            aligned_depth_image = np.asanyarray(aligned_depth.get_data())
            aligned_depth_cm_image = np.asanyarray(self.colorizer.colorize(aligned_depth).get_data())
            color_image = np.asanyarray(colour.get_data())

            image_info = {
                "ir_left_intrinsics": rs2dict(ir_left.profile.as_video_stream_profile().intrinsics),
                "ir_right_intrinsics": rs2dict(ir_right.profile.as_video_stream_profile().intrinsics),
                "depth_intrinsics": rs2dict(depth.profile.as_video_stream_profile().intrinsics),
                "aligned_depth_intrinsics": rs2dict(aligned_depth.profile.as_video_stream_profile().intrinsics),
                "colour_intrinsics": rs2dict(colour.profile.as_video_stream_profile().intrinsics),
                "ir_left_to_colour_extrinsics": rs2dict(ir_left.profile.get_extrinsics_to(colour.profile)),
                "ir_right_to_colour_extrinsics": rs2dict(ir_right.profile.get_extrinsics_to(colour.profile)),
                "depth_to_colour_extrinsics": rs2dict(depth.profile.get_extrinsics_to(colour.profile)),
                "aligned_depth_to_colour_extrinsics": rs2dict(aligned_depth.profile.get_extrinsics_to(colour.profile)),
            }

            if self.visualise:
                canvas = np.hstack(
                    [cv2.resize(color_image, (720, 480)), cv2.resize(aligned_depth_cm_image, (720, 480))]
                )

                if self.config.ir_enabled:
                    canvas = np.vstack([
                        canvas,
                        to3d(np.hstack([cv2.resize(ir_left_image, (720, 480)), cv2.resize(ir_right_image, (720, 480))]))
                    ])

                self.display.show(canvas)

            self.frames = RealsenseData(color_image, depth_image, aligned_depth_image, aligned_depth_cm_image,
                                        ir_left_image, ir_right_image, image_info)
            return self.frames