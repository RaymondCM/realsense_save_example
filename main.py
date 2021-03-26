import time
from copy import deepcopy
from io import StringIO

import pyrealsense2 as rs
import numpy as np
import cv2

import pathlib
from datetime import datetime
import json
import argparse

import threading
import queue

from tqdm import tqdm

folder_name = str(datetime.now())
for o in ['.', ':', " "]:
    folder_name = folder_name.replace(o, "_")
save_path = pathlib.Path(__file__).parent / "saved_data" / folder_name
log_file = save_path / "log.txt"
save_log = False


def log(*args, **kwargs):
    if save_log:
        with log_file.open('a' if log_file.exists() else 'w') as fh:
            print(*args, **kwargs, file=fh)
    print(*args, **kwargs)


class QueueWorker(threading.Thread):
    """Runs jobs from QueueJobs"""

    def __init__(self, q, *args, **kwargs):
        self.q = q
        super().__init__(*args, **kwargs)

    def run(self):
        while True:
            try:
                work = self.q.get()
            except queue.Empty:
                log("@")
                return
            work[0](*work[1], **work[2])
            self.q.task_done()


class QueueJobs(queue.Queue):
    """Add jobs in the form of (func, args, kwargs) to a task queue"""

    def __init__(self, maxsize=0, threads=1):
        super().__init__(maxsize)
        for _ in range(threads):
            QueueWorker(self).start()

    def add_task(self, func, args, kwargs, wait=False):
        self.put((func, args, kwargs)) if wait else self.put_nowait((func, args, kwargs))


def save_img(p, i):
    cv2.imwrite(str(p), i)


def save_dict(p, d):
    with open(str(p), 'w') as f:
        json.dump(d, f, default=lambda obj: str(obj), indent=4)


class RealsenseD400Camera:
    def __init__(self, config_json=None):
        self.device = None
        self.advanced_mode = None
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.load_config(config_json)
        self.profile = self.pipeline.start(self.config)
        self.colorizer = rs.colorizer()

        self.depth_sensor = self.profile.get_device().first_depth_sensor()
        self.depth_scale = self.depth_sensor.get_depth_scale()
        log("Depth Scale is: ", self.depth_scale)

        self.align_to = rs.stream.color
        self.align = rs.align(self.align_to)

    def load_config(self, config_json=None):
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

        width, height, fps = 1280, 720, 30
        if config_json:
            with open(config_json, "r") as fh:
                as_json_object = json.load(fh)
            json_string = str(as_json_object).replace("'", '\"')
            self.advanced_mode.load_json(json_string)
            width, height = int(as_json_object["stream-width"]), int(as_json_object["stream-height"])
            fps = int(as_json_object["stream-fps"])

        self.config.enable_device(self.device.get_info(rs.camera_info.serial_number))
        log("Enabling colour: {}x{}@{} - {}".format(1920, 1080, 30, str(rs.format.bgr8)))
        self.config.enable_stream(rs.stream.color, 1920, 1080, rs.format.bgr8, 30)
        log("Enabling depth: {}x{}@{} - {}".format(width, height, fps, str(rs.format.z16)))
        self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        log("Enabling infrared: {}x{}@{} - {}".format(width, height, fps, str(rs.format.y8)))
        self.config.enable_stream(rs.stream.infrared, 1, width, height, rs.format.y8, fps)
        self.config.enable_stream(rs.stream.infrared, 2, width, height, rs.format.y8, fps)

    def wait_for_frames(self):
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
            ir_left_image = np.asanyarray(ir_left.get_data())
            ir_right_image = np.asanyarray(ir_right.get_data())
            depth_image = np.asanyarray(depth.get_data())
            aligned_depth_image = np.asanyarray(aligned_depth.get_data())
            aligned_depth_cm_image = np.asanyarray(self.colorizer.colorize(aligned_depth).get_data())
            color_image = np.asanyarray(colour.get_data())

            def rs2dict(obj):
                return {k: getattr(obj, k, None) for k in dir(obj) if "__" not in k and not k.startswith("_")}

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

            return color_image, depth_image, aligned_depth_image, aligned_depth_cm_image, ir_left_image, \
                   ir_right_image, image_info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--visualise", action='store_true', default=False, help="Show the current frames")
    parser.add_argument("--save", action='store_true', default=False, help="Save the current frames")
    parser.add_argument("--interval", default=0, help="Interval between saved frames (0 to 59) "
                                                      "i.e 30 will save at 0 and 30 minutes past, 0 saves all")
    parser.add_argument("--config", default=None, help="Config json file saved from realsense-viewer")
    parser.add_argument("--threads", default=8, help="Number of threads to use for writing to disk")
    args = parser.parse_args()

    if args.config is None:
        args.config = pathlib.Path(__file__).parent / "configs/default.json"
    if args.save:
        global save_log
        save_log = True

    if args.save:
        if not save_path.exists():
            save_path.mkdir(parents=True)
        current_image = 0
        log("Saving images to {}".format(save_path.resolve()))
        workers = QueueJobs(maxsize=30, threads=args.threads)
    if args.visualise:
        cv2.namedWindow('Realsense', cv2.WINDOW_NORMAL)

    camera = RealsenseD400Camera(config_json=args.config)

    try:
        shutdown = False
        while not shutdown:
            colour, depth, a_depth, a_depth_cm, ir_l, ir_r, info = camera.wait_for_frames()

            if args.save:
                time_str = str(datetime.time(datetime.now())).replace(".", "_").replace(":", "_")
                tasks = [
                    (save_dict, (save_path / "{:07d}_{}_info.json".format(current_image, time_str), info)),
                    (save_img, (save_path / "{:07d}_{}_colour.png".format(current_image, time_str), colour)),
                    (save_img, (save_path / "{:07d}_{}_depth.png".format(current_image, time_str), depth)),
                    (save_img, (save_path / "{:07d}_{}_aligned_depth.png".format(current_image, time_str), a_depth)),
                    (save_img, (save_path / "{:07d}_{}_aligned_depth_cm.png".format(current_image, time_str), a_depth_cm)),
                    (save_img, (save_path / "{:07d}_{}_infrared_left.png".format(current_image, time_str), ir_l)),
                    (save_img, (save_path / "{:07d}_{}_infrared_right.png".format(current_image, time_str), ir_r)),
                ]
                for func, arguments in tasks:
                    workers.add_task(func, deepcopy(arguments), {})
                log("Saving frames (queue_size={}) from iter {:07d}".format(workers.qsize(), current_image))
                current_image += 1

            # Visualisation code
            if args.visualise:
                def to3d(im):
                    return np.dstack((im, im, im))
                images = np.vstack((
                    np.hstack(tuple(cv2.resize(x, (720, 480)) for x in (colour, a_depth_cm))),
                    np.hstack(tuple(cv2.resize(x, (720, 480)) for x in (to3d(ir_l),  to3d(ir_r)))),
                ))
                cv2.imshow('Realsense', images)
                key = cv2.waitKey(1)
                # Press esc or 'q' to close the image window
                if key & 0xFF == ord('q') or key == 27:
                    cv2.destroyAllWindows()
                    shutdown = True
    finally:
        camera.pipeline.stop()
        if args.save:
            workers.join()


if __name__ == '__main__':
    main()
