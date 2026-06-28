import Foundation
import Combine

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var config = AppConfig()
    @Published var env = EnvConfig()

    @Published var timesText = "09:00"
    @Published var crewworksRecipientsText = ""
    @Published var externalRecipientsText = ""

    @Published var alertTitle = ""
    @Published var alertMessage = ""
    @Published var showAlert = false
    @Published var isRunning = false

    private let store = ConfigStore.shared

    func load() {
        config = store.loadConfig()
        env = store.loadEnv()
        timesText = ConfigStore.joinList(config.schedule.times)
        crewworksRecipientsText = ConfigStore.joinList(config.crewworks.recipients)
        externalRecipientsText = ConfigStore.joinList(config.external.recipients)
    }

    func save() {
        config.schedule.times = ConfigStore.parseList(timesText)
        config.crewworks.recipients = ConfigStore.parseList(crewworksRecipientsText)
        config.external.recipients = ConfigStore.parseList(externalRecipientsText)
        store.saveConfig(config)
        store.saveEnv(env)
        Task { await NotificationScheduler.syncSchedule(config: config) }
        showInfo("저장 완료", "설정을 저장했습니다.")
    }

    func runTest() {
        env.sendEmail = false
        run(live: false)
    }

    func runLive() {
        env.sendEmail = true
        run(live: true)
    }

    private func run(live: Bool) {
        config.schedule.times = ConfigStore.parseList(timesText)
        config.crewworks.recipients = ConfigStore.parseList(crewworksRecipientsText)
        config.external.recipients = ConfigStore.parseList(externalRecipientsText)
        store.saveConfig(config)
        store.saveEnv(env)

        isRunning = true
        Task {
            let result = await MailRunner.run(config: config, env: env, force: true)
            isRunning = false
            let prefix = live ? "실제 발송" : "테스트"
            if result.isFullSuccess || (live && result.externalOK == true) {
                alertTitle = "\(prefix) 완료"
            } else if result.isPartialSuccess {
                alertTitle = "\(prefix) 일부 성공"
            } else {
                alertTitle = "\(prefix) 실패"
            }
            alertMessage = result.formattedMessage
            if !live {
                alertMessage = "(실제 전송 없음)\n\n" + alertMessage
            }
            showAlert = true
        }
    }

    private func showInfo(_ title: String, _ message: String) {
        alertTitle = title
        alertMessage = message
        showAlert = true
    }
}
