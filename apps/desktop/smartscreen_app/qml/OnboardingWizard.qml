import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Accessibility

Item {
    id: root
    Rectangle {
        anchors.fill: parent
        color: "#AA030A18"
    }

    Rectangle {
        id: card
        width: Math.min(parent.width * 0.78, 920)
        height: Math.min(parent.height * 0.82, 620)
        anchors.centerIn: parent
        radius: 20
        color: "#101A2D"
        border.color: "#2C4767"
        Accessible.role: Accessible.Dialog
        Accessible.name: "First run setup wizard"

        property int step: 0

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16

            Label {
                text: "Welcome to SmartScreen"
                color: "#ECF4FF"
                font.pixelSize: 32
                font.bold: true
            }

            Label {
                text: "Step " + (card.step + 1) + " of 5"
                color: "#97B1D4"
                font.pixelSize: 14
            }

            StackLayout {
                id: steps
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: card.step

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12
                        Label {
                            text: "This wizard configures your display, permissions, and startup behavior."
                            color: "#E1ECFF"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            text: "Your runtime is fully local. Update checks are manual only."
                            color: "#A8C0E0"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12
                        Label {
                            text: "Detect display device"
                            color: "#E1ECFF"
                            font.pixelSize: 22
                            font.bold: true
                        }
                        Label {
                            text: vm.onboardingDeviceStatus
                            color: "#A8C0E0"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Button {
                            text: "Scan for VID:PID 1A86:5722"
                            Accessible.name: "Scan for supported display"
                            onClicked: vm.scanOnboardingDevice()
                        }
                        Label {
                            text: "If not found, reconnect the USB cable and scan again."
                            color: "#A8C0E0"
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12
                        Label {
                            text: "Permissions"
                            color: "#E1ECFF"
                            font.pixelSize: 22
                            font.bold: true
                        }
                        Label {
                            text: vm.onboardingPermissionText
                            color: "#A8C0E0"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12
                        Label {
                            text: "Startup and device test"
                            color: "#E1ECFF"
                            font.pixelSize: 22
                            font.bold: true
                        }
                        CheckBox {
                            id: launchToggle
                            text: "Launch at login"
                            checked: vm.launchAtLogin
                            onToggled: vm.setOnboardingLaunchAtLogin(checked)
                        }
                        Button {
                            text: "Send test pattern"
                            Accessible.name: "Send onboarding test pattern"
                            onClicked: vm.runOnboardingTestPattern()
                        }
                        Label {
                            text: vm.onboardingDeviceStatus
                            color: "#A8C0E0"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12
                        Label {
                            text: "Setup complete"
                            color: "#E1ECFF"
                            font.pixelSize: 22
                            font.bold: true
                        }
                        Label {
                            text: "You can now stream the full 800x480 dashboard and configure updates, diagnostics, and themes from Settings."
                            color: "#A8C0E0"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: "Back"
                    enabled: card.step > 0
                    onClicked: card.step = Math.max(0, card.step - 1)
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: card.step < 4 ? "Next" : "Finish"
                    onClicked: {
                        if (card.step < 4) {
                            card.step = card.step + 1
                        } else {
                            vm.completeOnboarding()
                        }
                    }
                }
            }
        }
    }
}
