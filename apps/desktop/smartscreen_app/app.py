"""Desktop app runtime, view-model, and QML integration."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import webbrowser
from importlib import metadata
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from smartscreen_core import (
    AppConfig,
    DiagnosticsExporter,
    PerformanceController,
    PerformanceTargets,
    StreamController,
    UpdateService,
    build_doctor_payload,
    load_config,
    save_config,
    set_launch_at_login,
    touch_update_check,
)
from smartscreen_core.config import ONBOARDING_VERSION
from smartscreen_core.logging_setup import configure_logging, get_logger, install_crash_hooks
from smartscreen_display import DisplayTransport, ProtocolState, auto_select_device
from smartscreen_renderer import DashboardRenderer, build_test_pattern, image_to_rgb565_le, list_themes
from smartscreen_renderer.dashboard import DashboardData
from smartscreen_telemetry import TelemetryProvider


def _app_version() -> str:
    try:
        return metadata.version("smartscreen")
    except Exception:
        return "0.1.0"


def _permission_hint() -> str:
    if sys.platform.startswith("linux"):
        return "Linux may require your user to be in dialout/uucp group for serial access."
    if sys.platform == "darwin":
        return "If serial access fails, reconnect the USB display and retry from onboarding."
    return "If connection fails, run as the same user that installed the app and retry."


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

    appVersionChanged = Signal()
    pollMsChanged = Signal()
    launchAtLoginChanged = Signal()
    portOverrideChanged = Signal()
    uiThemeChanged = Signal()
    reducedMotionChanged = Signal()

    onboardingRequiredChanged = Signal()
    onboardingDeviceStatusChanged = Signal()
    onboardingPermissionTextChanged = Signal()

    updateStatusChanged = Signal()
    updateVersionChanged = Signal()
    updateUrlChanged = Signal()
    updateNotesChanged = Signal()
    updateChannelChanged = Signal()

    diagnosticsPathChanged = Signal()
    recoveryVisibleChanged = Signal()
    recoveryStateChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.config: AppConfig = load_config()
        self.logger = get_logger()
        self.telemetry = TelemetryProvider()
        self.renderer = DashboardRenderer(width=800, height=480)
        self.stream = StreamController(
            width=800,
            height=480,
            mode=self.config.stream.mode,
            poll_ms=self.config.stream.poll_ms,
            port_override=self.config.device.port_override,
        )
        self.updates = UpdateService()
        self.diagnostics = DiagnosticsExporter()
        self.performance = PerformanceController(
            PerformanceTargets(
                cpu_percent_max=self.config.performance.cpu_percent_max,
                rss_mb_max=self.config.performance.rss_mb_max,
                fps_min=self.config.performance.fps_min,
                fps_max=self.config.performance.fps_max,
            )
        )

        self._app_version = _app_version()
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

        self._onboarding_required = (
            not self.config.onboarding.completed or self.config.onboarding.version != ONBOARDING_VERSION
        )
        self._onboarding_device_status = "Device not scanned"
        self._onboarding_permission_text = _permission_hint()

        self._update_status = "Manual checks only"
        self._update_version = ""
        self._update_url = ""
        self._update_notes = ""

        self._diagnostics_path = ""
        self._recovery_visible = False
        self._recovery_state = ""

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(max(200, min(2000, self.config.stream.poll_ms)))

    @Property(str, notify=appVersionChanged)
    def appVersion(self) -> str:
        return self._app_version

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

    @Property(int, notify=pollMsChanged)
    def pollMs(self) -> int:
        return self.config.stream.poll_ms

    @Property(str, notify=portOverrideChanged)
    def portOverride(self) -> str:
        return self.config.device.port_override or ""

    @Property(bool, notify=launchAtLoginChanged)
    def launchAtLogin(self) -> bool:
        return bool(self.config.startup.launch_at_login)

    @Property(str, notify=uiThemeChanged)
    def uiTheme(self) -> str:
        return self.config.ui.theme

    @Property(bool, notify=reducedMotionChanged)
    def reducedMotion(self) -> bool:
        return bool(self.config.ui.reduced_motion)

    @Property(bool, notify=onboardingRequiredChanged)
    def onboardingRequired(self) -> bool:
        return self._onboarding_required

    @Property(str, notify=onboardingDeviceStatusChanged)
    def onboardingDeviceStatus(self) -> str:
        return self._onboarding_device_status

    @Property(str, notify=onboardingPermissionTextChanged)
    def onboardingPermissionText(self) -> str:
        return self._onboarding_permission_text

    @Property(str, notify=updateStatusChanged)
    def updateStatus(self) -> str:
        return self._update_status

    @Property(str, notify=updateVersionChanged)
    def updateVersion(self) -> str:
        return self._update_version

    @Property(str, notify=updateUrlChanged)
    def updateUrl(self) -> str:
        return self._update_url

    @Property(str, notify=updateNotesChanged)
    def updateNotes(self) -> str:
        return self._update_notes

    @Property(str, notify=updateChannelChanged)
    def updateChannel(self) -> str:
        return self.config.updates.channel

    @Property(str, notify=diagnosticsPathChanged)
    def diagnosticsPath(self) -> str:
        return self._diagnostics_path

    @Property(bool, notify=recoveryVisibleChanged)
    def recoveryVisible(self) -> bool:
        return self._recovery_visible

    @Property(str, notify=recoveryStateChanged)
    def recoveryState(self) -> str:
        return self._recovery_state

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
        self._set_text("_net_text", f"NET Up {snap.network.up_mb_s:05.2f} Down {snap.network.down_mb_s:05.2f} MB/s", self.netTextChanged)
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
                    text=f"{status.state.value} {status.port or ''}".strip(),
                    fps=status.fps,
                    throughput=status.throughput_bps,
                )

                budget = self.performance.sample(status.fps, self.config.stream.poll_ms, self.config.stream.mode)
                self.stream.apply_budget(budget)
                if budget.recommended_poll_ms != self.config.stream.poll_ms:
                    self.config.stream.poll_ms = budget.recommended_poll_ms
                    self._timer.setInterval(self.config.stream.poll_ms)
                    self.pollMsChanged.emit()
                if budget.recommended_mode != self.config.stream.mode:
                    self.config.stream.mode = budget.recommended_mode
            except Exception as exc:
                self._update_stream_status(text=f"Error: {exc}", fps=0.0, throughput=0.0)

    def _update_stream_status(self, text: str, fps: float, throughput: float) -> None:
        status = self.stream.status

        recovery_visible = status.state in (
            ProtocolState.BACKOFF_WAIT,
            ProtocolState.RECOVERING,
            ProtocolState.DEGRADED,
        )
        if recovery_visible != self._recovery_visible:
            self._recovery_visible = recovery_visible
            self.recoveryVisibleChanged.emit()

        recovery_state = status.state.value
        if status.state == ProtocolState.BACKOFF_WAIT:
            recovery_state = f"Retrying in {status.backoff_seconds:0.2f}s (attempt {status.recovery_attempts})"
        elif status.last_error:
            recovery_state = f"{status.state.value}: {status.last_error}"

        if recovery_state != self._recovery_state:
            self._recovery_state = recovery_state
            self.recoveryStateChanged.emit()

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

    @Slot()
    def retryRecoveryNow(self) -> None:
        self.reconnect()

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
        self.pollMsChanged.emit()

    @Slot(str)
    def setPortOverride(self, port: str) -> None:
        value = port.strip() or None
        self.config.device.port_override = value
        self.stream.port_override = value
        save_config(self.config)
        self.portOverrideChanged.emit()

    @Slot(bool)
    def setLaunchAtLogin(self, enabled: bool) -> None:
        self.config.startup.launch_at_login = bool(enabled)
        save_config(self.config)
        self.launchAtLoginChanged.emit()
        try:
            set_launch_at_login(enabled=bool(enabled))
        except Exception:
            pass

    @Slot(str)
    def setUiTheme(self, theme: str) -> None:
        value = theme.strip().lower()
        if value not in ("auto", "dark", "light"):
            return
        if self.config.ui.theme != value:
            self.config.ui.theme = value
            save_config(self.config)
            self.uiThemeChanged.emit()

    @Slot(bool)
    def setReducedMotion(self, enabled: bool) -> None:
        if self.config.ui.reduced_motion != bool(enabled):
            self.config.ui.reduced_motion = bool(enabled)
            save_config(self.config)
            self.reducedMotionChanged.emit()

    @Slot(str)
    def setUpdateChannel(self, channel: str) -> None:
        ch = channel if channel in ("stable", "beta") else "stable"
        if self.config.updates.channel != ch:
            self.config.updates.channel = ch
            save_config(self.config)
            self.updateChannelChanged.emit()

    @Slot(str)
    def checkForUpdates(self, channel: str = "") -> None:
        ch = channel if channel in ("stable", "beta") else self.config.updates.channel
        self._update_status = "Checking releases..."
        self.updateStatusChanged.emit()
        try:
            result = self.updates.check(
                current_version=self._app_version,
                channel=ch,
                etag=self.config.updates.etag,
            )
            self.config.updates.etag = result.etag or self.config.updates.etag
            self.setUpdateChannel(ch)
            touch_update_check(self.config)
            save_config(self.config)

            self._update_version = result.latest_version or ""
            self.updateVersionChanged.emit()
            self._update_url = result.download_url or ""
            self.updateUrlChanged.emit()
            self._update_notes = result.notes or ""
            self.updateNotesChanged.emit()

            if result.not_modified:
                self._update_status = "No change since last check"
            elif result.update_available:
                self._update_status = f"Update available: {result.latest_version}"
            elif result.latest_version:
                self._update_status = f"Up to date ({self._app_version})"
            else:
                self._update_status = "No releases found for selected channel"
            self.updateStatusChanged.emit()
        except Exception as exc:
            self._update_status = f"Update check failed: {exc}"
            self.updateStatusChanged.emit()

    @Slot()
    def openUpdateUrl(self) -> None:
        if self._update_url:
            webbrowser.open(self._update_url)

    @Slot()
    def exportDiagnostics(self) -> None:
        doctor = build_doctor_payload(self.config)
        out_dir = Path(tempfile.gettempdir())
        zip_path = self.diagnostics.bundle(
            cfg=self.config,
            doctor_payload=doctor,
            recent_transport_events=self.stream.recent_events(),
            output_dir=out_dir,
        )
        self._diagnostics_path = str(zip_path)
        self.diagnosticsPathChanged.emit()

    @Slot()
    def openDiagnosticsPath(self) -> None:
        if not self._diagnostics_path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self._diagnostics_path))))

    @Slot()
    def save(self) -> None:
        save_config(self.config)

    @Slot()
    def scanOnboardingDevice(self) -> None:
        selected = auto_select_device(DisplayTransport.discover())
        if selected:
            self.config.device.port_override = selected.device
            self._onboarding_device_status = f"Found {selected.device} ({selected.description})"
            self._set_text("_device_status", f"Ready {selected.device}", self.deviceStatusChanged)
            self.portOverrideChanged.emit()
            self.onboardingDeviceStatusChanged.emit()
            save_config(self.config)
            return

        self._onboarding_device_status = "No compatible VID:PID 1A86:5722 device found"
        self.onboardingDeviceStatusChanged.emit()

    @Slot()
    def runOnboardingTestPattern(self) -> None:
        try:
            image = build_test_pattern("quadrants", width=800, height=480)
            frame = image_to_rgb565_le(image)
            self.stream.connect()
            self.stream.send(frame)
            self.stream.disconnect()
            self._onboarding_device_status = "Test pattern sent successfully"
        except Exception as exc:
            self._onboarding_device_status = f"Test pattern failed: {exc}"
        self.onboardingDeviceStatusChanged.emit()

    @Slot(bool)
    def setOnboardingLaunchAtLogin(self, enabled: bool) -> None:
        self.setLaunchAtLogin(enabled)

    @Slot()
    def completeOnboarding(self) -> None:
        self.config.onboarding.completed = True
        self.config.onboarding.version = ONBOARDING_VERSION
        self.config.onboarding.last_device = self.config.device.port_override
        save_config(self.config)
        if self._onboarding_required:
            self._onboarding_required = False
            self.onboardingRequiredChanged.emit()

    def shutdown(self) -> None:
        self._timer.stop()
        if self._streaming:
            self.stopStreaming()
        save_config(self.config)

    @staticmethod
    def _fmt_temp(value: float | None) -> str:
        return "N/A" if value is None else f"{value:04.1f} C"

    @staticmethod
    def _fmt_percent(value: float | None) -> str:
        return "N/A" if value is None else f"{value:05.1f}%"


def run_gui() -> int:
    configure_logging()
    install_crash_hooks()
    logger = get_logger()

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("SmartScreen")
    app.setOrganizationName("DGE Projects")

    vm = SmartScreenViewModel()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("vm", vm)
    qml_path = __file__.replace("app.py", "qml/Main.qml")
    engine.load(qml_path)

    if not engine.rootObjects():
        logger.error("failed to load QML")
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

        diagnostics_action = QAction("Export Diagnostics", menu)
        diagnostics_action.triggered.connect(vm.exportDiagnostics)
        menu.addAction(diagnostics_action)

        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.show()

    exit_code = app.exec()
    vm.shutdown()
    logger.info("app shutdown", extra={"event": "shutdown", "exit_code": int(exit_code)})
    return int(exit_code)
