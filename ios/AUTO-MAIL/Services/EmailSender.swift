import Foundation
import Network

struct SmtpSettings {
    let host: String
    let port: Int
    let username: String
    let password: String
    let fromAddress: String
    let useTLS: Bool
}

enum EmailSenderError: LocalizedError {
    case smtpFailed(String)

    var errorDescription: String? {
        switch self {
        case .smtpFailed(let msg): return msg
        }
    }
}

enum EmailSender {
    static func send(
        recipients: [String],
        subject: String,
        body: String,
        dryRun: Bool,
        settings: SmtpSettings
    ) async throws {
        guard !recipients.isEmpty else { return }

        if dryRun {
            print("[외부 이메일]")
            print("  수신자: \(recipients.joined(separator: ", "))")
            print("  제목:   \(subject)")
            print("  본문:   \(body)")
            return
        }

        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            SmtpSession(settings: settings).send(
                recipients: recipients,
                subject: subject,
                body: body
            ) { result in
                continuation.resume(with: result)
            }
        }
    }
}

private final class SmtpSession {
    private let settings: SmtpSettings

    init(settings: SmtpSettings) {
        self.settings = settings
    }

    func send(
        recipients: [String],
        subject: String,
        body: String,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                try self.sendSync(recipients: recipients, subject: subject, body: body)
                completion(.success(()))
            } catch {
                completion(.failure(error))
            }
        }
    }

    private func sendSync(recipients: [String], subject: String, body: String) throws {
        let port = settings.port
        let useTLS = settings.useTLS && port == 465
        let params: NWParameters = useTLS ? .tls : .tcp
        guard let nwPort = NWEndpoint.Port(rawValue: UInt16(port)) else {
            throw EmailSenderError.smtpFailed("Invalid port")
        }

        let sem = DispatchSemaphore(value: 0)
        var sessionError: Error?
        var inbound = Data()
        var step = 0
        let steps: [(String) -> String?] = [
            { _ in nil },
            { _ in "EHLO automail.local" },
            { line in line.hasPrefix("250") && !settings.useTLS ? self.authLines().first : (settings.useTLS && port == 587 ? "STARTTLS" : self.authLines().first) },
        ]

        let conn = NWConnection(host: NWEndpoint.Host(settings.host), port: nwPort, using: params)
        conn.stateUpdateHandler = { state in
            if case .failed(let err) = state {
                sessionError = EmailSenderError.smtpFailed(err.localizedDescription)
                sem.signal()
            }
        }

        func readResponse() -> String? {
            let group = DispatchGroup()
            group.enter()
            var response = ""
            func recv() {
                conn.receive(minimumIncompleteLength: 1, maximumLength: 8192) { data, _, _, _ in
                    if let data, let text = String(data: data, encoding: .utf8) {
                        response += text
                        if text.contains("\r\n") {
                            group.leave()
                        } else {
                            recv()
                        }
                    } else {
                        group.leave()
                    }
                }
            }
            recv()
            group.wait()
            return response
        }

        func send(_ text: String) {
            let payload = (text + "\r\n").data(using: .utf8)!
            conn.send(content: payload, completion: .contentProcessed { _ in })
        }

        conn.start(queue: .global())
        _ = readResponse()
        send("EHLO automail.local")
        _ = readResponse()

        if settings.useTLS && port == 587 {
            send("STARTTLS")
            _ = readResponse()
            throw EmailSenderError.smtpFailed("iOS에서 Gmail은 포트 465(SSL) 사용을 권장합니다. SMTP 포트를 465로 변경해 주세요.")
        }

        for line in authLines() { send(line) }
        for line in authLines().dropFirst() { _ = readResponse() }
        _ = readResponse()

        send("MAIL FROM:<\(settings.fromAddress)>")
        _ = readResponse()
        for r in recipients {
            send("RCPT TO:<\(r)>")
            _ = readResponse()
        }
        send("DATA")
        _ = readResponse()

        let encodedSubject = "=?UTF-8?B?\(Data(subject.utf8).base64EncodedString())?="
        let encodedBody = Data(body.utf8).base64EncodedString()
        let message = """
        From: \(settings.fromAddress)
        To: \(recipients.joined(separator: ", "))
        Subject: \(encodedSubject)
        MIME-Version: 1.0
        Content-Type: text/plain; charset=UTF-8
        Content-Transfer-Encoding: base64

        \(encodedBody)
        .
        """
        send(message)
        _ = readResponse()
        send("QUIT")
        conn.cancel()
        sem.wait()
        if let sessionError { throw sessionError }
    }

    private func authLines() -> [String] {
        let user = Data(settings.username.utf8).base64EncodedString()
        let pass = Data(settings.password.utf8).base64EncodedString()
        return ["AUTH LOGIN", user, pass]
    }
}
