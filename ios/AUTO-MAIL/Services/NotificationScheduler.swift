import Foundation
import UserNotifications

enum NotificationScheduler {
    static func requestPermission() async -> Bool {
        (try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound])) ?? false
    }

    static func syncSchedule(config: AppConfig) async {
        let center = UNUserNotificationCenter.current()
        center.removeAllPendingNotificationRequests()

        guard !config.schedule.times.isEmpty else { return }

        for time in config.schedule.times {
            let parts = time.split(separator: ":")
            guard parts.count == 2, let hour = Int(parts[0]), let minute = Int(parts[1]) else { continue }

            var date = DateComponents()
            date.hour = hour
            date.minute = minute

            let content = UNMutableNotificationContent()
            content.title = "AUTO-MAIL"
            content.body = "예약된 메일 발송 시간입니다. 앱을 열어 발송을 확인하세요."
            content.sound = .default

            if config.schedule.weekdaysOnly {
                for weekday in 2...6 {
                    date.weekday = weekday
                    let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
                    let id = "automail-\(time)-wd\(weekday)"
                    center.add(UNNotificationRequest(identifier: id, content: content, trigger: trigger))
                }
            } else {
                let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
                center.add(UNNotificationRequest(identifier: "automail-\(time)", content: content, trigger: trigger))
            }
        }
    }
}
