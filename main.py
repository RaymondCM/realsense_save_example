import pyrealsense2 as rs
import numpy as np
import cv2

import pathlib
from datetime import datetime


def main():
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
            
            # Render and save code
            o_depth_image = np.asanyarray(o_depth_frame.get_data())
            depth_image = np.asanyarray(aligned_depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # Visualisation code
            depth_image_3d = np.dstack((depth_image, depth_image, depth_image))
            depth_image_3d = (((depth_image_3d - depth_image_3d.min()) / (depth_image_3d.ptp())) * 255.0).astype(np.uint8)

            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            images = (color_image, depth_image_3d, depth_colormap)
            cv2.namedWindow('RGB (Left) Aligned Depth to RGB (Middle) Depth Colour Visualisation (Right)', cv2.WINDOW_GUI_EXPANDED)
            cv2.imshow('RGB (Left) Aligned Depth to RGB (Middle) Depth Colour Visualisation (Right)', np.hstack(images))

            cv2.imwrite(str(save_path / "{:07d}_color.png".format(current_image)), color_image)
            cv2.imwrite(str(save_path / "{:07d}_depth.png".format(current_image)), o_depth_image)
            cv2.imwrite(str(save_path / "{:07d}_aligned_depth.png".format(current_image)), depth_image)
            cv2.imwrite(str(save_path / "{:07d}_aligned_depth_vis.png".format(current_image)), depth_colormap)
            print("Saved frames from iter {:07d} to '{}'".format(current_image, save_path.resolve()))
            current_image += 1

            key = cv2.waitKey(1)
            # Press esc or 'q' to close the image window
            if key & 0xFF == ord('q') or key == 27:
                cv2.destroyAllWindows()
                break
    finally:
        pipeline.stop()

if __name__ == '__main__':
    main()
