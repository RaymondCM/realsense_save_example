import pathlib
from datetime import datetime


def get_saved_data_root():
    return pathlib.Path(__file__).parent.parent / "saved_data"


def get_str_datetime():
    folder_name = str(datetime.now())
    for o in ['.', ':', " "]:
        folder_name = folder_name.replace(o, "_")
    return "D" + str(datetime.now()).replace(".", "_").replace(":", "_").replace(" ", "T")


def get_new_save_path():
    return get_saved_data_root() / get_str_datetime()
