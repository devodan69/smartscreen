import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1200
    height: 760
    visible: true
    title: "SmartScreen"
    color: "#0A0F1D"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0A0F1D" }
            GradientStop { position: 1.0; color: "#172445" }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 420
            radius: 18
            color: "#1A253F"
            border.color: "#2B3A60"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 14

                Label {
                    text: "SmartScreen"
                    color: "#F4F7FF"
                    font.pixelSize: 34
                    font.bold: true
                }

                Label {
                    text: "USB Serial Display Controller"
                    color: "#A9B5D1"
                    font.pixelSize: 16
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#2F426D" }

                Label { text: vm.deviceStatus; color: "#8CFFB5"; font.pixelSize: 15 }
                Label { text: "FPS " + vm.fps.toFixed(2); color: "#D5E2FF"; font.pixelSize: 14 }
                Label { text: "Throughput " + (vm.throughput / 1024).toFixed(1) + " KB/s"; color: "#D5E2FF"; font.pixelSize: 14 }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#2F426D" }

                Label { text: vm.cpuText; color: "#F4F7FF"; font.pixelSize: 14 }
                Label { text: vm.gpuText; color: "#F4F7FF"; font.pixelSize: 14 }
                Label { text: vm.ramText; color: "#F4F7FF"; font.pixelSize: 14 }
                Label { text: vm.netText; color: "#F4F7FF"; font.pixelSize: 14 }
                Label { text: vm.diskText; color: "#F4F7FF"; font.pixelSize: 14 }
                Label { text: vm.clockText; color: "#B9C6E8"; font.pixelSize: 13 }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#2F426D" }

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: vm.streaming ? "Streaming" : "Start"
                        enabled: !vm.streaming
                        onClicked: vm.startStreaming()
                    }
                    Button {
                        text: "Stop"
                        enabled: vm.streaming
                        onClicked: vm.stopStreaming()
                    }
                    Button {
                        text: "Reconnect"
                        onClicked: vm.reconnect()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Brightness"; color: "#D5E2FF" }
                    Slider {
                        id: brightness
                        from: 0
                        to: 100
                        value: 80
                        Layout.fillWidth: true
                        onMoved: vm.setBrightness(Math.round(value))
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Poll ms"; color: "#D5E2FF" }
                    Slider {
                        id: pollMs
                        from: 200
                        to: 2000
                        stepSize: 50
                        value: 500
                        Layout.fillWidth: true
                        onMoved: vm.setPollMs(Math.round(value))
                    }
                }

                CheckBox {
                    text: "Launch at login"
                    checked: false
                    onToggled: vm.setLaunchAtLogin(checked)
                }

                Item { Layout.fillHeight: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 18
            color: "#121B32"
            border.color: "#2B3A60"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 16

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "Live Dashboard Preview"
                        color: "#F4F7FF"
                        font.pixelSize: 24
                        font.bold: true
                    }

                    Item { Layout.fillWidth: true }

                    ComboBox {
                        id: themeSelect
                        model: JSON.parse(vm.themesJson)
                        onActivated: vm.setDashboardTheme(currentText)
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#0F1630"
                    radius: 14
                    border.color: "#2F426D"

                    Image {
                        anchors.fill: parent
                        anchors.margins: 12
                        source: vm.previewUrl
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        cache: false
                    }
                }
            }
        }
    }
}
