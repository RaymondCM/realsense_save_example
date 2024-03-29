import argparse
import os
import pathlib
import shutil
import time

from rs_store.utils import get_str_datetime, get_new_save_path

try:
    import thread
except ImportError:
    import _thread as thread

from timeit import default_timer as timer

from raytils.system import LoadBalancer

from rs_store.camera import RealsenseD400Camera
from rs_store.save import save


save_path = get_new_save_path()
log_file = save_path / "log.txt"
save_log = False


def log(*args, **kwargs):
    if save_log:
        with log_file.open('a' if log_file.exists() else 'w') as fh:
            print(*args, **kwargs, file=fh)
    print(*args, **kwargs)


def health_check(url, job_meta=None):
    try:
        attempt = 0
        while attempt <= 3:
            import socket
            import urllib.request
            try:
                urllib.request.urlopen(url, timeout=10)
                return True
            except socket.error as e:
                print(f"Ping attempt {attempt} failed: {e}")
            attempt += 1
    except Exception as e:
        print(f"Failed to send health check: {e}")
    return False


def get_interfaces():
    try:
        import netifaces

        extra_info = {}

        try:
            import socket
            extra_info["HOST"] = socket.gethostname()
        except Exception as e:
            print("Could not get hostname")

        for interface in netifaces.interfaces():
            try:
                for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                    extra_info[f"IP {interface}"] = link['addr']
            except Exception as e:
                print(f"Could not get interface {interface}")
        return extra_info
    except Exception as e:
        print("Could not get network interfaces")
        return {}


def msteams_notification(url, title, extra_info=None, job_meta=None):
    try:
        import pymsteams
        extra_info = extra_info or {}
        extra_info.update(get_interfaces())
        teams_message = pymsteams.connectorcard(url)
        teams_message.title(title)
        teams_message.text(" " + ',   \n'.join([f"{k}: {v}" for k, v in extra_info.items()]))
        teams_message.send()
    except Exception as e:
        print(f"Failed to send notification: {e}")


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--visualise", action='store_true', default=False, help="Show the current frames")
    parser.add_argument("--save", action='store_true', default=False, help="Save the current frames")
    parser.add_argument("--interval", default='Inf', help="Number of seconds to wait between captures")
    parser.add_argument("--config", default=None, help="Config json file saved from realsense-viewer")
    parser.add_argument("--threads", default=1, help="Number of threads to use for writing to disk")
    parser.add_argument("--out", default=None, help="Directory to save files in")
    parser.add_argument("--webhook", default=None, help="URL of MS Teams WebHook")
    parser.add_argument("--health", default=None, help="URL of HealthCheck.io")
    args = parser.parse_args()

    # TODO: ADD FILTERS
    if args.out is not None:
        global save_path
        global log_file
        save_path = pathlib.Path(str(args.out))
        log_file = save_path / "log.txt"
    if args.config is None:
        args.config = pathlib.Path(__file__).parent / "configs/default.yaml"
    if args.save:
        global save_log
        save_log = True
        if not save_path.exists():
            save_path.mkdir(parents=True)
        idx = 0
        n_threads = int(args.threads) or 1
        assert n_threads > 0
        load_balancer = LoadBalancer(maxsize=80, threads=n_threads, auto=n_threads > 1)
    args.interval = float(args.interval)
    camera = None

    save_on_space_key = args.save and args.visualise
    if save_on_space_key:
        log("Press space in the display window to save to disk.")

    try:
        camera = RealsenseD400Camera(config_path=args.config, visualise=args.visualise)
        last_capture = timer()

        shutdown = False
        if args.webhook and args.save:
            load_balancer.add_task(msteams_notification, (args.webhook, "Connected"))

        if args.save:
            save_path = save_path / f"{camera.serial_number}"
            if not save_path.exists():
                save_path.mkdir(parents=True)
            log("Saving images to {}".format(save_path.resolve()))

        while not shutdown:
            time_since_last_capture = timer() - last_capture
            start_capture = timer()

            frames, key_code = camera.get_frames(return_key=True)

            if args.save and time_since_last_capture > args.interval or (save_on_space_key and key_code == 32):
                last_capture = timer()
                time_str = get_str_datetime()
                if not save_path.exists():
                    save_path.mkdir(parents=True)
                for k in ["colour", "depth", "aligned_depth", "aligned_depth_cm", "ir_left", "ir_right", "meta"]:
                    data = getattr(frames, k)
                    if data is None:
                        continue
                    load_balancer.add_task(save, (save_path / f"{idx:07d}_{time_str}_{k}", data), {})

                log(f"Saving queue_size={load_balancer.qsize()}, iter={idx:07d} "
                    f"tps={load_balancer.tasks_per_second.get_fps()}")
                if args.health:
                    load_balancer.add_task(health_check, (args.health,))
                if args.webhook:
                    extra_info = {"serial": camera.serial_number, "capture_number": idx, "time": time_str}
                    try:
                        total, used, free = shutil.disk_usage("/")
                        extra_info.update({
                            "total_space": sizeof_fmt(total),
                            "used_space": sizeof_fmt(used),
                            "free_space": sizeof_fmt(free),
                        })
                    except Exception as e:
                        print("Could not get '/' disk space:", e)

                    load_balancer.add_task(msteams_notification, (args.webhook, "Data Collected", extra_info))
                idx += 1

            if args.interval > 0 and args.interval != float("inf"):
                time_to_sleep = args.interval - (timer() - start_capture)
                if time_to_sleep > 0:
                    print("Sleeping for {} seconds".format(time_to_sleep))
                    time.sleep(time_to_sleep)

    except Exception as e:
        if args.webhook and args.save:
            load_balancer.add_task(msteams_notification, (args.webhook, "Error"))
        print("Exception:", e)
    finally:
        try:
            if camera is not None:
                camera.stop()
            if args.save:
                load_balancer.join()
        except Exception as e:
            print("Could not cleanly exit")
            os._exit(1)


if __name__ == '__main__':
    main()
