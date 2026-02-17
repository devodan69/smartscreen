"""Desktop app runtime, view-model, and QML integration."""

from __future__ import annotations

import json
import sys
from dataclasses import replace

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from smartscreen_core import AppConfig, StreamController, load_config, save_config, set_launch_at_login
from smartscreen_renderer import DashboardRenderer, get_theme, list_themes
from smartscreen_renderer.dashboard import DashboardData
from smartscreen_telemetry import TelemetryProvider


class SmartScreenViewModel(QObject):
    cpuTextChanged = Signal()
    gpuTextChanged = Signal()
    ramTextChanged = Signal()
    netTextChanged = Signal()
    diskTextChanged = Signal()
    clockTextChanged = Signal()
    deviceStatusChanged = Signal()
    previewUrlChanged = Signal()
    streamingChanged = Signal()
    fpsChanged = Signal()
    throughputChanged = Signal()
    themesJsonChanged = Signal()
    dashboardThemeChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.config: AppConfig = load_config()
        self.telemetry = TelemetryProvider()
        self.renderer = DashboardRenderer(width=800, height=480)
        self.stream = StreamController(
            width=800,
            height=480,
            mode=self.config.stream.mode,
            poll_ms=self.config.stream.poll_ms,
            port_override=self.config.device.port_override,
        )

        self._cpu_text = "CPU --"
        self._gpu_text = "GPU --"
        self._ram_text = "RAM --"
        self._net_text = "NET --"
        self._disk_text = "DISK --"
        self._clock_text = "--"
        self._device_status = "Disconnected"
        self._preview_url = ""
        self._streaming = False
        self._fps = 0.0
        self._throughput = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(max(200, min(2000, self.config.stream.poll_ms)))

    @Property(str, notify=cpuTextChanged)
    def cpuText(self) -> str:
        return self._cpu_text

    @Property(str, notify=gpuTextChanged)
    def gpuText(self) -> str:
        return self._gpu_text

    @Property(str, notify=ramTextChanged)
    def ramText(self) -> str:
        return self._ram_text

    @Property(str, notify=netTextChanged)
    def netText(self) -> str:
        return self._net_text

    @Property(str, notify=diskTextChanged)
    def diskText(self) -> str:
        return self._disk_text

    @Property(str, notify=clockTextChanged)
    def clockText(self) -> str:
        return self._clock_text

    @Property(str, notify=deviceStatusChanged)
    def deviceStatus(self) -> str:
        return self._device_status

    @Property(str, notify=previewUrlChanged)
    def previewUrl(self) -> str:
        return self._preview_url

    @Property(bool, notify=streamingChanged)
    def streaming(self) -> bool:
        return self._streaming

    @Property(float, notify=fpsChanged)
    def fps(self) -> float:
        return self._fps

    @Property(float, notify=throughputChanged)
    def throughput(self) -> float:
        return self._throughput

    @Property(str, notify=themesJsonChanged)
    def themesJson(self) -> str:
        return json.dumps(list_themes())

    @Property(str, notify=dashboardThemeChanged)
    def dashboardTheme(self) -> str:
        return self.config.ui.dashboard_theme

    def _set_text(self, field: str, value: str, signal: Signal) -> None:
        if getattr(self, field) != value:
            setattr(self, field, value)
            signal.emit()

    def _snapshot_to_dashboard(self, snap):
        return DashboardData(
            cpu_percent=snap.cpu.percent,
            cpu_temp_c=snap.cpu.temp_c,
            gpu_percent=snap.gpu.percent,
            gpu_temp_c=snap.gpu.temp_c,
            ram_used_gb=snap.memory.used_gb,
            ram_total_gb=snap.memory.total_gb,
            disk_used_gb=snap.disk.used_gb,
            disk_total_gb=snap.disk.total_gb,
            net_up_mbps=snap.network.up_mb_s,
            net_down_mbps=snap.network.down_mb_s,
            timestamp=snap.clock.local_time,
        )

    def _tick(self) -> None:
        snap = self.telemetry.poll()
        dash = self._snapshot_to_dashboard(snap)

        self._set_text("_cpu_text", f"CPU {snap.cpu.percent:05.1f}%  {self._fmt_temp(snap.cpu.temp_c)}", self.cpuTextChanged)
        self._set_text("_gpu_text", f"GPU {self._fmt_percent(snap.gpu.percent)}  {self._fmt_temp(snap.gpu.temp_c)}", self.gpuTextChanged)
        self._set_text("_ram_text", f"RAM {snap.memory.used_gb:04.1f}/{snap.memory.total_gb:04.1f} GB", self.ramTextChanged)
        self._set_text("_net_text", f"NET ↑{snap.network.up_mb_s:05.2f} ↓{snap.network.down_mb_s:05.2f} MB/s", self.netTextChanged)
        self._set_text("_disk_text", f"DISK {snap.disk.used_gb:05.1f}/{snap.disk.total_gb:05.1f} GB", self.diskTextChanged)
        self._set_text("_clock_text", snap.clock.local_time.strftime("%Y-%m-%d %H:%M:%S"), self.clockTextChanged)

        preview = self.renderer.preview_data_url(dash, self.config.ui.dashboard_theme)
        if preview != self._preview_url:
            self._preview_url = preview
            self.previewUrlChanged.emit()

        if self._streaming:
            try:
                frame = self.renderer.render(dash, self.config.ui.dashboard_theme)
                self.stream.send(frame.bytes)
                status = self.stream.status
                self._update_stream_status(
                    text=f"Connected {status.port or ''}".strip(),
                    fps=status.fps,
                    throughput=status.throughput_bps,
                )
            except Exception as exc:
                self._update_stream_status(text=f"Error: {exc}", fps=0.0, throughput=0.0)

    def _update_stream_status(self, text: str, fps: float, throughput: float) -> None:
        if text != self._device_status:
            self._device_status = text
            self.deviceStatusChanged.emit()
        if abs(fps - self._fps) > 0.001:
            self._fps = fps
            self.fpsChanged.emit()
        if abs(throughput - self._throughput) > 1.0:
            self._throughput = throughput
            self.throughputChanged.emit()

    @Slot()
    def startStreaming(self) -> None:
        if self._streaming:
            return
        try:
            self.stream.connect()
            self._streaming = True
            self.streamingChanged.emit()
            self._update_stream_status("Connected", self.stream.status.fps, self.stream.status.throughput_bps)
        except Exception as exc:
            self._update_stream_status(f"Connect failed: {exc}", 0.0, 0.0)

    @Slot()
    def stopStreaming(self) -> None:
        if not self._streaming:
            return
        self._streaming = False
        self.streamingChanged.emit()
        self.stream.disconnect()
        self._update_stream_status("Disconnected", 0.0, 0.0)

    @Slot()
    def reconnect(self) -> None:
        self.stopStreaming()
        self.startStreaming()

    @Slot(str)
    def setDashboardTheme(self, name: str) -> None:
        if name not in list_themes():
            return
        self.config.ui.dashboard_theme = name
        save_config(self.config)
        self.dashboardThemeChanged.emit()

    @Slot(int)
    def setBrightness(self, level: int) -> None:
        self.config.display.brightness = max(0, min(100, level))
        save_config(self.config)
        try:
            self.stream.set_brightness(self.config.display.brightness)
        except Exception:
            pass

    @Slot(int)
    def setPollMs(self, poll_ms: int) -> None:
        v = max(200, min(2000, poll_ms))
        self.config.stream.poll_ms = v
        self.stream.poll_ms = v
        self._timer.setInterval(v)
        save_config(self.config)

    @Slot(str)
    def setPortOverride(self, port: str) -> None:
        value = port.strip() or None
        self.config.device.port_override = value
        self.stream.port_override = value
        save_config(self.config)

    @Slot(bool)
    def setLaunchAtLogin(self, enabled: bool) -> None:
        self.config.startup.launch_at_login = bool(enabled)
        save_config(self.config)
        try:
            set_launch_at_login(enabled=bool(enabled))
        except Exception:
            pass

    @Slot()
    def save(self) -> None:
        save_config(self.config)

    def shutdown(self) -> None:
        self._timer.stop()
        if self._streaming:
            self.stopStreaming()

    @staticmethod
    def _fmt_temp(value: float | None) -> str:
        return "N/A" if value is None else f"{value:04.1f}°C"

    @staticmethod
    def _fmt_percent(value: float | None) -> str:
        return "N/A" if value is None else f"{value:05.1f}%"


def run_gui() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SmartScreen")
    app.setOrganizationName("DGE Projects")

    vm = SmartScreenViewModel()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("vm", vm)
    qml_path = __file__.replace("app.py", "qml/Main.qml")
    engine.load(qml_path)

    if not engine.rootObjects():
        return 1

    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        icon = QIcon.fromTheme("video-display")
        tray = QSystemTrayIcon(icon, app)
        tray.setToolTip("SmartScreen")
        menu = QMenu()

        start_action = QAction("Start Streaming", menu)
        start_action.triggered.connect(vm.startStreaming)
        menu.addAction(start_action)

        stop_action = QAction("Stop Streaming", menu)
        stop_action.triggered.connect(vm.stopStreaming)
        menu.addAction(stop_action)

        reconnect_action = QAction("Reconnect", menu)
        reconnect_action.triggered.connect(vm.reconnect)
        menu.addAction(reconnect_action)

        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.show()

    exit_code = app.exec()
    vm.shutdown()
    return int(exit_code)
