import SwiftUI

struct SettingsView: View {
    @StateObject private var vm = SettingsViewModel()

    var body: some View {
        NavigationStack {
            TabView {
                ScheduleTabView(vm: vm)
                    .tabItem { Label("발송 시간", systemImage: "clock") }

                CrewWorksTabView(vm: vm)
                    .tabItem { Label("CrewWorks", systemImage: "building.2") }

                ExternalMailTabView(vm: vm)
                    .tabItem { Label("외부 메일", systemImage: "envelope") }

                MailContentTabView(vm: vm)
                    .tabItem { Label("메일 내용", systemImage: "doc.text") }
            }
            .navigationTitle("AUTO-MAIL")
            .toolbar {
                ToolbarItemGroup(placement: .bottomBar) {
                    Button("저장") { vm.save() }
                    Button("테스트") { vm.runTest() }
                    Button("실제 발송") { vm.runLive() }
                        .disabled(vm.isRunning)
                }
            }
            .alert(vm.alertTitle, isPresented: $vm.showAlert) {
                Button("확인", role: .cancel) {}
            } message: {
                Text(vm.alertMessage)
            }
            .onAppear {
                vm.load()
                Task { _ = await NotificationScheduler.requestPermission() }
            }
        }
    }
}

struct ScheduleTabView: View {
    @ObservedObject var vm: SettingsViewModel

    var body: some View {
        Form {
            Section("발송 시간 (쉼표 구분)") {
                TextField("09:00, 18:00", text: $vm.timesText)
            }
            Section {
                Toggle("평일만 발송", isOn: $vm.config.schedule.weekdaysOnly)
                Toggle("실제 메일 전송", isOn: $vm.env.sendEmail)
            } footer: {
                Text("실제 전송 OFF = 테스트 모드 (출력만). iOS는 예약 시간에 알림을 보냅니다.")
            }
        }
    }
}

struct CrewWorksTabView: View {
    @ObservedObject var vm: SettingsViewModel

    var body: some View {
        Form {
            Toggle("CrewWorks 내부 메일 사용", isOn: $vm.config.crewworks.enabled)
            Section("받는 사람 (ID)") {
                TextEditor(text: $vm.crewworksRecipientsText)
                    .frame(minHeight: 80)
            }
            Section("로그인") {
                TextField("로그인 ID", text: $vm.env.crewworksUsername)
                SecureField("비밀번호", text: $vm.env.crewworksPassword)
                TextField("OTP (선택)", text: $vm.env.crewworksOTP)
            }
            Section {
                Link("CrewWorks 열기 (Safari)", destination: CrewWorksSender.loginURL)
            } footer: {
                Text("iOS는 Selenium 자동화를 지원하지 않습니다. 테스트 모드에서만 내용 확인이 가능합니다.")
            }
        }
    }
}

struct ExternalMailTabView: View {
    @ObservedObject var vm: SettingsViewModel

    var body: some View {
        Form {
            Toggle("외부 SMTP 메일 사용", isOn: $vm.config.external.enabled)
            Section("받는 사람 (이메일)") {
                TextEditor(text: $vm.externalRecipientsText)
                    .frame(minHeight: 80)
            }
            Section {
                TextField("보내는 사람", text: $vm.env.smtpFrom)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.emailAddress)
                TextField("SMTP 계정", text: $vm.env.smtpUsername)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.emailAddress)
                SecureField("SMTP 비밀번호 (앱 비밀번호)", text: $vm.env.smtpPassword)
                TextField("SMTP 서버", text: $vm.env.smtpHost)
                TextField("SMTP 포트", value: $vm.env.smtpPort, format: .number)
            } header: {
                Text("SMTP")
            } footer: {
                Text("Gmail: smtp.gmail.com / iOS 권장 포트 465 / 앱 비밀번호")
            }
        }
    }
}

struct MailContentTabView: View {
    @ObservedObject var vm: SettingsViewModel

    var body: some View {
        Form {
            Section("제목 ({date}, {time})") {
                TextField("제목", text: $vm.config.mail.subject)
            }
            Section("본문") {
                TextEditor(text: $vm.config.mail.body)
                    .frame(minHeight: 200)
            }
        }
    }
}

#Preview {
    SettingsView()
}
