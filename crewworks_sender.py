"""CrewWorks internal mail sender (Selenium)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

MAX_RETRIES = 3
RETRY_DELAY_SEC = 2


@dataclass
class CrewWorksConfig:
    url: str
    username: str
    password: str
    otp: str = ""
    headless: bool = True


def _print_dry_run(recipients: Iterable[str], subject: str, body: str) -> None:
    print("[CrewWorks 내부 메일]")
    print(f"  수신자: {', '.join(recipients)}")
    print(f"  제목:   {subject}")
    print(f"  본문:   {body}")


def _login(driver, config: CrewWorksConfig) -> None:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    driver.get(config.url)
    wait = WebDriverWait(driver, 20)

    username_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[name*='id'], input[name*='user']"))
    )
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

    username_input.clear()
    username_input.send_keys(config.username)
    password_input.clear()
    password_input.send_keys(config.password)

    login_button = driver.find_element(
        By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], .btn-login, button.btn"
    )
    login_button.click()

    if config.otp:
        otp_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'][placeholder*='OTP'], input[name*='otp'], input[name*='OTP']"))
        )
        otp_input.send_keys(config.otp)
        confirm_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn-primary, button.btn")
        confirm_button.click()


def _compose_and_send(driver, recipients: list[str], subject: str, body: str) -> None:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    wait = WebDriverWait(driver, 20)

    mail_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "메일")
    if not mail_links:
        mail_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Mail")
    if mail_links:
        mail_links[0].click()

    compose_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "작성")
    if not compose_links:
        compose_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Compose")
    if compose_links:
        compose_links[0].click()

    recipient_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name*='to'], input[name*='recipient'], textarea[name*='to']"))
    )
    recipient_input.send_keys(", ".join(recipients))

    subject_input = driver.find_element(By.CSS_SELECTOR, "input[name*='subject'], input[name*='title']")
    subject_input.send_keys(subject)

    body_input = driver.find_element(By.CSS_SELECTOR, "textarea[name*='body'], textarea[name*='content'], iframe")
    if body_input.tag_name.lower() == "iframe":
        driver.switch_to.frame(body_input)
        body_input = driver.find_element(By.CSS_SELECTOR, "body")
        driver.switch_to.default_content()

    body_input.send_keys(body)

    send_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[value*='전송'], input[value*='Send']")
    send_button.click()


def send_crewworks_mail(
    recipients: list[str],
    subject: str,
    body: str,
    *,
    dry_run: bool,
    config: CrewWorksConfig | None = None,
) -> bool:
    if not recipients:
        print("[CrewWorks 내부 메일] 수신자가 없어 건너뜁니다.")
        return True

    if dry_run:
        _print_dry_run(recipients, subject, body)
        return True

    if config is None:
        raise ValueError("config is required for live send.")

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    if config.headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            _login(driver, config)
            _compose_and_send(driver, recipients, subject, body)
            print(f"[CrewWorks 내부 메일] 전송 완료: {', '.join(recipients)}")
            return True
        except Exception as exc:
            last_error = exc
            print(f"[CrewWorks 내부 메일] 시도 {attempt}/{MAX_RETRIES} 실패: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)
        finally:
            if driver is not None:
                driver.quit()

    raise RuntimeError(f"CrewWorks mail send failed: {last_error}")