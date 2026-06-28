import Foundation

enum MailRunner {
    static func run(config: AppConfig, env: EnvConfig, force: Bool = true) async -> RunResult {
        let now = Date()
        var result = RunResult()

        if config.schedule.weekdaysOnly && !force && !isWeekday(now) {
            ConfigStore.shared.appendLog("주말이므로 발송을 건너뜁니다.")
            return result
        }

        if !force && !matchesSchedule(now: now, times: config.schedule.times) {
            ConfigStore.shared.appendLog("발송 시간이 아닙니다.")
            return result
        }

        let dryRun = !env.sendEmail
        let subject = renderTemplate(config.mail.subject, now: now)
        let body = renderTemplate(config.mail.body, now: now)
        result.subject = subject

        if config.crewworks.enabled {
            do {
                try await CrewWorksSender.send(
                    recipients: config.crewworks.recipients,
                    subject: subject,
                    body: body,
                    dryRun: dryRun,
                    settings: CrewWorksSettings(
                        url: env.crewworksURL,
                        username: env.crewworksUsername,
                        password: env.crewworksPassword,
                        otp: env.crewworksOTP
                    )
                )
                result.crewworksOK = true
            } catch {
                result.crewworksOK = false
                result.crewworksError = error.localizedDescription
            }
        }

        if config.external.enabled {
            do {
                try await EmailSender.send(
                    recipients: config.external.recipients,
                    subject: subject,
                    body: body,
                    dryRun: dryRun,
                    settings: SmtpSettings(
                        host: env.smtpHost,
                        port: env.smtpPort,
                        username: env.smtpUsername,
                        password: env.smtpPassword,
                        fromAddress: env.smtpFrom.isEmpty ? env.smtpUsername : env.smtpFrom,
                        useTLS: env.smtpUseTLS
                    )
                )
                result.externalOK = true
            } catch {
                result.externalOK = false
                result.externalError = error.localizedDescription
            }
        }

        let mode = dryRun ? "DRY-RUN" : "LIVE"
        ConfigStore.shared.appendLog("\(mode) subject='\(subject)' crewworks=\(result.crewworksOK.map { $0 ? "ok" : "error" } ?? "-") external=\(result.externalOK.map { $0 ? "ok" : "error" } ?? "-")")
        return result
    }

    private static func isWeekday(_ date: Date) -> Bool {
        let w = Calendar.current.component(.weekday, from: date)
        return w >= 2 && w <= 6
    }

    private static func matchesSchedule(now: Date, times: [String], toleranceMinutes: Int = 5) -> Bool {
        guard !times.isEmpty else { return true }
        let cal = Calendar.current
        let current = cal.component(.hour, from: now) * 60 + cal.component(.minute, from: now)
        for t in times {
            let parts = t.split(separator: ":")
            guard parts.count == 2, let h = Int(parts[0]), let m = Int(parts[1]) else { continue }
            if abs(current - (h * 60 + m)) <= toleranceMinutes { return true }
        }
        return false
    }

    private static func renderTemplate(_ template: String, now: Date) -> String {
        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        let date = df.string(from: now)
        df.dateFormat = "HH:mm"
        let time = df.string(from: now)
        return template
            .replacingOccurrences(of: "{date}", with: date)
            .replacingOccurrences(of: "{time}", with: time)
    }
}
