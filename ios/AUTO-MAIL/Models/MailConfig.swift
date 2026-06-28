import Foundation

struct ScheduleConfig: Codable, Equatable {
    var times: [String] = ["09:00"]
    var weekdaysOnly: Bool = false

    enum CodingKeys: String, CodingKey {
        case times
        case weekdaysOnly = "weekdays_only"
    }
}

struct CrewWorksConfig: Codable, Equatable {
    var enabled: Bool = true
    var recipients: [String] = []
}

struct ExternalConfig: Codable, Equatable {
    var enabled: Bool = false
    var recipients: [String] = []
}

struct MailTemplate: Codable, Equatable {
    var subject: String = "[{date}] 정기 안내"
    var body: String = "안녕하세요.\n\n{date} {time} 정기 메일입니다.\n\n감사합니다."
}

struct AppConfig: Codable, Equatable {
    var schedule: ScheduleConfig = .init()
    var crewworks: CrewWorksConfig = .init()
    var external: ExternalConfig = .init()
    var mail: MailTemplate = .init()
}

struct EnvConfig: Codable, Equatable {
    var sendEmail: Bool = false
    var crewworksURL: String = "https://gw.yesyoungin.com/Main"
    var crewworksUsername: String = ""
    var crewworksPassword: String = ""
    var crewworksOTP: String = ""
    var smtpHost: String = "smtp.gmail.com"
    var smtpPort: Int = 465
    var smtpUsername: String = ""
    var smtpPassword: String = ""
    var smtpFrom: String = ""
    var smtpUseTLS: Bool = true

    enum CodingKeys: String, CodingKey {
        case sendEmail = "SEND_EMAIL"
        case crewworksURL = "CREWWORKS_URL"
        case crewworksUsername = "CREWWORKS_USERNAME"
        case crewworksPassword = "CREWWORKS_PASSWORD"
        case crewworksOTP = "CREWWORKS_OTP"
        case smtpHost = "SMTP_HOST"
        case smtpPort = "SMTP_PORT"
        case smtpUsername = "SMTP_USERNAME"
        case smtpPassword = "SMTP_PASSWORD"
        case smtpFrom = "SMTP_FROM"
        case smtpUseTLS = "SMTP_USE_TLS"
    }
}

struct RunResult: Equatable {
    var crewworksOK: Bool?
    var externalOK: Bool?
    var crewworksError: String?
    var externalError: String?
    var subject: String = ""

    var isPartialSuccess: Bool {
        let oks = [crewworksOK, externalOK].compactMap { $0 }.filter { $0 }.count
        let fails = [crewworksOK, externalOK].compactMap { $0 }.filter { !$0 }.count
        return oks > 0 && fails > 0
    }

    var isFullSuccess: Bool {
        let checks = [crewworksOK, externalOK].compactMap { $0 }
        return !checks.isEmpty && checks.allSatisfy { $0 }
    }

    var formattedMessage: String {
        var lines = ["발송 결과", ""]
        if !subject.isEmpty {
            lines.append("제목: \(subject)")
            lines.append("")
        }
        if let ok = crewworksOK {
            lines.append(ok ? "CrewWorks 내부 메일: 성공" : "CrewWorks 내부 메일: 실패")
            if let err = crewworksError, !ok { lines.append("  사유: \(err)") }
        }
        if let ok = externalOK {
            lines.append(ok ? "외부 이메일: 성공" : "외부 이메일: 실패")
            if let err = externalError, !ok { lines.append("  사유: \(err)") }
        }
        return lines.joined(separator: "\n")
    }
}
