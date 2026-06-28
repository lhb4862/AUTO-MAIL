# AUTO-MAIL iOS

Windows/Python 버전과 **동일한 구조**의 iOS 앱입니다.

## 폴더 구조 (Python 대응)

| Python (Windows) | iOS (Swift) |
|------------------|-------------|
| `settings_gui.py` | `Views/SettingsView.swift` |
| `main.py` | `Services/MailRunner.swift` |
| `config_store.py` | `Services/ConfigStore.swift` |
| `email_sender.py` | `Services/EmailSender.swift` |
| `crewworks_sender.py` | `Services/CrewWorksSender.swift` |
| `setup_scheduler.ps1` | `Services/NotificationScheduler.swift` |
| `config.json` / `.env` | `Documents/config.json` / `Documents/env.json` |

## Xcode에서 열기

1. Mac에서 **Xcode** 실행
2. **File → New → Project → iOS → App**
3. Product Name: `AUTO-MAIL`, Interface: **SwiftUI**, Language: **Swift**
4. 생성된 프로젝트에 `ios/AUTO-MAIL/` 폴더 안의 Swift 파일을 **드래그하여 추가**
5. 기존 `ContentView.swift` 삭제, `AUTO_MAILApp.swift`를 `@main`으로 사용
6. iPhone 선택 후 **Run (▶)**

또는 터미널(Mac):

```bash
cd ios
open AUTO-MAIL.xcodeproj
```

## 화면 (Windows와 동일)

- **발송 시간** — 시간, 평일만, 실제 전송 ON/OFF
- **CrewWorks** — 내부 메일 설정 (테스트 모드)
- **외부 메일** — SMTP 설정
- **메일 내용** — 제목/본문
- 하단: **저장 / 테스트 / 실제 발송**

## 안전 모드

- **실제 메일 전송** OFF (기본) → 테스트, 콘솔 출력만
- ON → 실제 SMTP 발송

## iOS 제한 사항

| 기능 | Windows | iOS |
|------|---------|-----|
| 외부 SMTP 메일 | ✅ | ✅ |
| CrewWorks Selenium 자동화 | ✅ | ❌ (Safari 링크 + 테스트만) |
| 백그라운드 자동 발송 | 작업 스케줄러 | **로컬 알림** (앱 열어 발송) |

CrewWorks 실제 자동 발송은 **PC `start.bat`** 을 사용하세요.

## Gmail SMTP (iOS)

- SMTP 서버: `smtp.gmail.com`
- 포트: **465** 권장 (SSL)
- 비밀번호: **앱 비밀번호** (일반 비밀번호 X)

## 요구 사항

- Xcode 15+
- iOS 16+
- Mac (iOS 앱 빌드/설치용)

Windows PC만으로는 iOS 앱을 직접 빌드할 수 없습니다. **Mac + Xcode** 또는 **TestFlight** 배포가 필요합니다.
