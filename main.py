import pyrealsense2 as rs
import numpy as np
import cv2

import pathlib
from datetime import datetime
import json


def cls_to_dict(obj):
    return {k: getattr(obj, k, None) for k in dir(obj) if "__" not in k and not k.startswith("_")}


def main():
    visualise = False
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

            with open(str(save_path / "{:07d}_info.json".format(current_image)), 'w') as f:
                json.dump({
                    "depth_intrinsics": cls_to_dict(o_depth_frame.profile.as_video_stream_profile().intrinsics),
                    "aligned_depth_intrinsics": cls_to_dict(aligned_depth_frame.profile.as_video_stream_profile().intrinsics),
                    "colour_intrinsics": cls_to_dict(color_frame.profile.as_video_stream_profile().intrinsics),
                    "depth_to_color_extrinsics": cls_to_dict(o_depth_frame.profile.get_extrinsics_to(color_frame.profile)),
                    "aligned_depth_to_color_extrinsics": cls_to_dict(aligned_depth_frame.profile.get_extrinsics_to(color_frame.profile)),
                }, f, default=lambda obj: str(obj), indent=4)

            time = str(datetime.time(datetime.now())).replace(".", "_").replace(":", "_")
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            cv2.imwrite(str(save_path / "{:07d}_{}_color.png".format(current_image, time)), color_image)
            cv2.imwrite(str(save_path / "{:07d}_{}_depth.png".format(current_image, time)), o_depth_image)
            cv2.imwrite(str(save_path / "{:07d}_{}_aligned_depth.png".format(current_image, time)), depth_image)
            cv2.imwrite(str(save_path / "{:07d}_{}_aligned_depth_vis.png".format(current_image, time)), depth_colormap)
            print("Saved frames from iter {:07d} to '{}'".format(current_image, save_path.resolve()))
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

if __name__ == '__main__':
    main()
