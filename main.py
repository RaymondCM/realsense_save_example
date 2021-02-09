from copy import deepcopy

import pyrealsense2 as rs
import numpy as np
import cv2

import pathlib
from datetime import datetime
import json
import argparse


import threading
import queue


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
                print("@")
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


def main():
    def cls_to_dict(obj):
        return {k: getattr(obj, k, None) for k in dir(obj) if "__" not in k and not k.startswith("_")}
    parser = argparse.ArgumentParser()
    parser.add_argument("--visualise", action='store_true', default=False, help="Show the current frames")
    parser.add_argument("--threads", default=8, help="Number of threads to use for writing to disk")
    args = parser.parse_args()

    visualise = args.visualise
    threads = args.threads
    pipeline = rs.pipeline()

    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 1920, 1080, rs.format.bgr8, 30)

    profile = pipeline.start(config)

    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()
    print("Depth Scale is: " , depth_scale)

    align_to = rs.stream.color
    align = rs.align(align_to)

    folder_name = str(datetime.now())
    for o in ['.', ':', " "]:
        folder_name = folder_name.replace(o, "_") 

    save_path = pathlib.Path(__file__).parent / folder_name
    if not save_path.exists():
        save_path.mkdir(parents=True)
    current_image = 0
    print("Saving images to {}".format(save_path.resolve()))

    workers = QueueJobs(maxsize=30, threads=threads)

    try:
        while True:
            frames = pipeline.wait_for_frames()
            o_depth_frame = frames.get_depth_frame()

            aligned_frames = align.process(frames)

            aligned_depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            if not aligned_depth_frame or not color_frame or not o_depth_frame:
                continue
            
            # Render
            o_depth_image = np.asanyarray(o_depth_frame.get_data())
            depth_image = np.asanyarray(aligned_depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            time = str(datetime.time(datetime.now())).replace(".", "_").replace(":", "_")
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            image_info = {
                "depth_intrinsics": cls_to_dict(o_depth_frame.profile.as_video_stream_profile().intrinsics),
                "aligned_depth_intrinsics": cls_to_dict(aligned_depth_frame.profile.as_video_stream_profile().intrinsics),
                "colour_intrinsics": cls_to_dict(color_frame.profile.as_video_stream_profile().intrinsics),
                "depth_to_color_extrinsics": cls_to_dict(o_depth_frame.profile.get_extrinsics_to(color_frame.profile)),
                "aligned_depth_to_color_extrinsics": cls_to_dict(aligned_depth_frame.profile.get_extrinsics_to(color_frame.profile)),
            }
            tasks = [
                (save_dict, (save_path / "{:07d}_info.json".format(current_image), image_info)),
                (save_img, (save_path / "{:07d}_{}_color.png".format(current_image, time), color_image)),
                (save_img, (save_path / "{:07d}_{}_depth.png".format(current_image, time), o_depth_image)),
                (save_img, (save_path / "{:07d}_{}_aligned_depth.png".format(current_image, time), depth_image)),
                (save_img, (save_path / "{:07d}_{}_aligned_depth_vis.png".format(current_image, time), depth_colormap)),
            ]
            for func, args in tasks:
                workers.add_task(func, deepcopy(args), {})
            print("Added frames to save_queue (queue_size={}) from iter {:07d}".format(workers.qsize(), current_image))
            current_image += 1

            # Visualisation code
            if visualise:
                depth_image_3d = np.dstack((depth_image, depth_image, depth_image))
                depth_image_3d = (((depth_image_3d - depth_image_3d.min()) / (depth_image_3d.ptp())) * 255.0).astype(np.uint8)

                images = (color_image, depth_image_3d, depth_colormap)
                cv2.namedWindow('RGB (Left) Aligned Depth to RGB (Middle) Depth Colour Visualisation (Right)', cv2.WINDOW_GUI_EXPANDED)
                cv2.imshow('RGB (Left) Aligned Depth to RGB (Middle) Depth Colour Visualisation (Right)', np.hstack(images))

                key = cv2.waitKey(1)
                # Press esc or 'q' to close the image window
                if key & 0xFF == ord('q') or key == 27:
                    cv2.destroyAllWindows()
                    break
    finally:
        pipeline.stop()
        workers.join()


if __name__ == '__main__':
    main()
