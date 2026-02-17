import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Accessibility

ApplicationWindow {
    id: root
    width: 1280
    height: 800
    visible: true
    title: "SmartScreen"

    property bool darkMode: vm.uiTheme === "dark" || vm.uiTheme === "auto"
    property color bgTop: darkMode ? "#0A1224" : "#F2F6FF"
    property color bgBottom: darkMode ? "#132A3B" : "#DCE7F8"
    property color cardBg: darkMode ? "#16263A" : "#FFFFFF"
    property color cardBorder: darkMode ? "#294662" : "#C0CFDE"
    property color textPrimary: darkMode ? "#EAF2FF" : "#0A1A2B"
    property color textSecondary: darkMode ? "#ADC4E2" : "#314A61"
    property color accentA: "#2CCEF6"
    property color accentB: "#8CFFB5"

    font.family: "Space Grotesk"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.bgTop }
            GradientStop { position: 1.0; color: root.bgBottom }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Rectangle {
            id: controlPanel
            Layout.preferredWidth: 420
            Layout.fillHeight: true
            radius: 18
            color: root.cardBg
            border.color: root.cardBorder
            Accessible.role: Accessible.Pane
            Accessible.name: "Control panel"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Label {
                    text: "SmartScreen"
                    color: root.textPrimary
                    font.pixelSize: 34
                    font.bold: true
                }

                Label {
                    text: "Version " + vm.appVersion + " - cross-platform display controller"
                    color: root.textSecondary
                    font.pixelSize: 14
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: root.cardBorder }

                Label { text: vm.deviceStatus; color: root.textPrimary; font.pixelSize: 14 }
                Label { text: "FPS " + vm.fps.toFixed(2); color: root.textSecondary; font.pixelSize: 13 }
                Label { text: "Throughput " + (vm.throughput / 1024).toFixed(1) + " KB/s"; color: root.textSecondary; font.pixelSize: 13 }

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: vm.streaming ? "Streaming" : "Start"
                        enabled: !vm.streaming
                        Accessible.name: "Start streaming"
                        focusPolicy: Qt.StrongFocus
                        onClicked: vm.startStreaming()
                    }
                    Button {
                        text: "Stop"
                        enabled: vm.streaming
                        Accessible.name: "Stop streaming"
                        focusPolicy: Qt.StrongFocus
                        onClicked: vm.stopStreaming()
                    }
                    Button {
                        text: "Reconnect"
                        Accessible.name: "Reconnect display"
                        focusPolicy: Qt.StrongFocus
                        onClicked: vm.reconnect()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Port"; color: root.textSecondary }
                    TextField {
                        id: portField
                        Layout.fillWidth: true
                        placeholderText: "Auto"
                        text: vm.portOverride
                        Accessible.name: "Serial port override"
                        selectByMouse: true
                        onEditingFinished: vm.setPortOverride(text)
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Brightness"; color: root.textSecondary }
                    Slider {
                        id: brightness
                        from: 0
                        to: 100
                        value: 80
                        Layout.fillWidth: true
                        Accessible.name: "Brightness"
                        onMoved: vm.setBrightness(Math.round(value))
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Poll ms"; color: root.textSecondary }
                    Slider {
                        id: pollMs
                        from: 200
                        to: 2000
                        stepSize: 50
                        value: vm.pollMs
                        Layout.fillWidth: true
                        Accessible.name: "Polling interval"
                        onMoved: vm.setPollMs(Math.round(value))
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "UI theme"; color: root.textSecondary }
                    ComboBox {
                        id: themeMode
                        Layout.fillWidth: true
                        model: ["auto", "dark", "light"]
                        currentIndex: model.indexOf(vm.uiTheme)
                        Accessible.name: "UI theme mode"
                        onActivated: vm.setUiTheme(currentText)
                    }
                }

                CheckBox {
                    id: loginToggle
                    text: "Launch at login"
                    checked: vm.launchAtLogin
                    Accessible.name: "Launch at login"
                    onToggled: vm.setLaunchAtLogin(checked)
                }

                CheckBox {
                    id: reduceMotion
                    text: "Reduced motion"
                    checked: vm.reducedMotion
                    Accessible.name: "Reduced motion"
                    onToggled: vm.setReducedMotion(checked)
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: root.cardBorder }

                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Updates"; color: root.textPrimary; font.bold: true }
                    Item { Layout.fillWidth: true }
                    ComboBox {
                        id: updateChannel
                        model: ["stable", "beta"]
                        currentIndex: model.indexOf(vm.updateChannel)
                        Accessible.name: "Update channel"
                        onActivated: vm.setUpdateChannel(currentText)
                    }
                }

                Label { text: vm.updateStatus; color: root.textSecondary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Label { text: vm.updateVersion.length > 0 ? ("Latest " + vm.updateVersion) : ""; color: root.textSecondary }

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: "Check updates"
                        Accessible.name: "Check updates"
                        onClicked: vm.checkForUpdates(updateChannel.currentText)
                    }
                    Button {
                        text: "Open release"
                        enabled: vm.updateUrl.length > 0
                        Accessible.name: "Open release page"
                        onClicked: vm.openUpdateUrl()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: "Export diagnostics"
                        Accessible.name: "Export diagnostics bundle"
                        onClicked: vm.exportDiagnostics()
                    }
                    Button {
                        text: "Open bundle"
                        enabled: vm.diagnosticsPath.length > 0
                        Accessible.name: "Open diagnostics location"
                        onClicked: vm.openDiagnosticsPath()
                    }
                }

                Label {
                    text: vm.diagnosticsPath.length > 0 ? vm.diagnosticsPath : ""
                    color: root.textSecondary
                    wrapMode: Text.WrapAnywhere
                    Layout.fillWidth: true
                }

                Item { Layout.fillHeight: true }
            }
        }

        Rectangle {
            id: previewPanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 18
            color: root.cardBg
            border.color: root.cardBorder
            Accessible.role: Accessible.Pane
            Accessible.name: "Preview panel"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 14

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "Live Dashboard Preview"
                        color: root.textPrimary
                        font.pixelSize: 25
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    ComboBox {
                        id: themeSelect
                        model: JSON.parse(vm.themesJson)
                        Accessible.name: "Dashboard theme"
                        onActivated: vm.setDashboardTheme(currentText)
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 14
                    color: darkMode ? "#0D192D" : "#EAF1FB"
                    border.color: root.cardBorder

                    Image {
                        anchors.fill: parent
                        anchors.margins: 10
                        source: vm.previewUrl
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        cache: false
                    }
                }

                Label {
                    text: vm.updateNotes.length > 0 ? vm.updateNotes : ""
                    color: root.textSecondary
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    visible: vm.updateNotes.length > 0
                }
            }
        }
    }

    Rectangle {
        id: recoveryBanner
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 18
        radius: 12
        height: vm.recoveryVisible ? 64 : 0
        color: "#3A2020"
        border.color: "#D86C6C"
        visible: vm.recoveryVisible

        Behavior on height {
            enabled: !vm.reducedMotion
            NumberAnimation { duration: 180 }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12
            Label {
                text: vm.recoveryState
                color: "#FFDADA"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Button {
                text: "Retry now"
                onClicked: vm.retryRecoveryNow()
                Accessible.name: "Retry connection now"
            }
            Button {
                text: "Export diagnostics"
                onClicked: vm.exportDiagnostics()
                Accessible.name: "Export diagnostics from recovery"
            }
        }
    }

    OnboardingWizard {
        id: onboarding
        anchors.fill: parent
        visible: vm.onboardingRequired
        z: 100
    }
}
