import cv2
import time

class RTSPCameraSource:
    """
    RTSP network / IP camera stream.
    Includes FFmpeg backend configuration and auto-reconnect logic.
    """

    def __init__(
        self,
        url: str,
        buffer_size: int = 1,
        reconnect: bool = True,
        reconnect_delay: float = 2.0,
    ):
        self.url = url
        self.buffer_size = buffer_size
        self.reconnect = reconnect
        self.reconnect_delay = reconnect_delay
        self.cap = None
        self._consecutive_failures = 0
        self._max_failures = 30  # before attempting reconnect

    def open(self):
        self._connect()

    def _connect(self):
        if self.cap:
            self.cap.release()

        # Use FFmpeg backend for better RTSP support, but default for HTTP MJPEG
        if self.url.startswith("rtsp://"):
            self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        else:
            self.cap = cv2.VideoCapture(self.url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open RTSP stream: {self.url}\n"
                "  • Verify the RTSP URL, credentials, and camera IP.\n"
                "  • Ensure OpenCV is built with FFmpeg support."
            )
        print(f"[INFO] RTSP stream opened: {self.url}")
        self._consecutive_failures = 0

    def read(self):
        if not self.cap:
            return False, None
            
        ret, frame = self.cap.read()
        if not ret:
            self._consecutive_failures += 1
            if self.reconnect and self._consecutive_failures >= self._max_failures:
                print(f"[WARN] RTSP stream lost. Reconnecting in {self.reconnect_delay}s …")
                time.sleep(self.reconnect_delay)
                try:
                    self._connect()
                except RuntimeError as e:
                    print(f"[ERROR] Reconnect failed: {e}")
            return False, None
            
        self._consecutive_failures = 0
        return True, frame

    def release(self):
        if self.cap:
            self.cap.release()

    def isOpened(self):
        return self.cap is not None and self.cap.isOpened()
