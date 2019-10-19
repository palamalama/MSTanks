#!/usr/bin/python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')


if __name__ == "__main__":
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path='./', recursive=False)
    observer.start()

    try:
        while True:
            print("looping")
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()