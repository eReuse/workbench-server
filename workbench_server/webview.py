import sys

from cefpython3 import cefpython as cef


def main(url: str = 'https://www.devicetag.io/app', title: str = 'DeviceTag.io'):
    """
    Opens a CEF (Chromium embedded framework) webview pointing at a DevicehubClient.
    """
    assert cef.__version__ >= "57.0", "CEF Python v57.0+ required to run this"
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    settings = {
        'ignore_certificate_errors': True
    }
    cef.Initialize(settings=settings)
    cef.CreateBrowserSync(url=url, window_title=title)
    cef.MessageLoop()
    cef.Shutdown()


if __name__ == '__main__':
    main()
