import time
import threading
import webbrowser


def launch_browser(port):
    time.sleep(1)
    for browser in ['chrome', 'firefox', 'chromium', 'safari']:
        try:
            webbrowser.get(browser).open('http://localhost:%s' % port)
        except:
            pass
        else:
            break


def start_thread(fn):
    thread = threading.Thread(target=fn)
    thread.setDaemon(True)
    thread.start()
    return thread

