import Foundation

final class ConfigStore {
    static let shared = ConfigStore()

    private let configURL: URL
    private let envURL: URL
    private let logURL: URL

    private init() {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        configURL = dir.appendingPathComponent("config.json")
        envURL = dir.appendingPathComponent("env.json")
        logURL = dir.appendingPathComponent("mail_log.txt")
    }

    func loadConfig() -> AppConfig {
        load(from: configURL, as: AppConfig.self) ?? AppConfig()
    }

    func saveConfig(_ config: AppConfig) {
        save(config, to: configURL)
    }

    func loadEnv() -> EnvConfig {
        load(from: envURL, as: EnvConfig.self) ?? EnvConfig()
    }

    func saveEnv(_ env: EnvConfig) {
        save(env, to: envURL)
    }

    func appendLog(_ message: String) {
        let ts = ISO8601DateFormatter().string(from: Date())
        let line = "[\(ts)] \(message)\n"
        if FileManager.default.fileExists(atPath: logURL.path) {
            if let handle = try? FileHandle(forWritingTo: logURL) {
                handle.seekToEndOfFile()
                handle.write(line.data(using: .utf8)!)
                try? handle.close()
            }
        } else {
            try? line.write(to: logURL, atomically: true, encoding: .utf8)
        }
    }

    static func parseList(_ text: String) -> [String] {
        text
            .replacingOccurrences(of: "\n", with: ",")
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
    }

    static func joinList(_ items: [String]) -> String {
        items.joined(separator: ", ")
    }

    private func load<T: Decodable>(from url: URL, as type: T.Type) -> T? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        let decoder = JSONDecoder()
        return try? decoder.decode(T.self, from: data)
    }

    private func save<T: Encodable>(_ value: T, to url: URL) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        guard let data = try? encoder.encode(value) else { return }
        try? data.write(to: url, options: .atomic)
    }
}
