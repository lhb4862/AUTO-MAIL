import Foundation
import SafariServices

struct CrewWorksSettings {
    let url: String
    let username: String
    let password: String
    let otp: String
}

enum CrewWorksSenderError: LocalizedError {
    case automationNotSupported

    var errorDescription: String? {
        switch self {
        case .automationNotSupported:
            return "iOS에서는 CrewWorks 브라우저 자동화(Selenium)를 지원하지 않습니다. PC 앱을 사용하거나 Safari에서 수동 발송해 주세요."
        }
    }
}

enum CrewWorksSender {
    static func send(
        recipients: [String],
        subject: String,
        body: String,
        dryRun: Bool,
        settings: CrewWorksSettings
    ) async throws {
        guard !recipients.isEmpty else { return }

        if dryRun {
            print("[CrewWorks 내부 메일]")
            print("  수신자: \(recipients.joined(separator: ", "))")
            print("  제목:   \(subject)")
            print("  본문:   \(body)")
            return
        }

        throw CrewWorksSenderError.automationNotSupported
    }

    static var loginURL: URL {
        URL(string: "https://gw.yesyoungin.com/Main")!
    }
}
