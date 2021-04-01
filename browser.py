import pathlib

import cv2
from raytils.ui.selection import get_selection_from_list


def main():
    folders = [x for x in (pathlib.Path(__file__).parent / "saved_data").glob('*') if x.is_dir()]
    selection = get_selection_from_list(folders)
    images = list(x for x in selection.glob("*") if x.is_file())

    criteria = lambda x: str(x).endswith("colour.png")
    filtered_images = list(filter(criteria, images))
    filtered_images = sorted(filtered_images, key=lambda x: x.name)

    interval = 15
    minutes_per_second = 60
    rate = int(((1 / minutes_per_second) / (60 / interval)) * 1000)
    cv2.namedWindow('Realsense Capture Browser', cv2.WINDOW_FREERATIO)

    for im_path in filtered_images:
        im = cv2.imread(str(im_path))
        cv2.imshow('Realsense Capture Browser', im)
        if cv2.waitKey(rate) == ord('q'):
            break


if __name__ == '__main__':
    main()
