import os
import time
import json
import threading
import pyperclip
import subprocess
import traceback
import re
import html as html_lib
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ---
AI_STUDIO_URL = 'https://chat.deepseek.com'
HISTORY_FILE = 'task_history.json'
PROFILES_FILE = 'profiles.json'
APP_STATE_FILE = 'app_state.json'
ACCOUNT_STATS_FILE = 'account_stats.json'  # Статистика глав и заморозки по аккаунтам
CHAPTERS_FREEZE_LIMIT = 100  # После скольки глав в сутки аккаунт замораживается
MAX_CJK_FIX_ATTEMPTS = 3    # Сколько раз просить DeepSeek переписать главу, если в [B] остались китайские иероглифы
MAX_PARAGRAPH_FIX_ATTEMPTS = 3  # Сколько раз просить DeepSeek переразбить абзацы/сократить предложения
SENTENCES_PER_PARAGRAPH_LIMIT = 5   # Максимум предложений в одном абзаце
PARAGRAPH_MAX_LENGTH = 555   # Максимум символов в одном абзаце (фиксированное значение)
MIN_LINES_PER_CHAPTER = 70   # Минимум строк в главе (проверка после перевода)
MAX_LINES_FIX_ATTEMPTS = 3   # Сколько раз просить DeepSeek расширить главу до 70+ строк

# Название и текст главы-акции, которую добавляет кнопка "🎁 Добавить акцию"
# в карточке книги (см. TaskCard.add_promo_chapter).
PROMO_CHAPTER_TITLE = '🔥 Платишь за главы — получаешь целую книгу. Честная акция!'
PROMO_CHAPTER_TEXT = (
    'Ребята, у меня для вас маленькая, но очень приятная движуха! 🌟\n'
    '📌 Суть простая:\n'
    'Покупаешь платные главы в книге на общую сумму от 500 рублей — и одну любую книгу из моего профиля ты забираешь абсолютно бесплатно. 🎁\n'
    '📎 Как это работает?\n'
    'Открываешь книгу и покупаешь главы так, чтобы чек вышел от 500 ₽.\n'
    'Делаешь скриншот покупки — это и есть твой пруф\n'
    'Отправляешь скриншот мне в личные сообщения и пишешь, какую книгу из моего профиля хочешь получить.\n'
    'Я дарю тебе выбранную книгу. Всё честно, без подвоха! ✨\n'
    '💡 Книгу можно выбрать любую — ту, на которую давно глаз положил(а), или ту, которую советовали друзья.\n'
    'Не откладывай — такая щедрость не каждый день случается 😉\n'
    'P.S Считаются только те покупки, которые были совершены с 31.07.2026 .'
)

ctk.set_appearance_mode('Dark')

THEMES = {
    # Минималистичные, современные палитры — один спокойный акцент,
    # нейтральные фоны, мягкие контрасты (в духе Linear / Notion / Vercel).
    'Оникс': {
        'bg': '#0b0b0d',
        'sidebar': '#111113',
        'card': '#161618',
        'card_border': '#232326',
        'accent_green': '#6e8bff',
        'hover_green': '#89a1ff',
        'red': '#f0546a',
        'text_main': '#eeeef0',
        'text_dim': '#87878f',
        'entry_bg': '#0f0f11',
        'scrollable': '#131315',
        'tabs': '#111113',
        'label_dim': '#4b4b52',
        'ctk_mode': 'Dark',
    },
    'Слоновая кость': {
        'bg': '#faf9f7',
        'sidebar': '#f2f0ec',
        'card': '#ffffff',
        'card_border': '#e6e3dd',
        'accent_green': '#3f63e0',
        'hover_green': '#5578f0',
        'red': '#d94f5c',
        'text_main': '#1c1c1e',
        'text_dim': '#8a8a8f',
        'entry_bg': '#ffffff',
        'scrollable': '#f4f2ee',
        'tabs': '#f2f0ec',
        'label_dim': '#b3b0a8',
        'ctk_mode': 'Light',
    },
    'Графит': {
        'bg': '#141416',
        'sidebar': '#1a1a1d',
        'card': '#1f1f23',
        'card_border': '#2c2c31',
        'accent_green': '#9d8cff',
        'hover_green': '#b0a2ff',
        'red': '#ff6b7a',
        'text_main': '#e9e9ec',
        'text_dim': '#8c8c94',
        'entry_bg': '#18181b',
        'scrollable': '#1c1c20',
        'tabs': '#1a1a1d',
        'label_dim': '#4f4f57',
        'ctk_mode': 'Dark',
    },
    'Изумруд': {
        'bg': '#0e1512',
        'sidebar': '#131c18',
        'card': '#18211d',
        'card_border': '#26332c',
        'accent_green': '#3ecf8e',
        'hover_green': '#5adba0',
        'red': '#ff6262',
        'text_main': '#e6f2ec',
        'text_dim': '#7fa090',
        'entry_bg': '#101713',
        'scrollable': '#141d18',
        'tabs': '#131c18',
        'label_dim': '#33473c',
        'ctk_mode': 'Dark',
    },
    'Туман': {
        'bg': '#f4f5f7',
        'sidebar': '#eceef2',
        'card': '#ffffff',
        'card_border': '#dee1e8',
        'accent_green': '#2f9e6e',
        'hover_green': '#3bb480',
        'red': '#e0505f',
        'text_main': '#1e2126',
        'text_dim': '#767c88',
        'entry_bg': '#ffffff',
        'scrollable': '#eef0f4',
        'tabs': '#eceef2',
        'label_dim': '#b7bcc6',
        'ctk_mode': 'Light',
    },
    'Полночь': {
        'bg': '#0a0d16',
        'sidebar': '#0f1320',
        'card': '#141a29',
        'card_border': '#212a3e',
        'accent_green': '#5b9dff',
        'hover_green': '#78b0ff',
        'red': '#ff5c7a',
        'text_main': '#e4e9f5',
        'text_dim': '#6d7793',
        'entry_bg': '#0c1019',
        'scrollable': '#101526',
        'tabs': '#0f1320',
        'label_dim': '#2c3550',
        'ctk_mode': 'Dark',
    },
}

CURRENT_THEME = 'Оникс'
COLORS = dict(THEMES[CURRENT_THEME])

STOP_EVENT = threading.Event()
CLIPBOARD_LOCK = threading.Lock()
RESTART_DELAY_SEC = 8          # Пауза перед автоперезапуском задачи после сбоя/ошибки
RESTART_DELAY_FROZEN_SEC = 600  # Пауза перед автоперезапуском, если все аккаунты книги заморожены
DRIVER_INSTALL_LOCK = threading.Lock()
GLOSSARY_WRITE_LOCK = threading.Lock()  # защищает файл промта (data['pr']) от гонок при дозаписи глоссария
CHROMEDRIVER_PATH = None

# Профили, чей Chrome сейчас реально открыт и работает в каком-либо потоке.
# kill_chrome_processes() больше не убивает вообще все chrome.exe в системе —
# он спрашивает этот реестр и не трогает процессы защищённых профилей, чтобы
# не убивать браузер "осиротевшего" потока (например, после handoff при смене
# аккаунта), пока sequential_manager убивает Chrome предыдущей книги.
ACTIVE_PROFILES_LOCK = threading.Lock()
ACTIVE_PROFILES = set()

# --- МОНИТОРИНГ БАЛАНСА RULATE (Windows-уведомления при изменении) ---
# Работает полностью в фоновом потоке через requests (НЕ трогает Selenium-драйвер,
# чтобы не конфликтовать с параллельными командами основного потока — WebDriver не
# потокобезопасен). Основной поток лишь изредка (раз в главу) обновляет "снимок" кук
# в RULATE_COOKIE_SNAPSHOTS — этого достаточно, сессия RuLate живёт долго.
BALANCE_STATE_FILE = 'balance_state.json'
BALANCE_POLL_INTERVAL_SEC = 20
# Имя профиля, с которого присылаются уведомления об изменении баланса RuLate.
# Если оставить пустой строкой — автоматически выбирается ПЕРВЫЙ аккаунт, который
# начнёт работу (первый вызов _ensure_balance_watch), и уведомления будут приходить
# только с него. Чтобы жёстко закрепить конкретный аккаунт — впишите сюда его имя
# профиля (как оно называется в менеджере профилей), например: 'Профиль_1'.
BALANCE_NOTIFY_PROFILE = ''
RULATE_COOKIE_LOCK = threading.Lock()
RULATE_COOKIE_SNAPSHOTS = {}   # profile_name -> список cookie-словарей из driver.get_cookies()
BALANCE_WATCH_LOCK = threading.Lock()
BALANCE_WATCH_THREADS = {}     # profile_name -> Thread


def show_windows_notification(title, message):
    """Показывает нативное всплывающее уведомление Windows (toast). Без сторонних
    pip-пакетов: если установлен plyer — используем его (надёжнее), иначе дёргаем
    Windows Toast API напрямую через PowerShell. На не-Windows или при любой ошибке
    просто ничего не делает — уведомление не критично, поэтому никогда не бросает
    исключение наружу и не должно ронять основной поток скрипта."""
    try:
        try:
            from plyer import notification as _plyer_notification
            _plyer_notification.notify(title=title, message=message, timeout=10)
            return
        except Exception:
            pass
        if os.name != 'nt':
            return
        safe_title = str(title).replace('"', "'").replace('`', "'")
        safe_msg = str(message).replace('"', "'").replace('`', "'")
        ps_script = (
            '[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, '
            'ContentType = WindowsRuntime] > $null; '
            '[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, '
            'ContentType = WindowsRuntime] > $null; '
            '$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent('
            '[Windows.UI.Notifications.ToastTemplateType]::ToastText02); '
            '$texts = $template.GetElementsByTagName("text"); '
            f'$texts.Item(0).AppendChild($template.CreateTextNode("{safe_title}")) > $null; '
            f'$texts.Item(1).AppendChild($template.CreateTextNode("{safe_msg}")) > $null; '
            '$toast = [Windows.UI.Notifications.ToastNotification]::new($template); '
            '[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('
            '"RuLate Bot").Show($toast)'
        )
        creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        subprocess.Popen(
            ['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps_script],
            creationflags=creationflags
        )
    except Exception:
        pass


def _parse_rulate_balance(html_text):
    """Достаёт из HTML-страницы RuLate текущий баланс и доход за сегодня.
    Возвращает (balance, today_income) — любое из значений может быть None,
    если соответствующий блок не нашёлся (сайт изменил вёрстку и т.п.)."""
    balance = None
    today_income = None
    try:
        m = re.search(r'class="income-value"[^>]*>\s*([+\-]?[\d.,]+)\s*<', html_text)
        if m:
            today_income = float(m.group(1).replace(',', '.').replace('+', ''))
    except Exception:
        pass
    try:
        m_block = re.search(
            r'<div class="main-header-balance">(.*?)<div class="main-header-balance income-counter-container"',
            html_text, re.S)
        if m_block:
            m_num = re.search(r'([\d]+[.,]\d+)', m_block.group(1))
            if m_num:
                balance = float(m_num.group(1).replace(',', '.'))
    except Exception:
        pass
    return balance, today_income


def _balance_watch_loop(app, p_name, rulate_url):
    """Фоновый цикл: раз в BALANCE_POLL_INTERVAL_SEC секунд запрашивает страницу
    RuLate напрямую (requests, куки из последнего снимка) и сравнивает баланс/доход
    с последним известным значением (хранится в BALANCE_STATE_FILE, переживает
    перезапуск скрипта). При изменении — пишет в лог и показывает Windows-уведомление
    (только если включена галочка 'Уведомления о балансе' в настройках)."""
    state = load_json(BALANCE_STATE_FILE, {})
    last = state.get(p_name, {})
    last_balance = last.get('balance')
    last_income = last.get('income')

    while True:
        with RULATE_COOKIE_LOCK:
            cookies = list(RULATE_COOKIE_SNAPSHOTS.get(p_name) or [])
        if not cookies:
            time.sleep(BALANCE_POLL_INTERVAL_SEC)
            continue
        try:
            sess = requests.Session()
            for c in cookies:
                try:
                    sess.cookies.set(c['name'], c['value'], domain='tl.rulate.ru')
                except Exception:
                    pass
            r = sess.get(rulate_url, timeout=15)
            if r.status_code == 200:
                balance, income = _parse_rulate_balance(r.text)
                changed = False
                parts = []
                if balance is not None and balance != last_balance:
                    if last_balance is not None:
                        diff = balance - last_balance
                        parts.append(f'Баланс: {last_balance:.2f} → {balance:.2f} ({"+" if diff >= 0 else ""}{diff:.2f})')
                    else:
                        parts.append(f'Баланс: {balance:.2f}')
                    last_balance = balance
                    changed = True
                if income is not None and income != last_income:
                    parts.append(f'Доход за сегодня: +{income:.2f}')
                    last_income = income
                    changed = True
                if changed:
                    msg = ' | '.join(parts)
                    app.log(f'[{p_name}] 💰 Баланс RuLate обновился: {msg}')
                    if getattr(app, 'balance_notify_var', None) and app.balance_notify_var.get():
                        show_windows_notification(f'RuLate — {p_name}', msg)
                    state[p_name] = {'balance': last_balance, 'income': last_income}
                    save_json(BALANCE_STATE_FILE, state)
        except Exception:
            pass  # сеть/сайт моргнули — тихо пробуем на следующем цикле
        time.sleep(BALANCE_POLL_INTERVAL_SEC)


def _register_active_profile(p_name):
    with ACTIVE_PROFILES_LOCK:
        ACTIVE_PROFILES.add(p_name)


def _unregister_active_profile(p_name):
    with ACTIVE_PROFILES_LOCK:
        ACTIVE_PROFILES.discard(p_name)


def clean_chrome_profile_lock(p_name):
    """Удаляет служебные файлы-блокировки Chrome-профиля (SingletonLock/Socket/Cookie),
    а также "хвосты" недописанных операций SQLite (*-journal, *-wal, *-shm, *.tmp).
    Если предыдущий процесс Chrome для этого профиля не успел до конца завершиться
    (например, при переходе скрипта к следующей книге, крэше вкладки или force-kill
    посреди записи Cookies/Preferences) — новый Chrome с тем же --user-data-dir видит
    "живую" блокировку или недописанный journal-файл базы и либо молча открывается и
    тут же закрывается, либо начинает вести себя нестабильно. Чистим всё это перед
    каждым запуском."""
    profile_dir = os.path.abspath("chrome_profiles/" + p_name)
    # DevToolsActivePort — ещё один частый виновник "открылся и тут же закрылся":
    # если он остался от предыдущего запуска, новый Chrome видит "живой" отладочный
    # порт и отказывается стартовать нормально.
    for lock_name in ('SingletonLock', 'SingletonSocket', 'SingletonCookie', 'DevToolsActivePort'):
        lock_path = os.path.join(profile_dir, lock_name)
        try:
            if os.path.exists(lock_path) or os.path.islink(lock_path):
                os.remove(lock_path)
        except Exception:
            pass
    # Недописанные SQLite-журналы/временные файлы (Cookies-journal, Preferences-journal,
    # Web Data-journal, *-wal, *.tmp и т.п.) остаются, если Chrome был убит (taskkill)
    # посреди операции записи. Провоцируют повреждение базы и нестабильное поведение
    # вкладки при следующем старте. Ищем их рекурсивно по всей папке профиля и удаляем.
    try:
        for root, _dirs, files in os.walk(profile_dir):
            for fname in files:
                low = fname.lower()
                if low.endswith('-journal') or low.endswith('-wal') or low.endswith('-shm') or low.endswith('.tmp'):
                    try:
                        os.remove(os.path.join(root, fname))
                    except Exception:
                        pass
    except Exception:
        pass


def _chrome_processes_alive():
    """Быстрая проверка через tasklist — остались ли живые chrome.exe."""
    try:
        result = subprocess.run(
            'tasklist /FI "IMAGENAME eq chrome.exe"', shell=True,
            capture_output=True, text=True, timeout=5
        )
        return 'chrome.exe' in (result.stdout or '')
    except Exception:
        # Не смогли проверить (не Windows / ошибка) — считаем что чисто,
        # чтобы не зависнуть навсегда.
        return False


def kill_chrome_processes(wait_sec=2, verify_timeout=10, exclude_profiles=None):
    """Завершает процессы chrome.exe и ЖДЁТ, пока ОС реально освободит файловые
    блокировки профиля, вместо фиксированной паузы.

    ВАЖНО: раньше это был безусловный 'taskkill /F /IM chrome.exe' — убивавший
    ВСЕ окна Chrome в системе, включая браузер другого, ещё активного потока
    (например "осиротевшего" потока после handoff при смене аккаунта, который
    sequential_manager не отслеживал). Теперь убиваем точечно: смотрим командную
    строку каждого chrome.exe (в ней всегда виден --user-data-dir=...\\chrome_profiles\\<профиль>)
    и НЕ трогаем процессы тех профилей, что сейчас зарегистрированы как активные
    (ACTIVE_PROFILES) или явно переданы в exclude_profiles."""
    with ACTIVE_PROFILES_LOCK:
        protected = set(ACTIVE_PROFILES)
    if exclude_profiles:
        protected.update(exclude_profiles)

    procs = None
    try:
        ps_cmd = (
            'powershell -NoProfile -Command '
            '"Get-CimInstance Win32_Process -Filter \\"Name=\'chrome.exe\'\\" '
            '| Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"'
        )
        result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, timeout=10)
        raw = (result.stdout or '').strip()
        if raw:
            parsed = json.loads(raw)
            procs = [parsed] if isinstance(parsed, dict) else parsed
        else:
            procs = []
    except Exception:
        procs = None

    if procs is not None:
        for proc in procs:
            pid = proc.get('ProcessId')
            cmdline = (proc.get('CommandLine') or '').lower()
            if not pid:
                continue
            is_protected = any(
                ('chrome_profiles\\' + prof).lower() in cmdline or
                ('chrome_profiles/' + prof).lower() in cmdline
                for prof in protected
            )
            if is_protected:
                continue
            try:
                subprocess.call(f'taskkill /F /PID {pid} /T', shell=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
    elif not protected:
        # PowerShell недоступен и защищать некого — ведём себя как раньше.
        try:
            subprocess.call('taskkill /F /IM chrome.exe /T', shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    # Если PowerShell недоступен, а защищённые профили ЕСТЬ — сознательно
    # ничего не убиваем глобально, чтобы не рисковать чужим браузером.

    time.sleep(max(wait_sec, 1))
    deadline = time.time() + verify_timeout
    while time.time() < deadline:
        if not _chrome_processes_alive():
            break
        time.sleep(0.5)
    # Небольшой запас, чтобы ОС успела снять файловые блокировки после смерти процесса
    time.sleep(1)


def get_driver_path():
    global CHROMEDRIVER_PATH
    with DRIVER_INSTALL_LOCK:
        if CHROMEDRIVER_PATH is not None:
            return CHROMEDRIVER_PATH
        # Пробуем selenium-manager (Selenium 4.6+) — без webdriver_manager
        try:
            from selenium.webdriver.chrome.service import Service as _Svc
            from selenium import __version__ as _sv
            major = int(_sv.split('.')[0])
            if major >= 4:
                # selenium-manager сам найдёт нужный chromedriver
                import subprocess, sys
                sm_path = os.path.join(os.path.dirname(sys.executable), 'selenium', 'webdriver', 'common', 'windows', 'selenium-manager.exe')
                if not os.path.exists(sm_path):
                    # Попробуем найти через пакет
                    import selenium
                    base = os.path.dirname(selenium.__file__)
                    for root, dirs, files in os.walk(base):
                        for f in files:
                            if f == 'selenium-manager.exe':
                                sm_path = os.path.join(root, f)
                                break
                if os.path.exists(sm_path):
                    result = subprocess.run([sm_path, '--browser', 'chrome', '--output', 'json'],
                                          capture_output=True, text=True, timeout=30)
                    import json as _json
                    data = _json.loads(result.stdout)
                    driver_path = data.get('result', {}).get('driver_path') or data.get('driver_path', '')
                    if driver_path and os.path.exists(driver_path):
                        CHROMEDRIVER_PATH = driver_path
                        return CHROMEDRIVER_PATH
        except Exception as e:
            print(f'selenium-manager failed: {e}')

        # Fallback — скачиваем chromedriver напрямую с Chrome for Testing
        try:
            import urllib.request, zipfile, shutil
            # Получаем версию установленного Chrome
            import subprocess, winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Google\Chrome\BLBeacon')
                chrome_ver = winreg.QueryValueEx(key, 'version')[0]
            except:
                try:
                    result = subprocess.run(
                        [r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--version'],
                        capture_output=True, text=True, timeout=10)
                    chrome_ver = result.stdout.strip().split()[-1]
                except:
                    chrome_ver = '146.0.7680.165'

            major = chrome_ver.split('.')[0]
            print(f'Detected Chrome version: {chrome_ver} (major: {major})')

            # Chrome for Testing JSON endpoint
            json_url = f'https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json'
            cache_dir = os.path.expanduser('~\\.chromedriver_cache')
            driver_exe = os.path.join(cache_dir, f'chromedriver_{major}.exe')

            if os.path.exists(driver_exe):
                CHROMEDRIVER_PATH = driver_exe
                print(f'Using cached chromedriver: {driver_exe}')
                return CHROMEDRIVER_PATH

            os.makedirs(cache_dir, exist_ok=True)
            print('Downloading chromedriver list...')
            with urllib.request.urlopen(json_url, timeout=30) as r:
                import json as _json
                data = _json.loads(r.read())

            # Ищем подходящую версию (совпадение по major)
            best = None
            for entry in reversed(data.get('versions', [])):
                if entry['version'].startswith(major + '.'):
                    downloads = entry.get('downloads', {}).get('chromedriver', [])
                    for d in downloads:
                        if d['platform'] == 'win64':
                            best = d['url']
                            break
                    if best:
                        break

            if not best:
                raise RuntimeError(f'No chromedriver found for Chrome {major}')

            print(f'Downloading chromedriver from: {best}')
            zip_path = os.path.join(cache_dir, 'chromedriver.zip')
            urllib.request.urlretrieve(best, zip_path)

            with zipfile.ZipFile(zip_path, 'r') as z:
                for name in z.namelist():
                    if name.endswith('chromedriver.exe'):
                        with z.open(name) as src, open(driver_exe, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        break
            os.remove(zip_path)
            os.chmod(driver_exe, 0o755)
            print(f'Chromedriver saved to: {driver_exe}')
            CHROMEDRIVER_PATH = driver_exe
        except Exception as e:
            print(f'Direct download failed: {e}')
            # Последний резерв — попробовать без Service (selenium-manager сам справится)
            CHROMEDRIVER_PATH = '__AUTO__'
        return CHROMEDRIVER_PATH

def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving JSON: {e}")

# ==================== ЛОКАЛЬНОЕ ХРАНИЛИЩЕ ПЕРЕВЕДЁННЫХ ГЛАВ (для Редактора) ====================
# Скрипт сам, без каких-либо окон, сохраняет каждую переведённую (DeepSeek) главу локально на
# диск в JSON, чтобы вкладка "Редактор" могла показывать/редактировать/откатывать/публиковать их.
TRANSLATIONS_DIR = 'translations'
CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')  # диапазоны китайских иероглифов

def _book_id_from_rulate(rulate_url):
    """Стабильный идентификатор книги для имени папки — берём числовой ID из URL RuLate."""
    m = re.search(r'/book/(\d+)', rulate_url or '')
    if m:
        return m.group(1)
    safe = re.sub(r'[^a-zA-Z0-9]+', '_', (rulate_url or 'book')).strip('_')
    return safe[:60] or 'unknown_book'

def _book_dir(book_id):
    d = os.path.join(TRANSLATIONS_DIR, book_id)
    os.makedirs(os.path.join(d, 'chapters'), exist_ok=True)
    return d

def _chapter_path(book_id, chapter_num):
    return os.path.join(TRANSLATIONS_DIR, book_id, 'chapters', f'{int(chapter_num):06d}.json')

def save_chapter_local(rulate_url, tomato_url, chapter_num, title, text, is_paid, is_delayed, posted, book_title=None, cover_url=None):
    """Сохраняет (или обновляет) главу локально. Если глава уже существовала — original_text
    (для кнопки "Откатить") НЕ перезаписывается, чтобы сохранить исходный текст перевода."""
    book_id = _book_id_from_rulate(rulate_url)
    book_dir = _book_dir(book_id)
    meta_path = os.path.join(book_dir, 'meta.json')
    meta = load_json(meta_path, {})
    meta['rulate_url'] = rulate_url
    meta['tomato_url'] = tomato_url
    if book_title:
        meta['title'] = book_title
    elif not meta.get('title'):
        meta['title'] = rulate_url or book_id
    if cover_url:
        meta['cover_url'] = cover_url
    save_json(meta_path, meta)

    ch_path = _chapter_path(book_id, chapter_num)
    existing = load_json(ch_path, None)
    original_text = existing.get('original_text') if existing else None
    if original_text is None:
        original_text = text
    ch_data = {
        'num': int(chapter_num),
        'title': title or '',
        'text': text or '',
        'original_text': original_text,
        'is_paid': bool(is_paid),
        'is_delayed': bool(is_delayed),
        'posted': bool(posted),
        'updated_at': datetime.now().isoformat(timespec='seconds'),
    }
    save_json(ch_path, ch_data)
    return book_id

def list_translated_books():
    if not os.path.isdir(TRANSLATIONS_DIR):
        return []
    result = []
    for book_id in sorted(os.listdir(TRANSLATIONS_DIR)):
        book_dir = os.path.join(TRANSLATIONS_DIR, book_id)
        if not os.path.isdir(book_dir):
            continue
        ch_dir = os.path.join(book_dir, 'chapters')
        count = len([f for f in os.listdir(ch_dir) if f.endswith('.json')]) if os.path.isdir(ch_dir) else 0
        if count == 0:
            continue
        meta = load_json(os.path.join(book_dir, 'meta.json'), {})
        result.append({
            'id': book_id,
            'title': meta.get('title', book_id),
            'count': count,
            'rulate_url': meta.get('rulate_url', ''),
            'tomato_url': meta.get('tomato_url', ''),
            'cover_url': meta.get('cover_url', ''),
        })
    return result

def list_book_chapters(book_id):
    ch_dir = os.path.join(TRANSLATIONS_DIR, book_id, 'chapters')
    if not os.path.isdir(ch_dir):
        return []
    chapters = []
    for fname in sorted(os.listdir(ch_dir)):
        if not fname.endswith('.json'):
            continue
        data = load_json(os.path.join(ch_dir, fname), None)
        if data:
            chapters.append(data)
    chapters.sort(key=lambda c: c.get('num', 0))
    return chapters

def load_book_chapter(book_id, chapter_num):
    return load_json(_chapter_path(book_id, chapter_num), None)

def save_book_chapter(book_id, chapter_num, data):
    save_json(_chapter_path(book_id, chapter_num), data)

def validate_ai_format(ai_text):
    if not ai_text:
        return (False, 'Пустой ответ')
    # Убираем markdown-обёртку (```...``` или `...`)
    cleaned = re.sub(r'```[^\n]*\n?', '', ai_text).strip()
    # Убираем вводный мусор до первого тега [
    first_bracket = cleaned.find('[')
    if first_bracket > 0:
        cleaned = cleaned[first_bracket:]
    # Нормализуем теги: пробелы внутри скобок, верхний регистр
    normalized = re.sub(
        r'\[\s*(?P<tag>/?\s*[A-Za-z]+)\s*\]',
        lambda m: '[' + re.sub(r'\s+', '', m.group('tag')).upper() + ']',
        cleaned
    )
    required_open  = ['[G]', '[T]', '[B]']
    required_close = ['[/G]', '[/T]', '[/B]']
    missing = [tag for tag in required_open if tag not in normalized]
    if missing:
        return (False, f"Отсутствуют теги: {', '.join(missing)}")
    missing_close = [tag for tag in required_close if tag not in normalized]
    if missing_close:
        return (False, f"Незакрытые теги: {', '.join(missing_close)}")
    # Проверяем что [B]...[/B] содержит хоть что-то
    body = extract_body(normalized)
    if not body or len(body) < 30:
        return (False, 'Тег [B] пуст или слишком короткий')
    # ОБЯЗАТЕЛЬНО: глоссарий [G] должен содержать хотя бы один новый термин.
    # Пустой глоссарий или отписки вида "новых терминов нет" — не принимаются.
    glossary = extract_glossary(normalized).strip()
    if not glossary or len(glossary) < 5:
        return (False, 'Тег [G] пуст — нужен минимум один новый термин')
    no_terms_phrases = [
        'нет новых терминов', 'новых терминов нет', 'термины отсутствуют',
        'нет терминов', 'без новых терминов', 'no new terms', 'none',
        'отсутствуют', 'н/а', 'n/a',
    ]
    if any(p in glossary.lower() for p in no_terms_phrases) and len(glossary) < 40:
        return (False, 'Тег [G] не содержит ни одного нового термина')
    return (True, 'OK')

def extract_body(ai_text):
    pattern = r'\[B\](.*?)(\[/B\]|$)'
    match = re.search(pattern, ai_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ai_text

def extract_glossary(ai_text):
    pattern = r'\[G\](.*?)\[/G\]'
    match = re.search(pattern, ai_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

PROMPT_HEADER_PROTECT_CHARS = 8000   # первые N символов промт-файла ЗАЩИЩЕНЫ и никогда не обрезаются —
                                      # это статичная инструкция для DeepSeek, а не накопленный глоссарий
PROMPT_FILE_MAX_CHARS = 150000       # общий предел размера промт-файла. Ни один чат (включая DeepSeek)
                                      # не может принять текст крупнее этого как обычное сообщение —
                                      # сверх лимита физически невозможно отправить текстом, только файлом.
                                      # Поэтому при превышении обрезаются САМЫЕ СТАРЫЕ (наименее актуальные
                                      # для текущих глав) строки накопленного глоссария.

_NO_TERMS_PHRASES = (
    'нет новых терминов', 'новых терминов нет', 'термины отсутствуют',
    'нет терминов', 'без новых терминов', 'no new terms', 'none',
    'отсутствуют', 'н/а', 'n/a',
)

def append_new_glossary_terms(path, new_glossary_text):
    """Дописывает в файл промта (data['pr']) ТОЛЬКО реально новые строки
    глоссария, которых там ещё нет, и никогда не пишет туда бесполезные
    отписки вида "новых терминов нет".

    Раньше сюда слепо дописывался ВЕСЬ блок [G]...[/G] из каждого ответа
    DeepSeek без всякой проверки — после каждой главы (и после каждой
    повторной попытки при исправлении иероглифов/абзацев). За сотни и тысячи
    глав промт-файл распухал до нескольких мегабайт, набитый тысячами
    повторов одних и тех же терминов и пустых "новых терминов нет". Именно
    из-за этого промт физически невозможно было отправить как текст —
    любой чат (включая DeepSeek) при вставке текста такого размера
    автоматически прикрепляет его как файл, это никак не связано со
    способом вставки (буфер обмена / JS)."""
    if not new_glossary_text or not path or not os.path.exists(path):
        return
    with GLOSSARY_WRITE_LOCK:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                existing = f.read()
        except Exception:
            existing = ''
        existing_lines = {ln.strip().lower() for ln in existing.split('\n') if ln.strip()}

        new_lines = []
        for ln in new_glossary_text.split('\n'):
            ln = ln.strip()
            if not ln:
                continue
            low = ln.lower()
            # Пустые отписки ("новых терминов нет" и т.п.) никогда не пишем
            if len(ln) < 60 and any(p in low for p in _NO_TERMS_PHRASES):
                continue
            if low in existing_lines:
                continue
            new_lines.append(ln)
            existing_lines.add(low)

        if new_lines:
            with open(path, 'a', encoding='utf-8') as f:
                f.write('\n' + '\n'.join(new_lines))
        _enforce_prompt_size_cap(path)

def _enforce_prompt_size_cap(path):
    """Если промт-файл превысил PROMPT_FILE_MAX_CHARS — обрезает САМЫЕ СТАРЫЕ
    строки накопленного глоссария (но никогда не трогает защищённый заголовок
    длиной PROMPT_HEADER_PROTECT_CHARS — это статичная инструкция), чтобы
    промт всегда можно было отправить как обычный текст, а не файл, и чтобы
    он всегда помещался в контекст модели. Должна вызываться из-под
    GLOSSARY_WRITE_LOCK (см. append_new_glossary_terms)."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return
    if len(content) <= PROMPT_FILE_MAX_CHARS:
        return
    header = content[:PROMPT_HEADER_PROTECT_CHARS]
    tail = content[PROMPT_HEADER_PROTECT_CHARS:]
    keep_tail_chars = max(0, PROMPT_FILE_MAX_CHARS - len(header))
    tail_lines = tail.split('\n')
    kept = []
    total = 0
    for ln in reversed(tail_lines):
        total += len(ln) + 1
        if total > keep_tail_chars:
            break
        kept.append(ln)
    kept.reverse()
    new_content = header + '\n'.join(kept)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception:
        pass

def extract_title(ai_text):
    """Извлекает название главы из тега [T]...[/T]"""
    pattern = r'\[T\](.*?)\[/T\]'
    match = re.search(pattern, ai_text, re.DOTALL | re.IGNORECASE)
    if match:
        # Убираем переносы строк внутри названия
        title = match.group(1).strip()
        title = re.sub(r'[\r\n]+', ' ', title).strip()
        return title
    return ""

def has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def extract_cjk_fragments(text, context=15, max_fragments=15):
    """Находит все места в тексте с китайскими иероглифами и возвращает список
    коротких фрагментов текста вокруг них (с небольшим контекстом по обе стороны),
    чтобы точечно показать DeepSeek, что именно осталось непереведённым.
    Соседние иероглифы (в пределах одной фразы/имени) объединяются в один
    фрагмент, а не дробятся на кучу дублирующихся мелких кусков."""
    if not text:
        return []
    runs = []
    for m in CJK_PATTERN.finditer(text):
        if runs and m.start() <= runs[-1][1] + 3:
            runs[-1] = (runs[-1][0], m.end())
        else:
            runs.append((m.start(), m.end()))
    fragments = []
    seen = set()
    for s, e in runs:
        frag_start = max(0, s - context)
        frag_end = min(len(text), e + context)
        frag = re.sub(r'\s+', ' ', text[frag_start:frag_end]).strip()
        if frag and frag not in seen:
            seen.add(frag)
            fragments.append(frag)
        if len(fragments) >= max_fragments:
            break
    return fragments

def build_cjk_retry_msg(fragments):
    """Формирует сообщение для DeepSeek с указанием конкретных фрагментов,
    где остались непереведённые китайские иероглифы, и просьбой переписать
    главу целиком без них."""
    quoted = '\n'.join(f'{i + 1}. "{f}"' for i, f in enumerate(fragments))
    return (
        'В присланном тобой переводе внутри тега [B]...[/B] остались НЕПЕРЕВЕДЁННЫЕ '
        'китайские иероглифы. Вот фрагменты текста, где они встречаются:\n\n'
        f'{quoted}\n\n'
        'Перепиши ВСЮ главу заново целиком, полностью убрав все китайские иероглифы — '
        'переведи их на русский по смыслу, используя контекст главы и уже известный глоссарий. '
        'Никаких китайских символов быть не должно вообще нигде в тексте.\n'
        'Обязательно используй теги [G]...[/G], [T]...[/T], [B]...[/B], как и раньше.'
    )

# Граница между предложениями: точка/!/?/многоточие, за которой (после
# необязательных закрывающих кавычек/скобок) идёт пробел и заглавная буква,
# кавычка или открывающая скобка — то есть явно начинается новое предложение.
_PARAGRAPH_SENTENCE_BOUNDARY_RE = re.compile(r'[.!?…]+[»"\')]*\s+(?=[А-ЯЁA-Z«"\'\(])')


def split_paragraph_into_sentences(paragraph):
    """Разбивает абзац на список предложений (строк). Использует границы между
    предложениями (см. _PARAGRAPH_SENTENCE_BOUNDARY_RE), но не считает точку
    границей, если перед ней стоит цифра (десятичная дробь вида "3.5") или
    один-два символа без пробела перед точкой (инициалы вида "А.С. Пушкин",
    сокращения вида "т.е.", "см.", "стр.") — такие случаи не являются реальным
    концом предложения."""
    text = paragraph.strip()
    if not text:
        return []
    sentences = []
    last_end = 0
    for m in _PARAGRAPH_SENTENCE_BOUNDARY_RE.finditer(text):
        start = m.start()
        left = text[:start]
        # десятичная дробь: "3.5" — перед точкой цифра
        if left and left[-1].isdigit():
            continue
        # инициалы/частые сокращения: 1-2 буквы (без пробела) сразу перед точкой,
        # например "А.С.", "т.е.", "см.", "др.", "им."
        prev_word_m = re.search(r'([^\s.]{1,3})$', left)
        if prev_word_m and len(prev_word_m.group(1)) <= 3 and prev_word_m.group(1).islower():
            common_abbr = {'т.е', 'т.д', 'т.п', 'см', 'др', 'им', 'стр', 'гл', 'рис', 'г', 'мин'}
            if prev_word_m.group(1) in common_abbr:
                continue
        sentence = text[last_end:m.end()].strip()
        if sentence:
            sentences.append(sentence)
        last_end = m.end()
    tail = text[last_end:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def count_sentences_in_paragraph(paragraph):
    """Считает, сколько предложений в абзаце (см. split_paragraph_into_sentences)."""
    return len(split_paragraph_into_sentences(paragraph))


def find_layout_issues(body_text, max_items=8):
    """Проверяет текст главы по символам и ищет две категории проблем:
      1) абзацы, где предложений больше SENTENCES_PER_PARAGRAPH_LIMIT (по
         умолчанию — больше 2);
      2) абзацы, чья длина в символах превышает фиксированный лимит
         PARAGRAPH_MAX_LENGTH.
    Возвращает (bad_paragraphs, long_paragraphs, max_len):
      - bad_paragraphs: список (номер_абзаца, текст_абзаца) с избытком предложений
      - long_paragraphs: список (номер_абзаца, текст_абзаца) длиннее лимита символов
      - max_len: фиксированный лимит символов в абзаце (PARAGRAPH_MAX_LENGTH) """
    if not body_text:
        return [], [], 0
    paragraphs = [p.strip() for p in body_text.split('\n') if p.strip()]
    max_len = PARAGRAPH_MAX_LENGTH

    bad_paragraphs = []
    long_paragraphs = []
    for i, p in enumerate(paragraphs, 1):
        sentences = split_paragraph_into_sentences(p)
        if len(sentences) > SENTENCES_PER_PARAGRAPH_LIMIT and len(bad_paragraphs) < max_items:
            bad_paragraphs.append((i, p))
        if len(p) > max_len and len(long_paragraphs) < max_items:
            long_paragraphs.append((i, p))
        if len(bad_paragraphs) >= max_items and len(long_paragraphs) >= max_items:
            break
    return bad_paragraphs, long_paragraphs, max_len


def build_layout_retry_msg(bad_paragraphs, long_paragraphs, max_len):
    """Формирует сообщение для DeepSeek с указанием конкретных абзацев,
    которые нарушают правила оформления (лимит предложений в абзаце и лимит
    символов в абзаце), и просьбой переписать главу с исправлениями."""
    parts = []
    if bad_paragraphs:
        quoted = '\n'.join(f'{i}. "{p[:250]}"' for i, p in bad_paragraphs)
        parts.append(
            f'В некоторых абзацах слишком много предложений — по правилам оформления в '
            f'КАЖДОМ абзаце должно быть НЕ БОЛЬШЕ {SENTENCES_PER_PARAGRAPH_LIMIT} предложений. '
            f'Вот абзацы, где это нарушено:\n\n{quoted}'
        )
    if long_paragraphs:
        quoted2 = '\n'.join(f'{i}. "{p[:250]}"' for i, p in long_paragraphs)
        parts.append(
            f'Также некоторые абзацы слишком длинные (длиннее {int(max_len)} символов). Разбей их на '
            f'несколько более коротких абзацев (или сократи формулировки), не теряя смысл. Вот эти '
            f'абзацы:\n\n{quoted2}'
        )
    body = '\n\n'.join(parts)
    return (
        'В присланном тобой переводе внутри тега [B]...[/B] найдены проблемы с оформлением текста.\n\n'
        f'{body}\n\n'
        f'Перепиши ВСЮ главу заново целиком, ничего не меняя по смыслу и не сокращая текст, но '
        f'исправь эти места: в каждом абзаце должно быть не больше {SENTENCES_PER_PARAGRAPH_LIMIT} '
        f'предложений, а сам абзац не должен быть длиннее {int(max_len)} символов (абзацы разделяй '
        'пустой строкой, как и раньше).\n'
        'Обязательно используй теги [G]...[/G], [T]...[/T], [B]...[/B], как и раньше.'
    )


def count_lines_in_text(text):
    """Подсчитывает количество строк в тексте (по символу \\n)."""
    if not text:
        return 0
    return len([l for l in text.split('\n') if l.strip()])


def build_lines_retry_msg(current_lines, min_lines):
    """Формирует сообщение для DeepSeek с просьбой расширить главу до min_lines строк."""
    return (
        f'В присланном тобой переводе внутри тега [B]...[/B] всего {current_lines} строк(и), '
        f'а нужно минимум {min_lines}. Текст слишком короткий.\n\n'
        'Перепиши ВСЮ главу заново, значительно РАСШИРЬ её — добавь больше деталей, '
        'описаний, диалогов, внутренних монологов, пояснений. Сделай так, чтобы '
        f'в тексте было НЕ МЕНЕЕ {min_lines} строк (абзацев). Сохрани смысл и стиль оригинала.\n'
        'Обязательно используй теги [G]...[/G], [T]...[/T], [B]...[/B], как и раньше.'
    )


def get_msk_today():
    """Возвращает сегодняшнюю дату по МСК (UTC+3) в формате YYYY-MM-DD."""
    import datetime
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    msk_now = utc_now + datetime.timedelta(hours=3)
    return msk_now.strftime('%Y-%m-%d')

def get_msk_now():
    """Возвращает текущее время по МСК."""
    import datetime
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)

def get_freeze_until_str():
    """Возвращает дату разморозки: следующий день до 12:00 МСК."""
    import datetime
    msk_now = get_msk_now()
    next_day = msk_now.date() + datetime.timedelta(days=1)
    return str(next_day) + ' 12:00'

def load_account_stats():
    return load_json(ACCOUNT_STATS_FILE, {})

def save_account_stats(stats):
    save_json(ACCOUNT_STATS_FILE, stats)

def get_account_stat(profile_name):
    """Возвращает словарь статистики аккаунта за сегодня."""
    stats = load_account_stats()
    today = get_msk_today()
    key = f'{profile_name}:{today}'
    return stats.get(key, {'chapters': 0, 'frozen': False, 'freeze_until': ''})

def add_chapter_to_account(profile_name):
    """Увеличивает счётчик глав аккаунта. Если ≥CHAPTERS_FREEZE_LIMIT — замораживает до 12:00 МСК след. дня."""
    stats = load_account_stats()
    today = get_msk_today()
    key = f'{profile_name}:{today}'
    if key not in stats:
        stats[key] = {'chapters': 0, 'frozen': False, 'freeze_until': ''}
    stats[key]['chapters'] += 1
    if stats[key]['chapters'] >= CHAPTERS_FREEZE_LIMIT and not stats[key]['frozen']:
        stats[key]['frozen'] = True
        stats[key]['freeze_until'] = get_freeze_until_str()
    save_account_stats(stats)
    return stats[key]

def is_account_frozen(profile_name):
    """Проверяет, заморожен ли аккаунт прямо сейчас (с учётом автоотмороженности в 12:00)."""
    import datetime
    stat = get_account_stat(profile_name)
    if not stat.get('frozen'):
        return False
    freeze_until_str = stat.get('freeze_until', '')
    if not freeze_until_str:
        return False
    try:
        freeze_dt = datetime.datetime.strptime(freeze_until_str, '%Y-%m-%d %H:%M')
        if get_msk_now() >= freeze_dt:
            # Время разморозки прошло — снимаем заморозку
            stats = load_account_stats()
            today = get_msk_today()
            key = f'{profile_name}:{today}'
            if key in stats:
                stats[key]['frozen'] = False
            save_account_stats(stats)
            return False
    except:
        pass
    return True

def freeze_account_manually(profile_name):
    stats = load_account_stats()
    today = get_msk_today()
    key = f'{profile_name}:{today}'
    if key not in stats:
        stats[key] = {'chapters': 0, 'frozen': False, 'freeze_until': ''}
    stats[key]['frozen'] = True
    stats[key]['freeze_until'] = get_freeze_until_str()
    save_account_stats(stats)

def unfreeze_account(profile_name):
    """Снимает заморозку с аккаунта и одновременно сбрасывает его счётчик
    переведённых за сегодня глав в 0 (по требованию — ручная разморозка должна
    давать аккаунту "чистый" лимит глав на оставшуюся часть суток)."""
    stats = load_account_stats()
    today = get_msk_today()
    key = f'{profile_name}:{today}'
    if key in stats:
        stats[key]['frozen'] = False
        stats[key]['freeze_until'] = ''
        stats[key]['chapters'] = 0
    save_account_stats(stats)

# ==================== МЕНЕДЖЕР ПРОФИЛЕЙ ====================

class ProfileManager(ctk.CTkFrame):
    """Встраиваемая панель профилей/аккаунтов — живёт прямо во вкладке приложения,
    а не в отдельном всплывающем окне."""
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS['bg'], corner_radius=0)
        self.app = app
        self.parent = app  # обратная совместимость с методами ниже
        self.pack(fill='both', expand=True)

        # Вкладки: Профили | Аккаунты
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=COLORS['card'],
            segmented_button_fg_color=COLORS['sidebar'],
            segmented_button_selected_color=COLORS['accent_green'],
            segmented_button_selected_hover_color=COLORS['hover_green'],
            segmented_button_unselected_color=COLORS['sidebar'],
            segmented_button_unselected_hover_color=COLORS['card_border'],
            text_color=COLORS['text_main'],
            corner_radius=10,
        )
        self.tabs.pack(fill='both', expand=True, padx=16, pady=16)

        self._build_profiles_tab(self.tabs.add('👤  Профили'))
        self._build_accounts_tab(self.tabs.add('📊  Аккаунты'))

    # ─── ВКЛАДКА ПРОФИЛИ ──────────────────────────────────────
    def _build_profiles_tab(self, tab):
        ctk.CTkLabel(tab, text='ПРОФИЛИ CHROME', font=('Impact', 22),
                     text_color=COLORS['accent_green']).pack(pady=(12, 2))
        ctk.CTkLabel(tab, text=f'Нажмите кнопку сайта чтобы войти в нужный аккаунт. После {CHAPTERS_FREEZE_LIMIT} глав аккаунт морозится до 12:00 МСК.',
                     font=('Segoe UI', 10), text_color=COLORS['text_dim']).pack(pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(tab, fg_color=COLORS['scrollable'], corner_radius=10)
        self.scroll.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        add_f = ctk.CTkFrame(tab, fg_color='transparent')
        add_f.pack(fill='x', padx=8, pady=(0, 8))
        self.entry = ctk.CTkEntry(add_f, placeholder_text='Имя нового профиля...', height=36, font=('Segoe UI', 12))
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        ctk.CTkButton(add_f, text='✚  СОЗДАТЬ', fg_color=COLORS['accent_green'],
                      hover_color=COLORS['hover_green'], text_color=COLORS['bg'],
                      width=130, height=36, font=('Segoe UI', 12, 'bold'), command=self.add_p).pack(side='right')
        self.refresh()

    def refresh(self):
        for child in self.scroll.winfo_children():
            child.destroy()
        profiles = load_json(PROFILES_FILE, ['Default'])
        for p in profiles:
            frozen = is_account_frozen(p)
            stat = get_account_stat(p)
            ch = stat.get('chapters', 0)
            freeze_until = stat.get('freeze_until', '')

            # Цвет карточки
            card_color = COLORS['entry_bg'] if not frozen else '#2a0a0a'
            border_color = COLORS['red'] if frozen else COLORS['card_border']

            card = ctk.CTkFrame(self.scroll, fg_color=card_color, corner_radius=10,
                                border_width=2, border_color=border_color)
            card.pack(fill='x', pady=5, padx=8)
            card.grid_columnconfigure(1, weight=1)

            # Иконка профиля
            icon_f = ctk.CTkFrame(card, width=44, height=44, fg_color=COLORS['card_border'], corner_radius=22)
            icon_f.grid(row=0, column=0, rowspan=3, padx=12, pady=10, sticky='ns')
            icon_f.grid_propagate(False)
            icon_text = '🔒' if frozen else '👤'
            ctk.CTkLabel(icon_f, text=icon_text, font=('Arial', 18)).place(relx=0.5, rely=0.5, anchor='center')

            # Имя + статус
            name_f = ctk.CTkFrame(card, fg_color='transparent')
            name_f.grid(row=0, column=1, sticky='w', padx=4, pady=(10, 0))
            ctk.CTkLabel(name_f, text=p, font=('Segoe UI', 13, 'bold'),
                         text_color=COLORS['red'] if frozen else COLORS['text_main']).pack(side='left')
            if frozen:
                ctk.CTkLabel(name_f, text=f'  🔒 Заморожен до {freeze_until}',
                             font=('Segoe UI', 10), text_color=COLORS['red']).pack(side='left', padx=6)
            else:
                ctk.CTkLabel(name_f, text=f'  📖 {ch}/{CHAPTERS_FREEZE_LIMIT} глав сегодня',
                             font=('Segoe UI', 10), text_color=COLORS['text_dim']).pack(side='left', padx=6)

            # Прогресс-бар глав
            prog_f = ctk.CTkFrame(card, fg_color='transparent')
            prog_f.grid(row=1, column=1, sticky='ew', padx=(4, 16), pady=(2, 2))
            pb = ctk.CTkProgressBar(prog_f, height=4, corner_radius=2,
                                    progress_color=COLORS['red'] if frozen else COLORS['accent_green'],
                                    fg_color=COLORS['card_border'])
            pb.pack(fill='x')
            pb.set(min(ch / CHAPTERS_FREEZE_LIMIT, 1.0))

            # Кнопки сайтов + разморозка
            btns_f = ctk.CTkFrame(card, fg_color='transparent')
            btns_f.grid(row=2, column=1, sticky='w', padx=4, pady=(0, 10))

            ctk.CTkButton(btns_f, text='🤖 Gemini', width=105, height=30,
                          fg_color='#1a6fa8', hover_color='#2080c0',
                          font=('Segoe UI', 11, 'bold'),
                          command=lambda n=p: self.quick_login(n, 'ai')).pack(side='left', padx=(0, 5))
            ctk.CTkButton(btns_f, text='🍅 Tomato', width=105, height=30,
                          fg_color='#a84a1a', hover_color='#c05020',
                          font=('Segoe UI', 11, 'bold'),
                          command=lambda n=p: self.quick_login(n, 'tom')).pack(side='left', padx=(0, 5))
            ctk.CTkButton(btns_f, text='📖 RuLate', width=105, height=30,
                          fg_color='#6a2a9b', hover_color='#7d35b5',
                          font=('Segoe UI', 11, 'bold'),
                          command=lambda n=p: self.quick_login(n, 'rul')).pack(side='left', padx=(0, 10))

            if frozen:
                ctk.CTkButton(btns_f, text='🔓 Разморозить', width=120, height=30,
                              fg_color=COLORS['accent_green'], hover_color=COLORS['hover_green'],
                              text_color=COLORS['bg'], font=('Segoe UI', 11, 'bold'),
                              command=lambda n=p: self._do_unfreeze(n)).pack(side='left')
            else:
                ctk.CTkButton(btns_f, text='❄ Заморозить', width=115, height=30,
                              fg_color='#2a2a4a', hover_color='#3a3a6a',
                              text_color=COLORS['text_dim'], font=('Segoe UI', 11),
                              command=lambda n=p: self._do_freeze(n)).pack(side='left')

            # Кнопка удаления
            ctk.CTkButton(card, text='✕', width=30, height=30,
                          fg_color='transparent', text_color=COLORS['text_dim'],
                          hover_color=COLORS['red'],
                          command=lambda n=p: self.delete_p(n)).grid(row=0, column=2, padx=10, pady=8, sticky='ne')

    def _do_freeze(self, name):
        freeze_account_manually(name)
        self.refresh()
        self._rebuild_accounts_tab()

    def _do_unfreeze(self, name):
        unfreeze_account(name)
        self.refresh()
        self._rebuild_accounts_tab()

    def add_p(self):
        name = self.entry.get().strip()
        if name:
            p = load_json(PROFILES_FILE, ['Default'])
            if name not in p:
                p.append(name)
                save_json(PROFILES_FILE, p)
                self.refresh()
                self.parent.update_menus()
                self.entry.delete(0, tk.END)

    def delete_p(self, name):
        if name == 'Default':
            return
        p = load_json(PROFILES_FILE, ['Default'])
        if name in p:
            p.remove(name)
            save_json(PROFILES_FILE, p)
            self.refresh()
            self.parent.update_menus()

    def quick_login(self, profile_name, site_type):
        urls = {'ai': 'https://chat.deepseek.com', 'tom': 'https://tomatomtl.com/', 'rul': 'https://tl.rulate.ru/login'}
        threading.Thread(target=self.open_browser, args=(profile_name, urls[site_type]), daemon=True).start()

    def open_browser(self, p_name, url):
        # Если профиль сейчас реально используется автоматическим переводом
        # (зарегистрирован в ACTIVE_PROFILES — см. worker()), Chrome для этого
        # --user-data-dir уже открыт другим процессом, и второй экземпляр с тем
        # же профилем принципиально не запустится (SingletonLock). Это не баг,
        # а ограничение самого Chrome — предупреждаем понятно, вместо общей
        # "Профиль занят" без объяснения причины.
        with ACTIVE_PROFILES_LOCK:
            is_running = p_name in ACTIVE_PROFILES
        if is_running:
            messagebox.showerror(
                'Профиль занят',
                f'Аккаунт "{p_name}" сейчас используется автоматическим переводом.\n'
                'Дождитесь окончания текущей задачи (или остановите её), '
                'прежде чем открывать этот профиль вручную.'
            )
            return
        try:
            # Профиль сейчас не активен — если "занят" всё же появляется, это
            # почти всегда СТАРЫЙ SingletonLock/DevToolsActivePort, оставшийся
            # от прошлого запуска (крэш, force-kill), а не реально работающий
            # Chrome. Чистим его перед открытием, как это уже делает
            # автоматический перевод при своём старте.
            clean_chrome_profile_lock(p_name)
            opts = self.parent.get_stealth_options(p_name)
            driver = self.parent._new_chrome_driver(opts)
            driver.get(url)
        except Exception as e:
            messagebox.showerror(
                'Ошибка',
                f'Не удалось открыть профиль "{p_name}".\n'
                f'Если Chrome для него уже открыт вручную (не через скрипт) — закройте его и попробуйте снова.\n\n{e}'
            )

    # ─── ВКЛАДКА АККАУНТЫ ─────────────────────────────────────
    def _build_accounts_tab(self, tab):
        self._accounts_tab_ref = tab
        top = ctk.CTkFrame(tab, fg_color='transparent')
        top.pack(fill='x', padx=10, pady=(12, 6))
        ctk.CTkLabel(top, text='СТАТИСТИКА АККАУНТОВ — СЕГОДНЯ', font=('Impact', 20),
                     text_color=COLORS['accent_green']).pack(side='left')
        ctk.CTkButton(top, text='🔄 Обновить', width=110, height=32,
                      fg_color=COLORS['accent_green'], hover_color=COLORS['hover_green'],
                      text_color=COLORS['bg'], font=('Segoe UI', 11, 'bold'),
                      command=self._rebuild_accounts_tab).pack(side='right')

        self._accounts_body = ctk.CTkScrollableFrame(tab, fg_color=COLORS['scrollable'], corner_radius=10)
        self._accounts_body.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        self._rebuild_accounts_tab()

    def _rebuild_accounts_tab(self):
        for child in self._accounts_body.winfo_children():
            child.destroy()
        profiles = load_json(PROFILES_FILE, ['Default'])
        today = get_msk_today()

        # Заголовок таблицы
        hdr = ctk.CTkFrame(self._accounts_body, fg_color=COLORS['card'], corner_radius=8)
        hdr.pack(fill='x', padx=4, pady=(4, 2))
        hdr.grid_columnconfigure(1, weight=1)
        for col, (txt, w) in enumerate([('Аккаунт', 0), ('Статус', 120), ('Глав сегодня', 110), ('Прогресс', 150), ('До разморозки', 160)]):
            ctk.CTkLabel(hdr, text=txt, font=('Segoe UI', 11, 'bold'),
                         text_color=COLORS['accent_green'], anchor='w',
                         width=w if w else 0).grid(row=0, column=col, padx=(12 if col==0 else 6), pady=8, sticky='w')

        used_today = []
        not_used_today = []
        for p in profiles:
            stat = get_account_stat(p)
            if stat.get('chapters', 0) > 0:
                used_today.append(p)
            else:
                not_used_today.append(p)

        def section_sep(label):
            f = ctk.CTkFrame(self._accounts_body, fg_color='transparent')
            f.pack(fill='x', padx=4, pady=(10, 2))
            ctk.CTkLabel(f, text=label, font=('Segoe UI', 10, 'bold'),
                         text_color=COLORS['label_dim']).pack(side='left', padx=8)
            ctk.CTkFrame(f, height=1, fg_color=COLORS['card_border']).pack(side='left', fill='x', expand=True, padx=6)

        def add_row(profile_name):
            stat = get_account_stat(profile_name)
            ch = stat.get('chapters', 0)
            frozen = is_account_frozen(profile_name)
            freeze_until = stat.get('freeze_until', '')

            row_color = '#2a0a0a' if frozen else COLORS['entry_bg']
            row = ctk.CTkFrame(self._accounts_body, fg_color=row_color, corner_radius=8,
                               border_width=1, border_color=COLORS['red'] if frozen else COLORS['card_border'])
            row.pack(fill='x', padx=4, pady=2)
            row.grid_columnconfigure(0, weight=1)

            # Имя аккаунта
            ctk.CTkLabel(row, text=('🔒 ' if frozen else ('✅ ' if ch > 0 else '⬜ ')) + profile_name,
                         font=('Segoe UI', 12, 'bold'),
                         text_color=COLORS['red'] if frozen else (COLORS['accent_green'] if ch > 0 else COLORS['text_dim']),
                         anchor='w').grid(row=0, column=0, padx=12, pady=8, sticky='w')

            # Статус
            status_text = '❄ Заморожен' if frozen else ('🟢 Использован' if ch > 0 else '⬜ Не использован')
            ctk.CTkLabel(row, text=status_text, font=('Segoe UI', 11), width=120,
                         text_color=COLORS['red'] if frozen else (COLORS['text_main'] if ch > 0 else COLORS['text_dim']),
                         anchor='w').grid(row=0, column=1, padx=6, pady=8, sticky='w')

            # Глав сегодня
            ctk.CTkLabel(row, text=f'{ch} / {CHAPTERS_FREEZE_LIMIT}', font=('Segoe UI', 11), width=110,
                         text_color=COLORS['text_main'], anchor='w').grid(row=0, column=2, padx=6, pady=8, sticky='w')

            # Прогресс-бар
            pb_f = ctk.CTkFrame(row, fg_color='transparent', width=150)
            pb_f.grid(row=0, column=3, padx=6, pady=8, sticky='w')
            pb = ctk.CTkProgressBar(pb_f, height=8, width=140, corner_radius=4,
                                    progress_color=COLORS['red'] if frozen else COLORS['accent_green'],
                                    fg_color=COLORS['card_border'])
            pb.pack()
            pb.set(min(ch / CHAPTERS_FREEZE_LIMIT, 1.0))

            # До разморозки / кнопка разморозить
            if frozen and freeze_until:
                btn_f = ctk.CTkFrame(row, fg_color='transparent')
                btn_f.grid(row=0, column=4, padx=6, pady=6, sticky='w')
                ctk.CTkLabel(btn_f, text=f'до {freeze_until}', font=('Segoe UI', 10),
                             text_color=COLORS['red']).pack(side='left', padx=(0, 6))
                ctk.CTkButton(btn_f, text='🔓', width=34, height=28, corner_radius=6,
                              fg_color=COLORS['accent_green'], hover_color=COLORS['hover_green'],
                              text_color=COLORS['bg'], font=('Segoe UI', 12),
                              command=lambda n=profile_name: self._do_unfreeze(n)).pack(side='left')
            else:
                ctk.CTkLabel(row, text='—', font=('Segoe UI', 11),
                             text_color=COLORS['text_dim']).grid(row=0, column=4, padx=6, pady=8, sticky='w')

        if used_today:
            section_sep(f'ИСПОЛЬЗОВАНЫ СЕГОДНЯ ({len(used_today)})')
            for p in used_today:
                add_row(p)

        if not_used_today:
            section_sep(f'НЕ ИСПОЛЬЗОВАЛИСЬ СЕГОДНЯ ({len(not_used_today)})')
            for p in not_used_today:
                add_row(p)

# ==================== КАРТОЧКА ЗАДАЧИ ====================

class TaskCard(ctk.CTkFrame):
    def __init__(self, parent, index, delete_cb, app_ref):
        super().__init__(parent, fg_color=COLORS['card'], corner_radius=10,
                         border_width=1, border_color=COLORS['card_border'])
        # Место в сетке (3 книги в ряд) задаёт App через _relayout_book_grid(),
        # поэтому саму себя карточка больше не пакует.
        self.app = app_ref
        self.is_saved = False
        self.is_hidden = False
        self.cover_url = ''
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Общее состояние "активна" — используется и галочкой на плитке (компактный
        # режим), и галочкой в развёрнутых настройках; обе привязаны к одной переменной.
        self.active_var = ctk.BooleanVar(value=True)

        # ════════════════════ КОМПАКТНАЯ ПЛИТКА (сетка книг) ════════════════════
        # Блок "обложка + название + количество глав" — параметр в параметр
        # скопирован из плитки раздела «Редактор» (см. render_editor_books_view):
        # тот же corner_radius, те же паддинги, тот же шрифт и цвет текста.
        # Ничего не наложено НА обложку — управление (галочка/удаление/скрыть)
        # вынесено отдельной полоской ПОД обложкой, чтобы не отличаться от
        # «Редактора» ни на пиксель там, где сравнение действительно важно.
        self.compact_view = ctk.CTkFrame(self, fg_color='transparent')
        self.compact_view.grid(row=0, column=0, sticky='new')

        self.cover_wrap = ctk.CTkLabel(self.compact_view, text='📖', font=('Arial', 26),
                                        width=120, height=160,
                                        fg_color=COLORS['entry_bg'], corner_radius=8,
                                        text_color=COLORS['label_dim'])
        self.cover_wrap.pack(padx=14, pady=(14, 10))
        self.cover_lbl = self.cover_wrap  # общий объект: и рамка обложки, и место для картинки

        self.title_lbl = ctk.CTkLabel(self.compact_view, text=f'КНИГА #{index}',
                                       font=('Segoe UI', 12, 'bold'), anchor='center',
                                       justify='center', wraplength=150)
        self.title_lbl.pack(fill='x', padx=10)

        self.chapters_info_lbl = ctk.CTkLabel(self.compact_view, text='',
                                               text_color=COLORS['text_dim'],
                                               font=('Segoe UI', 10))
        self.chapters_info_lbl.pack(pady=(2, 10))

        # Клик по обложке/названию/статусу открывает настройки книги на весь экран
        for w in (self.compact_view, self.cover_wrap, self.title_lbl, self.chapters_info_lbl):
            w.configure(cursor='hand2')
            w.bind('<Button-1>', self._on_card_click)

        # ─── Полоска управления — отдельно от обложки, под ней ───
        ctrl_row = ctk.CTkFrame(self.compact_view, fg_color='transparent')
        ctrl_row.pack(fill='x', padx=12, pady=(0, 12))
        self.chk_active = ctk.CTkCheckBox(ctrl_row, text='', width=18, checkbox_width=18, checkbox_height=18,
                                           fg_color=COLORS['accent_green'],
                                           checkmark_color=COLORS['bg'],
                                           border_color=COLORS['text_dim'],
                                           variable=self.active_var,
                                           command=self._save_data)
        self.chk_active.select()
        self.chk_active.pack(side='left')
        ctk.CTkButton(ctrl_row, text='🙈', width=26, height=22, corner_radius=6,
                      fg_color=COLORS['entry_bg'], hover_color=COLORS['card_border'],
                      text_color=COLORS['text_dim'], font=('Segoe UI', 10),
                      command=lambda: self.app.hide_book(self)).pack(side='right', padx=(4, 0))
        ctk.CTkButton(ctrl_row, text='✕', width=26, height=22, corner_radius=6,
                      fg_color=COLORS['entry_bg'], hover_color=COLORS['red'],
                      text_color=COLORS['text_dim'], font=('Segoe UI', 11, 'bold'),
                      command=lambda: delete_cb(self)).pack(side='right')

        # ════════════════════ РАЗВЁРНУТЫЙ ВИД (настройки на весь экран) ════════════════════
        self.detail_view = ctk.CTkFrame(self, fg_color='transparent')
        self.detail_view.grid(row=0, column=0, sticky='new')
        self.detail_view.grid_columnconfigure(1, weight=1)
        self.detail_view.grid_remove()  # скрыт по умолчанию — открывается кликом по плитке

        self.cover_f = ctk.CTkFrame(self.detail_view, width=100, height=140, fg_color=COLORS['entry_bg'], corner_radius=8)
        self.cover_f.grid(row=0, column=0, rowspan=7, padx=14, pady=14, sticky='n')
        self.cover_lbl_detail = ctk.CTkLabel(self.cover_f, text='📖', font=('Arial', 24),
                                              text_color=COLORS['label_dim'])
        self.cover_lbl_detail.place(relx=0.5, rely=0.5, anchor='center')

        header = ctk.CTkFrame(self.detail_view, fg_color='transparent')
        header.grid(row=0, column=1, sticky='ew', padx=(0, 14), pady=(12, 4))

        ctk.CTkCheckBox(header, text='', width=20, variable=self.active_var,
                         fg_color=COLORS['accent_green'], checkmark_color=COLORS['bg'],
                         command=self._save_data).pack(side='left')

        self.title_lbl_detail = ctk.CTkLabel(header, text=f'КНИГА #{index}',
                                              font=('Segoe UI', 13, 'bold'),
                                              text_color=COLORS['accent_green'], anchor='w',
                                              wraplength=140, justify='left')
        self.title_lbl_detail.pack(side='left', padx=6)

        self.chapters_info_lbl_detail = ctk.CTkLabel(header, text='',
                                                      font=('Segoe UI', 10),
                                                      text_color=COLORS['text_dim'])
        self.chapters_info_lbl_detail.pack(side='left', padx=10)

        ctk.CTkButton(header, text='✕', width=26, height=26, corner_radius=6,
                      fg_color='transparent', text_color=COLORS['text_dim'],
                      hover_color=COLORS['red'],
                      command=lambda: delete_cb(self)).pack(side='right')
        self.save_btn = ctk.CTkButton(header, text='✓', width=26, height=26, corner_radius=6,
                                       fg_color=COLORS['entry_bg'],
                                       text_color=COLORS['accent_green'],
                                       hover_color=COLORS['card_border'],
                                       command=self.mark_saved)
        self.save_btn.pack(side='right', padx=4)

        # Кнопка "← Все книги" — возврат к сетке из развёрнутого режима
        self.back_btn = ctk.CTkButton(header, text='← Все книги', width=100, height=26, corner_radius=6,
                                       fg_color=COLORS['entry_bg'], hover_color=COLORS['card_border'],
                                       text_color=COLORS['text_main'],
                                       command=lambda: self.app._show_book_grid())
        self.back_btn.pack(side='right', padx=10)

        # Кнопка "Скрыть книгу" — переносит книгу в раздел «Скрытые книги»
        # (на «Редактор» это не влияет — он читает главы с диска независимо)
        ctk.CTkButton(header, text='🙈 Скрыть', width=90, height=26, corner_radius=6,
                      fg_color=COLORS['entry_bg'], hover_color=COLORS['card_border'],
                      text_color=COLORS['text_main'],
                      command=lambda: self.app.hide_book(self)).pack(side='right', padx=(0, 4))

        self._details_visible = False

        # ─── Блок настроек (внутри развёрнутого вида) ───
        self.details_frame = ctk.CTkFrame(self.detail_view, fg_color='transparent')
        self.details_frame.grid(row=1, column=1, sticky='ew', padx=(0, 14))

        self.ent_rulate = self.add_row(self.details_frame, 'RuLate:')
        self.ent_rulate.bind('<FocusOut>', self.on_link_change)
        self.ent_rulate.bind('<KeyRelease>', self._debounce_link)
        self.ent_rulate.bind('<KeyRelease>', self._debounce_autosave, add='+')
        self._link_after_id = None
        self._autosave_after_id = None
        self.ent_tomato = self.add_row(self.details_frame, 'Tomato:')
        self.ent_tomato.bind('<KeyRelease>', self._debounce_autosave)

        row3 = ctk.CTkFrame(self.details_frame, fg_color='transparent')
        row3.pack(fill='x', pady=2)
        ctk.CTkLabel(row3, text='Старт с:', width=50, font=('Segoe UI', 11), text_color=COLORS['text_dim']).pack(side='left')
        self.ent_start = ctk.CTkEntry(row3, width=58, height=28, fg_color=COLORS['entry_bg'],
                                       border_width=1, border_color=COLORS['card_border'],
                                       text_color=COLORS['text_main'], corner_radius=6)
        self.ent_start.insert(0, '1')
        self.ent_start.pack(side='left')
        self.ent_start.bind('<KeyRelease>', self._debounce_autosave)
        self.ent_start.bind('<KeyRelease>', lambda e: self._update_paid_from_start(), add='+')
        self.ent_start.bind('<FocusOut>', lambda e: self._update_paid_from_start())

        ctk.CTkLabel(row3, text='Кол-во:', font=('Segoe UI', 11), text_color=COLORS['text_dim']).pack(side='left', padx=(10, 5))
        self.ent_limit = ctk.CTkEntry(row3, width=55, height=28, fg_color=COLORS['entry_bg'],
                                       border_width=1, border_color=COLORS['card_border'],
                                       text_color=COLORS['text_main'], corner_radius=6)
        self.ent_limit.insert(0, '200')
        self.ent_limit.pack(side='left')
        self.ent_limit.bind('<KeyRelease>', self._debounce_autosave)

        ctk.CTkLabel(row3, text='Аккаунты:', font=('Segoe UI', 11), text_color=COLORS['text_dim']).pack(side='left', padx=(14, 5))
        self.selected_profiles = list(self.app.profiles)
        self.acc_btn = ctk.CTkButton(row3, text=self._accounts_label(), height=28, width=135,
                                     fg_color=COLORS['entry_bg'], hover_color=COLORS['card_border'],
                                     text_color=COLORS['text_main'], border_width=1,
                                     border_color=COLORS['card_border'], corner_radius=6,
                                     font=('Segoe UI', 11), command=self.open_account_picker)
        self.acc_btn.pack(side='left', padx=5)
        self.prof_var = ctk.StringVar(value=self.selected_profiles[0] if self.selected_profiles else "Default")

        self.promo_btn = ctk.CTkButton(row3, text='🎁 Добавить акцию', height=28,
                                        fg_color=COLORS['entry_bg'], hover_color=COLORS['card_border'],
                                        text_color=COLORS['text_main'], border_width=1,
                                        border_color=COLORS['card_border'], corner_radius=6,
                                        font=('Segoe UI', 11), command=self.add_promo_chapter)
        self.promo_btn.pack(side='left', padx=5)

        row4 = ctk.CTkFrame(self.details_frame, fg_color='transparent')
        row4.pack(fill='x', pady=2)
        ctk.CTkLabel(row4, text='Промпт:', width=55, font=('Segoe UI', 11), text_color=COLORS['text_dim']).pack(side='left')
        self.ent_prompt = ctk.CTkEntry(row4, height=28, fg_color=COLORS['entry_bg'],
                                        border_width=1, border_color=COLORS['card_border'],
                                        text_color=COLORS['text_main'], corner_radius=6)
        self.ent_prompt.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.ent_prompt.bind('<KeyRelease>', self._debounce_autosave)
        ctk.CTkButton(row4, text='📂', width=28, height=28, corner_radius=6,
                      fg_color=COLORS['entry_bg'], hover_color=COLORS['card_border'],
                      border_width=1, border_color=COLORS['card_border'],
                      text_color=COLORS['text_main'], command=self.browse).pack(side='right')

        row5 = ctk.CTkFrame(self.details_frame, fg_color='transparent')
        row5.pack(fill='x', pady=8)
        self.sw_paid = ctk.CTkSwitch(row5, text='Платная', font=('Segoe UI', 11),
                                      progress_color=COLORS['accent_green'],
                                      text_color=COLORS['text_main'], command=self._save_data)
        self.sw_paid.pack(side='left', padx=(0, 20))
        self.sw_otl = ctk.CTkSwitch(row5, text='Отложка', font=('Segoe UI', 11),
                                     progress_color=COLORS['accent_green'],
                                     text_color=COLORS['text_main'], command=self._save_data)
        self.sw_otl.pack(side='left')
        self._update_paid_from_start()  # применить при создании (после того, как sw_paid уже существует)
        self.pg = ctk.CTkProgressBar(self.details_frame, height=3, progress_color=COLORS['accent_green'],
                                      fg_color=COLORS['entry_bg'], corner_radius=2)
        self.pg.pack(fill='x', pady=(4, 12))
        self.pg.set(0)

    def _update_paid_from_start(self, event=None):
        """Автоматически ставит платность в зависимости от поля «Старт с»:
        1-20 → бесплатно, 21+ → платно."""
        try:
            start_val = int(self.ent_start.get() or 1)
        except ValueError:
            return
        if start_val >= 1 and start_val <= 20:
            if self.sw_paid.get():
                self.sw_paid.deselect()
        elif start_val >= 21:
            if not self.sw_paid.get():
                self.sw_paid.select()
        self._save_data()

    def add_promo_chapter(self):
        """Публикует на RuLate главу-акцию (название и текст — PROMO_CHAPTER_TITLE /
        PROMO_CHAPTER_TEXT вверху файла) прямо в эту книгу. Использует первый
        выбранный для книги аккаунт и ту же логику публикации, что и кнопка
        "Добавить на RuLate" в Редакторе (self.app._post_chapter_to_rulate)."""
        rulate_url = self.ent_rulate.get().strip()
        if not rulate_url:
            messagebox.showerror('Ошибка', 'Сначала укажите ссылку RuLate для этой книги.')
            return
        if not self.selected_profiles:
            messagebox.showerror('Ошибка', 'Для этой книги не выбран ни один аккаунт (см. кнопку "Аккаунты").')
            return
        profile = self.selected_profiles[0]
        if not messagebox.askyesno('Акция',
                                    f'Опубликовать главу-акцию "{PROMO_CHAPTER_TITLE}" '
                                    f'в этой книге профилем "{profile}"?'):
            return
        self.app.log(f'🎁 Публикую главу-акцию (профиль {profile})...')
        threading.Thread(target=self.app._manual_promo_publish_worker,
                          args=(rulate_url, profile), daemon=True).start()

    def _on_card_click(self, event=None):
        """Клик по обложке/названию карточки в сетке — открывает настройки
        этой книги на весь экран (сетка книг прячется, показывается back_btn)."""
        self.app._open_book_detail(self)

    def set_grid_mode(self, is_detail):
        """Переключает визуальное состояние карточки между компактной плиткой
        в сетке (обложка+название, как в разделе «Редактор») и развёрнутым
        видом с настройками книги на весь экран."""
        self._details_visible = is_detail
        if is_detail:
            self.compact_view.grid_remove()
            self.detail_view.grid()
        else:
            self.detail_view.grid_remove()
            self.compact_view.grid()

    def _set_cover_image(self, ctk_img):
        """Обновляет обложку сразу в компактной плитке и в развёрнутом виде,
        и кэширует картинку — её же переиспользует плитка в «Скрытых книгах»."""
        self._ctk_img_cache = ctk_img
        self.cover_lbl.configure(image=ctk_img, text='')
        self.cover_lbl_detail.configure(image=ctk_img, text='')

    def _sync_title(self, text, color=None):
        """Обновляет название книги сразу в плитке и в развёрнутом виде."""
        self.title_lbl.configure(text=text)
        self.title_lbl_detail.configure(text=text)
        if color:
            self.title_lbl.configure(text_color=color)
            self.title_lbl_detail.configure(text_color=color)

    def _sync_chapters_info(self, text):
        """Обновляет статус/кол-во глав сразу в плитке и в развёрнутом виде."""
        self.chapters_info_lbl.configure(text=text)
        self.chapters_info_lbl_detail.configure(text=text)

    def _accounts_label(self):
        n = len(self.selected_profiles)
        total = len(self.app.profiles)
        if n == 0: return '⚠ Нет аккаунтов'
        if n == total: return f'✔ Все ({n})'
        return f'✔ {n} из {total}'

    def open_account_picker(self):
        popup = ctk.CTkToplevel(self)
        popup.title('Выбор аккаунтов')
        popup.geometry('440x500')
        popup.configure(fg_color=COLORS['bg'])
        popup.after(10, popup.lift)
        ctk.CTkLabel(popup, text='Аккаунты для этой книги',
                     font=('Segoe UI', 14, 'bold'), text_color=COLORS['accent_green']).pack(pady=(14, 2))
        ctk.CTkLabel(popup, text='Порядок выбора = очерёдность ротации. 🔒 = заморожен, нельзя выбрать.',
                     font=('Segoe UI', 10), text_color=COLORS['text_dim'], wraplength=400).pack(pady=(0, 8))

        outer = ctk.CTkScrollableFrame(popup, fg_color=COLORS['scrollable'], corner_radius=8)
        outer.pack(fill='both', expand=True, padx=15, pady=(0, 8))

        check_vars = {}
        for i, p in enumerate(self.app.profiles):
            frozen = is_account_frozen(p)
            stat = get_account_stat(p)
            ch = stat.get('chapters', 0)
            freeze_until = stat.get('freeze_until', '')

            var = ctk.BooleanVar(value=(p in self.selected_profiles and not frozen))
            check_vars[p] = var

            row_frame = ctk.CTkFrame(outer, fg_color='transparent')
            row_frame.grid(row=i, column=0, columnspan=3, sticky='ew', padx=4, pady=2)
            row_frame.grid_columnconfigure(0, weight=1)

            cb_text = ('🔒 ' if frozen else '') + p
            cb = ctk.CTkCheckBox(
                row_frame, text=cb_text, variable=var,
                fg_color=COLORS['red'] if frozen else COLORS['accent_green'],
                text_color=COLORS['text_dim'] if frozen else COLORS['text_main'],
                font=('Segoe UI', 12), state='disabled' if frozen else 'normal',
            )
            cb.pack(side='left')

            # Подпись: глав / заморожен до
            if frozen:
                ctk.CTkLabel(row_frame, text=f'❄ заморожен до {freeze_until}',
                             font=('Segoe UI', 10), text_color=COLORS['red']).pack(side='left', padx=8)
            else:
                ctk.CTkLabel(row_frame, text=f'📖 {ch}/100 сегодня',
                             font=('Segoe UI', 10), text_color=COLORS['text_dim']).pack(side='left', padx=8)

        # Кнопки Выбрать все / Снять все (только незамороженные)
        btn_row = ctk.CTkFrame(popup, fg_color='transparent')
        btn_row.pack(fill='x', padx=15, pady=(0, 4))
        def select_all():
            for p, v in check_vars.items():
                if not is_account_frozen(p): v.set(True)
        def deselect_all():
            for v in check_vars.values(): v.set(False)
        ctk.CTkButton(btn_row, text='Выбрать все', width=120, height=28,
                      fg_color=COLORS['entry_bg'], command=select_all).pack(side='left', padx=(0, 8))
        ctk.CTkButton(btn_row, text='Снять все', width=120, height=28,
                      fg_color=COLORS['entry_bg'], command=deselect_all).pack(side='left')

        def apply():
            self.selected_profiles = [p for p in self.app.profiles if check_vars[p].get() and not is_account_frozen(p)]
            if not self.selected_profiles:
                unfrozen = [p for p in self.app.profiles if not is_account_frozen(p)]
                self.selected_profiles = [unfrozen[0]] if unfrozen else [self.app.profiles[0]]
            self.prof_var.set(self.selected_profiles[0])
            self.acc_btn.configure(text=self._accounts_label())
            self._save_data()
            popup.destroy()
        ctk.CTkButton(popup, text='Применить', fg_color=COLORS['accent_green'],
                      hover_color=COLORS['hover_green'], text_color=COLORS['bg'],
                      height=38, command=apply).pack(pady=8, padx=15, fill='x')

    def add_row(self, parent, label):
        f = ctk.CTkFrame(parent, fg_color='transparent')
        f.pack(fill='x', pady=2)
        ctk.CTkLabel(f, text=label, width=55, anchor='w', font=('Segoe UI', 11),
                     text_color=COLORS['text_dim']).pack(side='left')
        e = ctk.CTkEntry(f, height=28, fg_color=COLORS['entry_bg'],
                         border_width=1, border_color=COLORS['card_border'],
                         text_color=COLORS['text_main'], corner_radius=6)
        e.pack(side='left', fill='x', expand=True)
        return e

    def update_counter(self, val):
        self.ent_start.delete(0, tk.END)
        self.ent_start.insert(0, str(val))

    def browse(self):
        f = filedialog.askopenfilename(filetypes=[('Text files', '*.txt')])
        if f:
            self.ent_prompt.delete(0, tk.END)
            self.ent_prompt.insert(0, f)

    def _debounce_link(self, event=None):
        if self._link_after_id:
            self.after_cancel(self._link_after_id)
        self._link_after_id = self.after(800, self.on_link_change)

    def _debounce_autosave(self, event=None):
        """Автосохранение полей книги без нажатия галочки — с небольшой задержкой,
        чтобы не писать в файл на каждое нажатие клавиши."""
        if self._autosave_after_id:
            self.after_cancel(self._autosave_after_id)
        self._autosave_after_id = self.after(600, self._save_data)

    def on_link_change(self, event=None):
        url = self.ent_rulate.get().strip()
        if 'tl.rulate.ru/book/' in url:
            threading.Thread(target=self.fetch_metadata, args=(url,), daemon=True).start()

    def fetch_metadata(self, url):
        h = load_json(HISTORY_FILE, {})
        if url in h:
            self.after(0, lambda: self.fill_from_history(h[url]))
        try:
            import urllib.request as _ur
            req = _ur.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with _ur.urlopen(req, timeout=10) as r:
                html = r.read().decode('utf-8', errors='ignore')
            # Парсим заголовок
            title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ''
            # Парсим обложку
            img_m = re.search(r'id=["\']Info["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
            if not img_m:
                img_m = re.search(r'class=["\'][^"\']*images[^"\']*["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
            img_url = img_m.group(1) if img_m else ''
            if img_url and img_url.startswith('/'):
                img_url = 'https://tl.rulate.ru' + img_url
            # Парсим кол-во глав
            ch_m = re.search(r'Размер перевода.*?(\d+)', html, re.DOTALL)
            ch_count = ch_m.group(1) if ch_m else '?'
            if title or img_url:
                self.after(0, lambda: self.update_ui_metadata(title, img_url, ch_count))
        except Exception as e:
            # Fallback через selenium
            try:
                opts = self.app.get_stealth_options('Metadata_Temp')
                opts.add_argument('--headless')
                driver = self.app._new_chrome_driver(opts)
                driver.get(url)
                title = ''
                img_url = ''
                ch_count = '?'
                try: title = driver.find_element(By.CSS_SELECTOR, 'article h1').text.strip()
                except: pass
                try: img_url = driver.find_element(By.CSS_SELECTOR, '#Info .images img').get_attribute('src')
                except: pass
                try:
                    ch_count_text = driver.find_element(By.XPATH, "//dt[contains(text(), 'Размер перевода')]/following-sibling::dd[1]").text
                    ch_count = re.search(r'(\d+)', ch_count_text).group(1)
                except: pass
                driver.quit()
                if title or img_url:
                    self.after(0, lambda: self.update_ui_metadata(title, img_url, ch_count))
            except:
                pass

    def fill_from_history(self, data):
        self.ent_tomato.delete(0, tk.END)
        self.ent_tomato.insert(0, data.get('tomato', ''))
        self.ent_prompt.delete(0, tk.END)
        self.ent_prompt.insert(0, data.get('prompt', ''))
        self.ent_start.delete(0, tk.END)
        self.ent_start.insert(0, str(data.get('start', 1) or 1))
        self._update_paid_from_start()
        if 'limit' in data:
            self.ent_limit.delete(0, tk.END)
            self.ent_limit.insert(0, str(data['limit']))
        if 'profile' in data:
            self.prof_var.set(data['profile'])
        if 'selected_profiles' in data:
            self.selected_profiles = [p for p in data['selected_profiles'] if p in self.app.profiles]
            if not self.selected_profiles:
                self.selected_profiles = list(self.app.profiles)
            self.acc_btn.configure(text=self._accounts_label())
        if data.get('cover_url'):
            self.cover_url = data['cover_url']
            try:
                res = requests.get(self.cover_url, timeout=5)
                img = Image.open(BytesIO(res.content))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 160))
                self._set_cover_image(ctk_img)
            except:
                pass

    def update_ui_metadata(self, title, img_url, ch_count):
        self._sync_title(title[:50] + '...')
        self._sync_chapters_info(f'Уже на сайте: {ch_count}')
        self.cover_url = img_url or getattr(self, 'cover_url', '')
        try:
            res = requests.get(img_url, timeout=5)
            img = Image.open(BytesIO(res.content))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 160))
            self._set_cover_image(ctk_img)
        except:
            pass

    def _save_data(self):
        """Единая точка сохранения книги в историю — вызывается и вручную (галочка),
        и автоматически при любом изменении полей (автосохранение)."""
        r, t, p, s, pr, lim = (self.ent_rulate.get(), self.ent_tomato.get(), self.ent_prompt.get(), self.ent_start.get(), self.prof_var.get(), self.ent_limit.get())
        if r and t and p:
            h = load_json(HISTORY_FILE, {})
            h[r] = {'tomato': t, 'prompt': p, 'start': int(s or 0), 'profile': pr,
                    'limit': int(lim or 200), 'selected_profiles': self.selected_profiles,
                    'cover_url': self.cover_url}
            save_json(HISTORY_FILE, h)
            if not self.is_saved:
                self.is_saved = True
            base_title = self.title_lbl.cget('text').split('✓')[0].strip()
            self._sync_title(f'{base_title} ✓', color=COLORS['accent_green'])
            return True
        return False

    def mark_saved(self):
        self._save_data()

    def get_data(self):
        return {
            'r': self.ent_rulate.get(), 
            't': self.ent_tomato.get(), 
            'start': max(int(self.ent_start.get() or 1), 1), 
            'limit': int(self.ent_limit.get() or 200), 
            'is_delayed': self.sw_otl.get(), 
            'is_paid': self.sw_paid.get(),
            'card': self, 
            'pr': self.ent_prompt.get(),
            'profile': self.prof_var.get(),
            'selected_profiles': list(self.selected_profiles),
            'active': self.active_var.get(),
            'is_saved': self.is_saved,
            'cover_url': self.cover_url,
            'book_title': self.title_lbl.cget('text').split(' ✓')[0].strip(),
        }

# ==================== ГЛАВНОЕ ОКНО ====================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('AI TRANSLATOR SCRIPT')
        self.geometry('1150x850')
        self.profiles = load_json(PROFILES_FILE, ['Default'])

        # Восстанавливаем тему до отрисовки UI
        saved_state = load_json(APP_STATE_FILE, {})
        global CURRENT_THEME, COLORS
        if saved_state.get('theme') in THEMES:
            CURRENT_THEME = saved_state['theme']
            COLORS = dict(THEMES[CURRENT_THEME])
            ctk.set_appearance_mode(THEMES[CURRENT_THEME]['ctk_mode'])

        self.configure(fg_color=COLORS['bg'])
        self.sidebar = ctk.CTkFrame(self, width=235, fg_color=COLORS['sidebar'], corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Logo header
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color=COLORS['card'], corner_radius=0, height=72)
        logo_frame.pack(fill='x')
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(logo_frame, text='⚡ AI TRANSLATE', font=('Impact', 22),
                     text_color=COLORS['accent_green']).place(relx=0.5, rely=0.5, anchor='center')
        # Accent border
        ctk.CTkFrame(self.sidebar, height=3, fg_color=COLORS['accent_green']).pack(fill='x')

        # Scrollable sidebar
        sidebar_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color='transparent', corner_radius=0,
                                                scrollbar_button_color=COLORS['card_border'],
                                                scrollbar_button_hover_color=COLORS['accent_green'])
        sidebar_scroll.pack(fill='both', expand=True)
        ctk.CTkFrame(sidebar_scroll, height=10, fg_color='transparent').pack()

        def nav_btn(text, color, cmd, is_accent=False):
            btn = ctk.CTkButton(
                sidebar_scroll, text=text, fg_color=color,
                hover_color=COLORS['hover_green'] if is_accent else COLORS['card_border'],
                font=('Segoe UI', 12, 'bold' if is_accent else 'normal'),
                text_color=COLORS['bg'] if is_accent else COLORS['text_main'],
                anchor='w', height=38, corner_radius=8, border_width=1 if not is_accent else 0,
                border_color=COLORS['card_border'],
                command=cmd
            )
            btn.pack(padx=12, pady=3, fill='x')

        nav_btn('✚  Добавить книгу', COLORS['accent_green'], self.add_book, True)
        nav_btn('👤  Профили', COLORS['card'], self.open_accounts_tab)
        nav_btn('🚀  Запустить всё', COLORS['accent_green'], self.start_all, True)
        nav_btn('⛔  Остановить', COLORS['card'], self.stop_all)

        def section_label(text):
            f = ctk.CTkFrame(sidebar_scroll, fg_color='transparent')
            f.pack(fill='x', padx=12, pady=(14, 4))
            ctk.CTkFrame(f, height=1, fg_color=COLORS['card_border']).pack(fill='x', pady=(0, 5))
            ctk.CTkLabel(f, text=text, font=('Segoe UI', 9, 'bold'),
                         text_color=COLORS['label_dim']).pack(anchor='w')

        section_label('НАСТРОЙКИ')
        self._settings_visible = False

        def toggle_settings():
            if self._settings_visible:
                settings_frame.pack_forget()
                settings_toggle_btn.configure(text='⚙  Режим, тема, ожидание...   ▸')
            else:
                settings_frame.pack(fill='x', padx=0, pady=(2, 6))
                settings_toggle_btn.configure(text='⚙  Режим, тема, ожидание...   ▾')
            self._settings_visible = not self._settings_visible

        settings_toggle_btn = ctk.CTkButton(
            sidebar_scroll, text='⚙  Режим, тема, ожидание...   ▸',
            fg_color=COLORS['card'], hover_color=COLORS['card_border'],
            text_color=COLORS['text_main'], anchor='w', height=34, corner_radius=7,
            font=('Segoe UI', 11), border_width=1, border_color=COLORS['card_border'],
            command=toggle_settings
        )
        settings_toggle_btn.pack(padx=12, pady=(2, 2), fill='x')

        # Раскрывающаяся панель — скрыта по умолчанию, открывается по клику выше
        settings_frame = ctk.CTkFrame(sidebar_scroll, fg_color='transparent')

        def sub_label(text):
            ctk.CTkLabel(settings_frame, text=text, font=('Segoe UI', 9, 'bold'),
                         text_color=COLORS['label_dim']).pack(anchor='w', padx=8, pady=(8, 2))

        sub_label('РЕЖИМ ПЕРЕВОДА')
        self.mode_var = ctk.StringVar(value='sequential')
        ctk.CTkRadioButton(settings_frame, text='По очереди', variable=self.mode_var, value='sequential',
                           font=('Segoe UI', 11), fg_color=COLORS['accent_green'],
                           text_color=COLORS['text_main']).pack(padx=20, anchor='w')
        ctk.CTkRadioButton(settings_frame, text='Все вместе', variable=self.mode_var, value='parallel',
                           font=('Segoe UI', 11), fg_color=COLORS['accent_green'],
                           text_color=COLORS['text_main']).pack(padx=20, anchor='w', pady=5)

        sub_label('ВРЕМЯ ОЖИДАНИЯ')
        self.ai_wait_ent = ctk.CTkEntry(
            settings_frame, placeholder_text='Задержка AI (сек)',
            fg_color=COLORS['entry_bg'], border_color=COLORS['card_border'],
            text_color=COLORS['text_main'], height=34, corner_radius=7
        )
        self.ai_wait_ent.insert(0, '25')
        self.ai_wait_ent.pack(padx=12, pady=5, fill='x')

        sub_label('ПРОПУСК ВХОДА')
        self.skip_ai = self._add_check_to(settings_frame, 'Пропуск Deepseek')
        self.skip_tom = self._add_check_to(settings_frame, 'Пропуск Tomato')
        self.skip_rul = self._add_check_to(settings_frame, 'Пропуск RuLate')

        sub_label('БРАУЗЕР')
        self.headless_mode = self._add_check_to(settings_frame, 'Скрытый браузер')

        sub_label('УВЕДОМЛЕНИЯ')
        self.balance_notify_var = ctk.BooleanVar(value=True)
        self.balance_notify_cb = ctk.CTkCheckBox(settings_frame, text='Уведомления о балансе',
                                                  variable=self.balance_notify_var,
                                                  font=('Segoe UI', 11), fg_color=COLORS['accent_green'],
                                                  text_color=COLORS['text_main'], checkmark_color=COLORS['bg'])
        self.balance_notify_cb.pack(padx=20, anchor='w', pady=2)

        sub_label('ТЕМА ОФОРМЛЕНИЯ')
        self.theme_var = ctk.StringVar(value=CURRENT_THEME)
        theme_frame = ctk.CTkFrame(settings_frame, fg_color='transparent')
        theme_frame.pack(padx=8, fill='x', pady=(0, 8))
        theme_icons = {
            'Оникс': '⚫', 'Слоновая кость': '⚪', 'Графит': '◆',
            'Изумруд': '🟢', 'Туман': '☁️', 'Полночь': '🌌',
        }
        for t_name in THEMES:
            ctk.CTkRadioButton(
                theme_frame, text=f'{theme_icons.get(t_name, "◉")} {t_name}',
                variable=self.theme_var, value=t_name,
                font=('Segoe UI', 11), fg_color=COLORS['accent_green'],
                text_color=COLORS['text_main'],
                command=self.apply_theme
            ).pack(anchor='w', pady=2, padx=12)

        # Main content area
        self.main = ctk.CTkFrame(self, fg_color=COLORS['bg'], corner_radius=0)
        self.main.pack(side='right', fill='both', expand=True, padx=0, pady=0)
        self.tabs = ctk.CTkTabview(
            self.main,
            fg_color=COLORS['card'],
            segmented_button_fg_color=COLORS['sidebar'],
            segmented_button_selected_color=COLORS['accent_green'],
            segmented_button_selected_hover_color=COLORS['hover_green'],
            segmented_button_unselected_color=COLORS['sidebar'],
            segmented_button_unselected_hover_color=COLORS['card_border'],
            text_color=COLORS['text_main'],
            corner_radius=10,
        )
        self.tabs.pack(fill='both', expand=True, padx=15, pady=15)

        self.task_list = ctk.CTkScrollableFrame(
            self.tabs.add('📚  Книги'),
            fg_color='transparent',
            scrollbar_button_color=COLORS['card_border'],
            scrollbar_button_hover_color=COLORS['accent_green'],
        )
        self.task_list.pack(fill='both', expand=True)
        for col_i in range(3):
            self.task_list.grid_columnconfigure(col_i, weight=1, uniform='bookcol')
        self._book_grid_open_card = None

        self.hidden_list = ctk.CTkScrollableFrame(
            self.tabs.add('🙈  Скрытые книги'),
            fg_color='transparent',
            scrollbar_button_color=COLORS['card_border'],
            scrollbar_button_hover_color=COLORS['accent_green'],
        )
        self.hidden_list.pack(fill='both', expand=True)
        for col_i in range(3):
            self.hidden_list.grid_columnconfigure(col_i, weight=1, uniform='hiddencol')

        log_tab = self.tabs.add('📋  Логи')
        log_tab.configure(fg_color=COLORS['bg'])
        self.log_box = ctk.CTkTextbox(
            log_tab, font=('Consolas', 11),
            fg_color=COLORS['entry_bg'],
            text_color=COLORS['text_main'],
            border_color=COLORS['card_border'],
            border_width=1, corner_radius=8
        )
        self.log_box.pack(fill='both', expand=True, padx=12, pady=12)
        
        self.editor_tab = self.tabs.add('📝  Редактор')
        self.setup_editor_tab()

        accounts_tab = self.tabs.add('🗂  Аккаунты')
        accounts_tab.configure(fg_color=COLORS['bg'])
        self.profile_manager = ProfileManager(accounts_tab, self)

        self.cards = []
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._restore_state()
        if not self.cards:
            self.add_book()
        self._relayout_hidden_grid()

    def apply_theme(self):
        global CURRENT_THEME, COLORS
        CURRENT_THEME = self.theme_var.get()
        COLORS = dict(THEMES[CURRENT_THEME])
        ctk.set_appearance_mode(COLORS['ctk_mode'])
        # Перезапускаем окно для применения темы
        self._save_state()
        self.destroy()
        new_app = App()
        new_app.mainloop()

    def _new_chrome_driver(self, opts):
        """Создаёт Chrome-драйвер. Окно сразу сворачивается, чтобы не перекрывать
        остальные окна пользователя и не выхватывать фокус во время работы скрипта
        (Chrome при этом продолжает нормально работать в свёрнутом виде)."""
        driver_path = get_driver_path()
        driver = (webdriver.Chrome(options=opts) if driver_path == '__AUTO__'
                  else webdriver.Chrome(service=Service(driver_path), options=opts))
        try:
            driver.minimize_window()
        except Exception:
            pass
        return driver

    def get_stealth_options(self, p_name, headless=False):
        clean_chrome_profile_lock(p_name)
        opts = webdriver.ChromeOptions()
        opts.add_argument(f'--user-data-dir={os.path.abspath("chrome_profiles/" + p_name)}')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_experimental_option('excludeSwitches', ['enable-automation'])
        opts.add_experimental_option('useAutomationExtension', False)
        opts.set_capability('unhandledPromptBehavior', 'accept')
        if headless:
            opts.add_argument('--headless=new')
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-gpu')
            opts.add_argument('--window-size=1920,1080')
        prefs = {"profile.default_content_setting_values.clipboard": 1}
        opts.add_experimental_option("prefs", prefs)
        return opts

    def add_nav_btn(self, text, color, cmd):
        ctk.CTkButton(self.sidebar, text=text, fg_color=color, font=('Segoe UI', 12), anchor='w', height=36, corner_radius=6, command=cmd).pack(padx=15, pady=4, fill='x')

    def add_nav_btn_to(self, parent, text, color, cmd):
        ctk.CTkButton(parent, text=text, fg_color=color, font=('Segoe UI', 12), anchor='w', height=36, corner_radius=6, command=cmd).pack(padx=12, pady=3, fill='x')

    def add_check(self, text):
        cb = ctk.CTkCheckBox(self.sidebar, text=text, font=('Segoe UI', 11), fg_color=COLORS['accent_green'],
                              text_color=COLORS['text_main'])
        cb.pack(padx=20, anchor='w', pady=2)
        return cb

    def _add_check_to(self, parent, text):
        cb = ctk.CTkCheckBox(parent, text=text, font=('Segoe UI', 11), fg_color=COLORS['accent_green'],
                              text_color=COLORS['text_main'], checkmark_color=COLORS['bg'])
        cb.pack(padx=20, anchor='w', pady=2)
        return cb

    def open_accounts_tab(self):
        """Переключает на встроенную вкладку 'Аккаунты' вместо отдельного окна."""
        self.tabs.set('🗂  Аккаунты')
        self.profile_manager.refresh()
        self.profile_manager._rebuild_accounts_tab()

    def update_menus(self):
        self.profiles = load_json(PROFILES_FILE, ['Default'])
        for c in self.cards:
            c.selected_profiles = [p for p in c.selected_profiles if p in self.profiles]
            if not c.selected_profiles:
                c.selected_profiles = list(self.profiles)
            c.acc_btn.configure(text=c._accounts_label())

    def add_book(self):
        c = TaskCard(self.task_list, len(self.cards) + 1, self.remove_book, self)
        self.cards.append(c)
        self._relayout_book_grid()

    def remove_book(self, c):
        if self._book_grid_open_card is c:
            self._book_grid_open_card = None
        c.destroy()
        self.cards.remove(c)
        self._relayout_book_grid()
        self._relayout_hidden_grid()

    def hide_book(self, card):
        """Скрывает книгу из раздела «Книги» и переносит её в «Скрытые книги».
        На вкладку «Редактор» (уже опубликованные главы) это не влияет —
        она читает данные с диска независимо от карточек книг."""
        card.is_hidden = True
        if self._book_grid_open_card is card:
            self._book_grid_open_card = None
        self._relayout_book_grid()
        self._relayout_hidden_grid()
        self._save_state()
        self.log(f'🙈 Книга "{card.title_lbl.cget("text").split(" ✓")[0].strip()}" скрыта из списка книг.')

    def unhide_book(self, card):
        """Возвращает книгу из «Скрытых книг» обратно в раздел «Книги»."""
        card.is_hidden = False
        self._relayout_book_grid()
        self._relayout_hidden_grid()
        self._save_state()
        self.log(f'👁 Книга "{card.title_lbl.cget("text").split(" ✓")[0].strip()}" возвращена в список книг.')

    def _relayout_book_grid(self):
        """Расставляет карточки книг сеткой по 3 в ряд. Если сейчас открыта
        детальная карточка (настройки на весь экран) — она разворачивается
        на всю ширину, остальные карточки скрыты. Скрытые книги (is_hidden)
        в эту сетку не попадают — они показаны в разделе «Скрытые книги»."""
        for c in self.cards:
            c.grid_forget()
        visible_cards = [c for c in self.cards if not getattr(c, 'is_hidden', False)]
        if self._book_grid_open_card is not None and self._book_grid_open_card in visible_cards:
            card = self._book_grid_open_card
            card.set_grid_mode(True)
            card.grid(row=0, column=0, columnspan=3, sticky='new', padx=8, pady=8)
        else:
            row = col = 0
            for c in visible_cards:
                c.set_grid_mode(False)
                c.grid(row=row, column=col, sticky='new', padx=8, pady=8)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
        # ВАЖНО: это и есть причина бага "клик по книге ничего не показывает,
        # помогает только переключение вкладки". CustomTkinter планирует
        # перерисовку после grid()/grid_remove() асинхронно и иногда не успевает
        # её выполнить до возврата из обработчика клика <Button-1> — виджет
        # физически появляется/меняется, но на экране это не отражается, пока
        # что-то ещё (например, смена вкладки) не заставит Tk перерисовать
        # окно целиком. Одного update_idletasks() иногда недостаточно, потому
        # что CTkScrollableFrame пересчитывает scrollregion своего внутреннего
        # canvas тоже отложенно (через after_idle) — сам виджет вроде бы
        # "готов", а видимая область прокрутки/канвас ещё нет. Поэтому здесь
        # форсируем это в несколько шагов: полный update() (обрабатывает вообще
        # все отложенные события, не только геометрию), затем ещё раз дожимаем
        # idle-задачи у самого списка книг и у его внутреннего canvas.
        self.update_idletasks()
        self.update()
        try:
            self.task_list.update_idletasks()
            self.task_list._parent_canvas.update_idletasks()
            self.task_list._parent_canvas.configure(
                scrollregion=self.task_list._parent_canvas.bbox('all'))
        except Exception:
            pass
        # Подстраховка: если что-то из этого всё же не успело отрисоваться
        # синхронно, повторяем ту же перерисовку ещё раз на следующем тике
        # цикла событий Tk — это не блокирует интерфейс, просто "добивает"
        # кадр сразу после текущего.
        self.after(0, self._force_book_grid_redraw)

    def _force_book_grid_redraw(self):
        """Доп. перерисовка на следующем тике event loop — см. комментарий
        в _relayout_book_grid() про баг с пропадающим после клика меню."""
        try:
            self.task_list.update_idletasks()
            self.task_list._parent_canvas.update_idletasks()
            self.task_list._parent_canvas.configure(
                scrollregion=self.task_list._parent_canvas.bbox('all'))
        except Exception:
            pass

    def _relayout_hidden_grid(self):
        """Строит плитки для скрытых книг во вкладке «Скрытые книги».
        Это лёгкие независимые виджеты (не сами TaskCard — их нельзя
        физически перенести в другой контейнер), которые лишь показывают
        обложку/название и кнопку возврата книги в общий список."""
        for w in self.hidden_list.winfo_children():
            w.destroy()
        hidden_cards = [c for c in self.cards if getattr(c, 'is_hidden', False)]
        if not hidden_cards:
            ctk.CTkLabel(self.hidden_list, text='Здесь появятся книги, которые вы скроете из раздела «Книги».',
                         text_color=COLORS['text_dim'], justify='center').pack(pady=40)
            return
        row = col = 0
        for card in hidden_cards:
            tile = ctk.CTkFrame(self.hidden_list, fg_color=COLORS['card'], corner_radius=10,
                                 border_width=1, border_color=COLORS['card_border'])
            tile.grid(row=row, column=col, sticky='new', padx=8, pady=8)

            cover_lbl = ctk.CTkLabel(tile, text='📖', font=('Arial', 26), width=120, height=160,
                                      fg_color=COLORS['entry_bg'], corner_radius=8,
                                      text_color=COLORS['label_dim'])
            cached_img = getattr(card, '_ctk_img_cache', None)
            if cached_img:
                cover_lbl.configure(image=cached_img, text='')
            cover_lbl.pack(padx=14, pady=(14, 10))

            title_text = card.title_lbl.cget('text').split(' ✓')[0].strip()
            ctk.CTkLabel(tile, text=title_text, font=('Segoe UI', 12, 'bold'),
                         anchor='center', justify='center', wraplength=150).pack(fill='x', padx=10)

            ctk.CTkButton(tile, text='↩ Вернуть в список', fg_color=COLORS['accent_green'],
                          hover_color=COLORS['hover_green'], height=28,
                          command=lambda c=card: self.unhide_book(c)).pack(pady=(10, 14), padx=14, fill='x')

            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _open_book_detail(self, card):
        """Открывает настройки одной книги на весь экран (клик по карточке в сетке)."""
        self._book_grid_open_card = card
        self._relayout_book_grid()

    def _show_book_grid(self):
        """Возвращает к сетке всех книг (кнопка «← Все книги»)."""
        self._book_grid_open_card = None
        self._relayout_book_grid()

    def log(self, m):
        self.log_box.insert('end', f'[{time.strftime("%H:%M:%S")}] {m}\n')
        self.log_box.see('end')

    def stop_all(self):
        STOP_EVENT.set()
        self.log('🛑 ОСТАНОВКА')

    # ==================== ВКЛАДКА "РЕДАКТОР" ====================
    # Просмотр/редактирование уже переведённых глав, откат правок, ручная публикация
    # на RuLate и анализ глав на предмет "непереведённых" китайских иероглифов.

    def setup_editor_tab(self):
        self.editor_container = ctk.CTkFrame(self.editor_tab, fg_color='transparent')
        self.editor_container.pack(fill='both', expand=True, padx=15, pady=15)
        self.editor_current_view = 'books'      # 'books' | 'chapters' | 'chapter'
        self.editor_current_book_id = None
        self._editor_book_covers = {}            # book_id -> CTkImage (кэш обложек)
        self.render_editor_books_view()
        self._editor_autorefresh_tick()

    def _clear_editor_container(self):
        for w in self.editor_container.winfo_children():
            w.destroy()

    def _editor_autorefresh_tick(self):
        """Автообновление вкладки «Редактор» без кнопки — сама подтягивает новые
        книги/главы по мере их появления, не сбрасывая открытую для правки главу."""
        try:
            if self.tabs.get() == '📝  Редактор':
                if self.editor_current_view == 'books':
                    self.render_editor_books_view(keep_covers=True)
                elif self.editor_current_view == 'chapters' and self.editor_current_book_id:
                    self.refresh_editor_chapters_list(self.editor_current_book_id)
                # editor_current_view == 'chapter' — открыт текст главы, ничего не трогаем,
                # чтобы не потерять несохранённые правки пользователя
        except Exception:
            pass
        self.after(4000, self._editor_autorefresh_tick)

    def _load_editor_cover(self, book_id, img_url, label_widget):
        try:
            res = requests.get(img_url, timeout=6)
            img = Image.open(BytesIO(res.content))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 160))
            self._editor_book_covers[book_id] = ctk_img
            self.after(0, lambda: label_widget.configure(image=ctk_img, text='') if label_widget.winfo_exists() else None)
        except Exception:
            pass

    def render_editor_books_view(self, keep_covers=True):
        self.editor_current_view = 'books'
        self.editor_current_book_id = None
        self._clear_editor_container()
        top = ctk.CTkFrame(self.editor_container, fg_color='transparent')
        top.pack(fill='x', pady=(0, 12))
        ctk.CTkLabel(top, text='📝 Редактор переводов', font=('Segoe UI', 17, 'bold')).pack(side='left')

        books = list_translated_books()
        if not books:
            ctk.CTkLabel(self.editor_container,
                         text='Пока нет сохранённых переводов.\nКак только скрипт переведёт первую главу — она появится здесь.',
                         text_color=COLORS['text_dim'], justify='center').pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(self.editor_container, fg_color='transparent')
        scroll.pack(fill='both', expand=True)
        for col_i in range(3):
            scroll.grid_columnconfigure(col_i, weight=1, uniform='editorcol')

        row = col = 0
        for b in books:
            open_cb = lambda e=None, bid=b['id']: self.render_editor_chapters_view(bid)
            tile = ctk.CTkFrame(scroll, fg_color=COLORS['card'], corner_radius=10, border_width=1,
                                border_color=COLORS['card_border'], cursor='hand2')
            tile.grid(row=row, column=col, sticky='new', padx=8, pady=8)
            tile.bind('<Button-1>', open_cb)

            cover_lbl = ctk.CTkLabel(tile, text='📖', font=('Arial', 26), width=120, height=160,
                                      fg_color=COLORS['entry_bg'], corner_radius=8,
                                      text_color=COLORS['label_dim'], cursor='hand2')
            cover_lbl.pack(padx=14, pady=(14, 10))
            cover_lbl.bind('<Button-1>', open_cb)
            cached = self._editor_book_covers.get(b['id']) if keep_covers else None
            if cached:
                cover_lbl.configure(image=cached, text='')
            elif b.get('cover_url'):
                threading.Thread(target=self._load_editor_cover, args=(b['id'], b['cover_url'], cover_lbl), daemon=True).start()

            title_lbl = ctk.CTkLabel(tile, text=b['title'], font=('Segoe UI', 12, 'bold'), anchor='center',
                                      justify='center', wraplength=150, cursor='hand2')
            title_lbl.pack(fill='x', padx=10)
            title_lbl.bind('<Button-1>', open_cb)
            count_lbl = ctk.CTkLabel(tile, text=f"{b['count']} глав", text_color=COLORS['text_dim'],
                                      font=('Segoe UI', 10), cursor='hand2')
            count_lbl.pack(pady=(2, 14))
            count_lbl.bind('<Button-1>', open_cb)

            col += 1
            if col >= 3:
                col = 0
                row += 1

    def render_editor_chapters_view(self, book_id):
        self.editor_current_view = 'chapters'
        self.editor_current_book_id = book_id
        self._clear_editor_container()
        meta = load_json(os.path.join(TRANSLATIONS_DIR, book_id, 'meta.json'), {})

        top = ctk.CTkFrame(self.editor_container, fg_color='transparent')
        top.pack(fill='x', pady=(0, 12))
        ctk.CTkButton(top, text='← Назад', width=90, fg_color=COLORS['card'],
                      command=self.render_editor_books_view).pack(side='left')
        ctk.CTkLabel(top, text=f"📖 {meta.get('title', book_id)}", font=('Segoe UI', 15, 'bold')).pack(side='left', padx=15)
        ctk.CTkButton(top, text='🔍 Анализ ошибок (иероглифы)', fg_color=COLORS['red'],
                      command=lambda: self.run_cjk_analysis(book_id)).pack(side='right')

        body = ctk.CTkFrame(self.editor_container, fg_color='transparent')
        body.pack(fill='both', expand=True)
        body.grid_columnconfigure(0, weight=1, minsize=260)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self.editor_chapters_frame = ctk.CTkScrollableFrame(body, fg_color=COLORS['card'])
        self.editor_chapters_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        self._populate_editor_chapters_list(book_id)

        self.editor_detail_frame = ctk.CTkFrame(body, fg_color=COLORS['card'])
        self.editor_detail_frame.grid(row=0, column=1, sticky='nsew')
        ctk.CTkLabel(self.editor_detail_frame, text='← Выберите главу слева, чтобы открыть текст',
                     text_color=COLORS['text_dim']).pack(expand=True)

    def _populate_editor_chapters_list(self, book_id):
        for w in self.editor_chapters_frame.winfo_children():
            w.destroy()
        chapters = list_book_chapters(book_id)
        if not chapters:
            ctk.CTkLabel(self.editor_chapters_frame, text='Нет сохранённых глав', text_color=COLORS['text_dim']).pack(pady=20)
        for ch in chapters:
            flags = ''
            if ch.get('is_paid'): flags += ' 💰'
            if ch.get('is_delayed'): flags += ' ⏳'
            flags += ' ✅' if ch.get('posted') else ' ⚪'
            title_disp = (ch.get('title') or '').strip()[:26]
            btn = ctk.CTkButton(self.editor_chapters_frame, text=f"#{ch['num']}  {title_disp}{flags}",
                                anchor='w', fg_color='transparent', hover_color=COLORS['hover_green'],
                                text_color=COLORS['text_main'], height=32,
                                command=lambda c=ch['num']: self.render_editor_chapter(book_id, c))
            btn.pack(fill='x', pady=1, padx=2)

    def refresh_editor_chapters_list(self, book_id):
        """Вызывается автообновлением — обновляет только список глав слева,
        не трогая открытую справа главу (если она есть), чтобы не потерять правки."""
        if not hasattr(self, 'editor_chapters_frame') or not self.editor_chapters_frame.winfo_exists():
            return
        self._populate_editor_chapters_list(book_id)

    def render_editor_chapter(self, book_id, chapter_num, highlight_cjk=True):
        self.editor_current_view = 'chapter'
        for w in self.editor_detail_frame.winfo_children():
            w.destroy()
        ch = load_book_chapter(book_id, chapter_num)
        if not ch:
            ctk.CTkLabel(self.editor_detail_frame, text='Глава не найдена').pack(expand=True)
            return

        top = ctk.CTkFrame(self.editor_detail_frame, fg_color='transparent')
        top.pack(fill='x', padx=14, pady=(14, 6))
        title_ent = ctk.CTkEntry(top, height=34, font=('Segoe UI', 13, 'bold'))
        title_ent.insert(0, ch.get('title', ''))
        title_ent.pack(fill='x')

        flags_parts = []
        if ch.get('is_paid'): flags_parts.append('💰 Платная')
        if ch.get('is_delayed'): flags_parts.append('⏳ Отложка')
        flags_parts.append('✅ Опубликована на RuLate' if ch.get('posted') else '⚪ Ещё не опубликована')
        ctk.CTkLabel(self.editor_detail_frame, text=f"Глава #{chapter_num}  •  " + '  '.join(flags_parts),
                     text_color=COLORS['text_dim'], font=('Segoe UI', 11)).pack(anchor='w', padx=14, pady=(0, 8))

        txt = ctk.CTkTextbox(self.editor_detail_frame, font=('Segoe UI', 12), wrap='word',
                              fg_color=COLORS['entry_bg'], border_width=1, border_color=COLORS['card_border'])
        txt.pack(fill='both', expand=True, padx=14, pady=(0, 10))
        txt.insert('1.0', ch.get('text', ''))
        if highlight_cjk:
            self._highlight_cjk_in_textbox(txt)
            txt.bind('<KeyRelease>', lambda e: self._highlight_cjk_in_textbox(txt))

        self.editor_current_book_id = book_id
        self.editor_current_chapter_num = chapter_num
        self.editor_current_textbox = txt
        self.editor_current_title_ent = title_ent

        btns = ctk.CTkFrame(self.editor_detail_frame, fg_color='transparent')
        btns.pack(fill='x', padx=14, pady=(0, 14))

        btns_top = ctk.CTkFrame(btns, fg_color='transparent')
        btns_top.pack(fill='x', pady=(0, 8))
        ctk.CTkButton(btns_top, text='💾 Сохранить', fg_color=COLORS['accent_green'], hover_color=COLORS['hover_green'],
                      command=lambda: self.save_editor_chapter(book_id, chapter_num)).pack(side='left', padx=(0, 8))
        ctk.CTkButton(btns_top, text='↩ Откатить к исходному', fg_color=COLORS['card'], border_width=1, border_color=COLORS['card_border'],
                      command=lambda: self.revert_editor_chapter(book_id, chapter_num)).pack(side='left')

        btns_bottom = ctk.CTkFrame(btns, fg_color='transparent')
        btns_bottom.pack(fill='x')
        ctk.CTkButton(btns_bottom, text='📖 Добавить на RuLate', fg_color=COLORS['accent_green'], hover_color=COLORS['hover_green'],
                      command=lambda: self.push_chapter_to_rulate(book_id, chapter_num)).pack(side='left', fill='x', expand=True, padx=(0, 8))
        ctk.CTkButton(btns_bottom, text='🗑 Удалить с RuLate', fg_color=COLORS['card'], border_width=1,
                      border_color=COLORS['red'], text_color=COLORS['red'], hover_color=COLORS['red'],
                      command=lambda: self.delete_chapter_from_rulate(book_id, chapter_num)).pack(side='left', fill='x', expand=True)

    def save_editor_chapter(self, book_id, chapter_num):
        ch = load_book_chapter(book_id, chapter_num)
        if not ch:
            return
        ch['title'] = self.editor_current_title_ent.get().strip()
        ch['text'] = self.editor_current_textbox.get('1.0', 'end-1c')
        ch['updated_at'] = datetime.now().isoformat(timespec='seconds')
        save_book_chapter(book_id, chapter_num, ch)
        self.log(f'💾 Глава #{chapter_num} сохранена в редакторе')

    def revert_editor_chapter(self, book_id, chapter_num):
        ch = load_book_chapter(book_id, chapter_num)
        if not ch:
            return
        if not messagebox.askyesno('Откат правок', f'Вернуть главу #{chapter_num} к исходному тексту перевода (до ваших правок)?'):
            return
        ch['text'] = ch.get('original_text', ch.get('text', ''))
        save_book_chapter(book_id, chapter_num, ch)
        self.render_editor_chapter(book_id, chapter_num)
        self.log(f'↩ Глава #{chapter_num} откачена к исходному тексту перевода')

    def _guess_profile_for_book(self, rulate_url):
        """Пытается определить, каким Chrome-профилем публиковалась эта книга —
        сперва из истории задач, потом среди открытых карточек книг в разделе Книги."""
        h = load_json(HISTORY_FILE, {})
        entry = h.get(rulate_url)
        if entry and entry.get('profile'):
            return entry['profile']
        for c in getattr(self, 'cards', []):
            try:
                if c.ent_rulate.get().strip() == rulate_url:
                    if c.selected_profiles:
                        return list(c.selected_profiles)[0]
                    if c.prof_var.get():
                        return c.prof_var.get()
            except Exception:
                continue
        return None

    def push_chapter_to_rulate(self, book_id, chapter_num):
        # Сохраняем несохранённые правки перед публикацией
        self.save_editor_chapter(book_id, chapter_num)
        ch = load_book_chapter(book_id, chapter_num)
        meta = load_json(os.path.join(TRANSLATIONS_DIR, book_id, 'meta.json'), {})
        rulate_url = meta.get('rulate_url')
        if not ch or not rulate_url:
            messagebox.showerror('Ошибка', 'Не найдена ссылка RuLate для этой книги.')
            return
        profile = self._guess_profile_for_book(rulate_url)
        if not profile:
            messagebox.showerror('Ошибка', 'Не удалось определить Chrome-профиль для публикации.\n'
                                            'Откройте книгу в разделе "Книги" хотя бы раз, чтобы скрипт запомнил профиль.')
            return
        if not messagebox.askyesno('Публикация', f'Опубликовать главу #{chapter_num} на RuLate профилем "{profile}"?'):
            return
        self.log(f'📖 Публикую главу #{chapter_num} на RuLate вручную из редактора (профиль {profile})...')
        threading.Thread(target=self._manual_rulate_publish_worker,
                          args=(book_id, chapter_num, rulate_url, dict(ch), profile), daemon=True).start()

    def _manual_rulate_publish_worker(self, book_id, chapter_num, rulate_url, ch, profile):
        driver = None
        try:
            opts = self.get_stealth_options(profile)
            driver = self._new_chrome_driver(opts)
            wait = WebDriverWait(driver, 20)
            ok = self._post_chapter_to_rulate(driver, wait, rulate_url, ch.get('title', ''), ch.get('text', ''),
                                               ch.get('is_paid', False), ch.get('is_delayed', False), p_name=profile)
            if ok:
                ch['posted'] = True
                save_book_chapter(book_id, chapter_num, ch)
                self.log(f'✅ Глава #{chapter_num} опубликована на RuLate вручную.')
                self.after(0, lambda: messagebox.showinfo('Готово', f'Глава #{chapter_num} опубликована на RuLate.'))
                self.after(0, lambda: self.render_editor_chapter(book_id, chapter_num))
            else:
                self.log(f'❌ Не удалось опубликовать главу #{chapter_num} на RuLate.')
                self.after(0, lambda: messagebox.showerror('Ошибка', f'Не удалось опубликовать главу #{chapter_num}. Смотрите логи.'))
        except Exception as e:
            self.log(f'Ошибка ручной публикации главы: {e}')
        finally:
            if driver:
                try: driver.quit()
                except: pass

    def _manual_promo_publish_worker(self, rulate_url, profile):
        """Публикует главу-акцию (PROMO_CHAPTER_TITLE / PROMO_CHAPTER_TEXT) в фоновом
        потоке — вызывается кнопкой "🎁 Добавить акцию" в карточке книги. Это не
        глава перевода, поэтому в chapters/*.json она не сохраняется — только
        публикуется на RuLate как обычная бесплатная, не отложенная глава."""
        driver = None
        try:
            opts = self.get_stealth_options(profile)
            driver = self._new_chrome_driver(opts)
            wait = WebDriverWait(driver, 20)
            ok = self._post_chapter_to_rulate(driver, wait, rulate_url,
                                               PROMO_CHAPTER_TITLE, PROMO_CHAPTER_TEXT,
                                               is_paid=False, is_delayed=False, p_name=profile)
            if ok:
                self.log(f'✅ Глава-акция опубликована на RuLate (профиль {profile}).')
                self.after(0, lambda: messagebox.showinfo('Готово', 'Глава-акция опубликована на RuLate.'))
            else:
                self.log(f'❌ Не удалось опубликовать главу-акцию (профиль {profile}).')
                self.after(0, lambda: messagebox.showerror('Ошибка', 'Не удалось опубликовать главу-акцию. Смотрите логи.'))
        except Exception as e:
            self.log(f'Ошибка публикации главы-акции: {e}')
        finally:
            if driver:
                try: driver.quit()
                except: pass

    def delete_chapter_from_rulate(self, book_id, chapter_num):
        """Удаляет главу с сайта RuLate: открывает страницу книги, находит главу
        по названию в таблице «Оглавление» (нажимая карандашик ✎ «Редактировать»),
        затем нажимает появившуюся кнопку «Удалить»."""
        ch = load_book_chapter(book_id, chapter_num)
        meta = load_json(os.path.join(TRANSLATIONS_DIR, book_id, 'meta.json'), {})
        rulate_url = meta.get('rulate_url')
        if not ch or not rulate_url:
            messagebox.showerror('Ошибка', 'Не найдена ссылка RuLate для этой книги.')
            return
        title = (ch.get('title') or '').strip()
        if not title:
            messagebox.showerror('Ошибка', 'У главы нет названия — по нему скрипт ищет главу на RuLate.')
            return
        profile = self._guess_profile_for_book(rulate_url)
        if not profile:
            messagebox.showerror('Ошибка', 'Не удалось определить Chrome-профиль для удаления.\n'
                                            'Откройте книгу в разделе "Книги" хотя бы раз, чтобы скрипт запомнил профиль.')
            return
        if not messagebox.askyesno('Удаление главы',
                                    f'Удалить главу #{chapter_num} "{title}" с RuLate профилем "{profile}"?\n'
                                    f'Это действие нельзя отменить.'):
            return
        self.log(f'🗑 Удаляю главу #{chapter_num} с RuLate вручную из редактора (профиль {profile})...')
        threading.Thread(target=self._manual_rulate_delete_worker,
                          args=(book_id, chapter_num, rulate_url, title, profile), daemon=True).start()

    def _manual_rulate_delete_worker(self, book_id, chapter_num, rulate_url, title, profile):
        driver = None
        try:
            opts = self.get_stealth_options(profile)
            driver = self._new_chrome_driver(opts)
            wait = WebDriverWait(driver, 20)
            ok = self._delete_chapter_from_rulate(driver, wait, rulate_url, title)
            if ok:
                ch = load_book_chapter(book_id, chapter_num)
                if ch:
                    ch['posted'] = False
                    save_book_chapter(book_id, chapter_num, ch)
                self.log(f'✅ Глава #{chapter_num} удалена с RuLate.')
                self.after(0, lambda: messagebox.showinfo('Готово', f'Глава #{chapter_num} удалена с RuLate.'))
                self.after(0, lambda: self.render_editor_chapter(book_id, chapter_num))
            else:
                self.log(f'❌ Не удалось удалить главу #{chapter_num} с RuLate.')
                self.after(0, lambda: messagebox.showerror('Ошибка', f'Не удалось удалить главу #{chapter_num}. Смотрите логи.'))
        except Exception as e:
            self.log(f'Ошибка ручного удаления главы: {e}')
        finally:
            if driver:
                try: driver.quit()
                except: pass

    def run_cjk_analysis(self, book_id):
        chapters = list_book_chapters(book_id)
        found = []
        for ch in chapters:
            text = ch.get('text', '') or ''
            matches = CJK_PATTERN.findall(text)
            if matches:
                found.append((ch.get('num'), ch.get('title', ''), len(matches)))
        self.log(f'🔍 Анализ ошибок: ' + (f'иероглифы найдены в {len(found)} главах' if found else 'иероглифов не найдено — всё чисто'))

        report_win = ctk.CTkToplevel(self)
        report_win.title('Отчёт: анализ ошибок')
        report_win.geometry('560x460')
        report_win.configure(fg_color=COLORS['bg'])
        # Окно иначе может открыться позади главного окна или свернуться вместе
        # с ним — принудительно поднимаем его наверх и даём фокус.
        report_win.attributes('-topmost', True)
        report_win.after(10, report_win.lift)
        report_win.after(10, report_win.focus_force)
        report_win.after(400, lambda: report_win.attributes('-topmost', False))
        if not found:
            ctk.CTkLabel(report_win, text='✅ Китайские иероглифы не найдены\nни в одной сохранённой главе.',
                         font=('Segoe UI', 14), justify='center').pack(expand=True)
            return
        ctk.CTkLabel(report_win, text=f'⚠ Найдены иероглифы в {len(found)} главах:',
                     font=('Segoe UI', 14, 'bold'), text_color=COLORS['red']).pack(anchor='w', padx=14, pady=(14, 6))

        scroll = ctk.CTkScrollableFrame(report_win, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=14, pady=(0, 14))
        for num, title, cnt in found:
            row = ctk.CTkFrame(scroll, fg_color=COLORS['card'], corner_radius=8,
                               border_width=1, border_color=COLORS['card_border'])
            row.pack(fill='x', pady=3)
            info = ctk.CTkFrame(row, fg_color='transparent')
            info.pack(side='left', fill='x', expand=True, padx=12, pady=8)
            ctk.CTkLabel(info, text=f"Глава #{num}  «{(title or '')[:34]}»", anchor='w',
                        font=('Segoe UI', 12, 'bold')).pack(fill='x')
            ctk.CTkLabel(info, text=f'{cnt} иероглиф(ов)', anchor='w', text_color=COLORS['red'],
                        font=('Segoe UI', 11)).pack(fill='x')
            ctk.CTkButton(row, text='Перейти к главе →', width=140, fg_color=COLORS['accent_green'],
                         hover_color=COLORS['hover_green'],
                         command=lambda n=num, w=report_win: self._jump_to_cjk_chapter(book_id, n, w)
                         ).pack(side='right', padx=12, pady=8)

    def _jump_to_cjk_chapter(self, book_id, chapter_num, report_win):
        """Открывает главу в редакторе (с подсветкой иероглифов в тексте) и закрывает окно отчёта."""
        try:
            report_win.destroy()
        except Exception:
            pass
        self.render_editor_chapters_view(book_id)
        self.render_editor_chapter(book_id, chapter_num, highlight_cjk=True)

    def _highlight_cjk_in_textbox(self, textbox):
        """Подсвечивает все китайские иероглифы в тексте CTkTextbox жёлтым фоном,
        чтобы их было проще найти и вручную поправить."""
        # CTkTextbox не прокидывает tag_add/tag_config напрямую — они есть у
        # внутреннего tkinter.Text виджета (_textbox).
        tk_text = getattr(textbox, '_textbox', textbox)
        try:
            tk_text.tag_remove('cjk_highlight', '1.0', 'end')
            tk_text.tag_config('cjk_highlight', background='#F5C518', foreground='#1a1a1a')
        except Exception:
            return
        content = textbox.get('1.0', 'end-1c')
        for m in CJK_PATTERN.finditer(content):
            start_idx = f'1.0+{m.start()}c'
            end_idx = f'1.0+{m.end()}c'
            try:
                tk_text.tag_add('cjk_highlight', start_idx, end_idx)
            except Exception:
                pass

    def setup_profile_tab(self):
        top_f = ctk.CTkFrame(self.profile_tab, fg_color='transparent')
        top_f.pack(fill='x', padx=20, pady=20)
        self.prof_url_ent = ctk.CTkEntry(top_f, placeholder_text='Ссылка на профиль RuLate', height=35)
        self.prof_url_ent.pack(side='left', fill='x', expand=True, padx=(0, 10))
        ctk.CTkButton(top_f, text='🔄 Обновить', fg_color=COLORS['accent_green'], hover_color=COLORS['hover_green'],
                      width=110, height=35, font=('Segoe UI', 12, 'bold'),
                      command=self.refresh_profile_stats).pack(side='right', padx=(0, 8))
        ctk.CTkButton(top_f, text='СКАНИРОВАТЬ', fg_color=COLORS['accent_green'],
                      height=35, command=self.search_profile_books).pack(side='right')
        self.prof_results = ctk.CTkScrollableFrame(self.profile_tab, fg_color=COLORS['scrollable'])
        self.prof_results.pack(fill='both', expand=True, padx=20, pady=10)
        # Храним данные карточек для обновления
        self._prof_book_data = []  # список (frame, name, link, stat_label)

    def refresh_profile_stats(self):
        """Обновляет статистику (количество глав) для всех книг в табе Профиль."""
        if not self._prof_book_data:
            self.log('ℹ️ Нет книг для обновления. Сначала нажмите СКАНИРОВАТЬ.')
            return
        self.log('🔄 Обновляю статистику книг...')
        threading.Thread(target=self._refresh_stats_worker, daemon=True).start()

    def _refresh_stats_worker(self):
        driver = None
        try:
            opts = self.get_stealth_options('Scanner_Temp')
            opts.add_argument('--headless')
            driver = self._new_chrome_driver(opts)
            wait = WebDriverWait(driver, 20)
            for item in self._prof_book_data:
                stat_label = item.get('stat_label')
                link = item.get('link', '')
                if not link or stat_label is None:
                    continue
                try:
                    driver.get(link)
                    time.sleep(3)
                    # Считаем количество глав в таблице
                    rows = driver.find_elements(By.CSS_SELECTOR, 'table.translation tr')
                    ch_count = max(0, len(rows) - 1)
                    self.after(0, lambda lbl=stat_label, c=ch_count: lbl.configure(
                        text=f'📖 Глав: {c}', text_color=COLORS['accent_green']
                    ))
                    self.log(f'✅ {item.get("name", link)[:40]} — {ch_count} глав')
                except Exception as e:
                    self.log(f'⚠️ Ошибка обновления {link}: {e}')
                    self.after(0, lambda lbl=stat_label: lbl.configure(
                        text='❌ Ошибка', text_color=COLORS['red']
                    ))
        except Exception as e:
            self.log(f'Ошибка обновления статистики: {e}')
        finally:
            if driver:
                try: driver.quit()
                except: pass
            self.log('✅ Статистика обновлена.')

    def search_profile_books(self):
        url = self.prof_url_ent.get().strip()
        if url:
            threading.Thread(target=self.scan_profile_worker, args=(url,), daemon=True).start()

    def scan_profile_worker(self, url):
        self.log('🔍 Сканирую профиль...')
        for child in self.prof_results.winfo_children():
            child.destroy()
        self._prof_book_data = []  # сбрасываем при новом сканировании
        try:
            opts = self.get_stealth_options('Scanner_Temp')
            opts.add_argument('--headless')
            driver = self._new_chrome_driver(opts)
            driver.get(url)
            time.sleep(3)
            items = driver.find_elements(By.CSS_SELECTOR, 'table.projects-list tr')[1:]
            for item in items:
                try:
                    title_a = item.find_element(By.CSS_SELECTOR, 'td.t a')
                    name = title_a.text.strip()
                    link = title_a.get_attribute('href')
                    img = item.find_element(By.TAG_NAME, 'img').get_attribute('src')
                    # Получаем количество глав для каждой книги
                    try:
                        driver.get(link)
                        time.sleep(2)
                        rows = driver.find_elements(By.CSS_SELECTOR, 'table.translation tr')
                        ch_count = max(0, len(rows) - 1)
                        driver.back()
                        time.sleep(1)
                    except:
                        ch_count = 0
                    self.after(0, lambda n=name, l=link, i=img, c=ch_count: self.add_profile_book_ui(n, l, i, c))
                except:
                    continue
            driver.quit()
            self.log('✅ Сканирование завершено.')
        except Exception as e:
            self.log(f'Ошибка сканирования: {e}')

    def add_profile_book_ui(self, name, link, img_url, ch_count=0):
        f = ctk.CTkFrame(self.prof_results, fg_color=COLORS['card'], corner_radius=8,
                         border_width=1, border_color=COLORS['card_border'])
        f.pack(fill='x', pady=5, padx=5)
        try:
            res = requests.get(img_url, timeout=5)
            img = Image.open(BytesIO(res.content))
            ctk_img = ctk.CTkImage(img, size=(60, 90))
            ctk_img_lbl = ctk.CTkLabel(f, image=ctk_img, text='')
            ctk_img_lbl.pack(side='left', padx=10, pady=10)
        except:
            pass
        info_f = ctk.CTkFrame(f, fg_color='transparent')
        info_f.pack(side='left', fill='both', expand=True, padx=10)
        ctk.CTkLabel(info_f, text=name[:50], font=('Segoe UI', 12, 'bold'),
                     text_color=COLORS['text_main'], anchor='w').pack(anchor='w', pady=(12, 2))
        stat_label = ctk.CTkLabel(info_f,
                                  text=f'📖 Глав: {ch_count}' if ch_count else '📖 Глав: —',
                                  font=('Segoe UI', 11), text_color=COLORS['text_dim'], anchor='w')
        stat_label.pack(anchor='w')
        ctk.CTkButton(f, text='Редактор', width=100, fg_color='#3498db',
                      command=lambda: self.start_editor(link)).pack(side='right', padx=15)
        # Сохраняем для кнопки Обновить
        self._prof_book_data.append({'frame': f, 'name': name, 'link': link, 'stat_label': stat_label})

    def start_editor(self, book_url):
        threading.Thread(target=self.editor_scanner, args=(book_url,), daemon=True).start()

    def editor_scanner(self, url):
        self.log(f'🛠 Запуск редактора: {url}')
        driver = None
        report = []
        try:
            opts = self.get_stealth_options('Default')
            driver = self._new_chrome_driver(opts)
            wait = WebDriverWait(driver, 20)
            driver.get(url)
            ch1_link = wait.until(EC.presence_of_element_located((By.XPATH, "//tr[contains(., 'Глава 1')]//td[@class='t']/a")))
            driver.execute_script('arguments[0].click();', ch1_link)
            
            while not STOP_EVENT.is_set():
                time.sleep(2)
                read_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-info[title*='читать']")))
                driver.execute_script('arguments[0].click();', read_btn)
                time.sleep(3)
                content = driver.find_element(By.ID, "readpage").text
                curr_chapter_title = driver.title
                if has_chinese(content):
                    self.log(f'⚠️ Найдено в: {curr_chapter_title}')
                    report.append(curr_chapter_title)
                
                try:
                    next_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Следующая глава')]")
                    driver.execute_script('arguments[0].click();', next_btn)
                except:
                    self.log("🏁 Конец книги достигнут.")
                    break
            
            final_report = 'Отчет: Китайские иероглифы найдены в главах:\n' + ('\n'.join(report) if report else 'Нигде не найдены.')
            self.after(0, lambda: messagebox.showinfo('Результат редактора', final_report))
            driver.quit()
        except Exception as e:
            self.log(f'Ошибка редактора: {e}')
            if driver: driver.quit()

    def on_close(self):
        self._save_state()
        self.destroy()

    def _save_state(self):
        state = {
            'mode': self.mode_var.get(),
            'ai_wait': self.ai_wait_ent.get(),
            'skip_ai': self.skip_ai.get(),
            'skip_tom': self.skip_tom.get(),
            'skip_rul': self.skip_rul.get(),
            'headless': self.headless_mode.get(),
            'balance_notify': self.balance_notify_var.get(),
            'theme': CURRENT_THEME,
            'books': []
        }
        for c in self.cards:
            state['books'].append({
                'rulate': c.ent_rulate.get(),
                'tomato': c.ent_tomato.get(),
                'start': c.ent_start.get(),
                'limit': c.ent_limit.get(),
                'prompt': c.ent_prompt.get(),
                'is_paid': c.sw_paid.get(),
                'is_delayed': c.sw_otl.get(),
                'selected_profiles': c.selected_profiles,
                'is_saved': c.is_saved,
                'active': c.chk_active.get(),
                'is_hidden': getattr(c, 'is_hidden', False),
            })
        save_json(APP_STATE_FILE, state)

    def _restore_state(self):
        state = load_json(APP_STATE_FILE, None)
        if not state:
            return
        # Восстанавливаем настройки сайдбара
        if 'mode' in state:
            self.mode_var.set(state['mode'])
        if 'ai_wait' in state:
            self.ai_wait_ent.delete(0, tk.END)
            self.ai_wait_ent.insert(0, state['ai_wait'])
        if 'balance_notify' in state:
            if state['balance_notify']:
                self.balance_notify_cb.select()
            else:
                self.balance_notify_cb.deselect()
        for attr, key in [('skip_ai', 'skip_ai'), ('skip_tom', 'skip_tom'), ('skip_rul', 'skip_rul'), ('headless_mode', 'headless')]:
            if key in state:
                cb = getattr(self, attr)
                if state[key]:
                    cb.select()
                else:
                    cb.deselect()
        # Восстанавливаем книги
        for book in state.get('books', []):
            c = TaskCard(self.task_list, len(self.cards) + 1, self.remove_book, self)
            self.cards.append(c)
            if book.get('rulate'):
                c.ent_rulate.insert(0, book['rulate'])
            if book.get('tomato'):
                c.ent_tomato.insert(0, book['tomato'])
            if book.get('prompt'):
                c.ent_prompt.insert(0, book['prompt'])
            c.ent_start.delete(0, tk.END)
            c.ent_start.insert(0, book.get('start', '0'))
            c.ent_limit.delete(0, tk.END)
            c.ent_limit.insert(0, book.get('limit', '200'))
            if book.get('is_paid'):
                c.sw_paid.select()
            if book.get('is_delayed'):
                c.sw_otl.select()
            sel_prof = book.get('selected_profiles', [])
            if sel_prof:
                c.selected_profiles = [p for p in sel_prof if p in self.profiles] or list(self.profiles)
                c.acc_btn.configure(text=c._accounts_label())
            if book.get('active', True):
                c.chk_active.select()
            else:
                c.chk_active.deselect()
            if book.get('is_saved'):
                c.is_saved = True
                c.title_lbl.configure(text_color=COLORS['accent_green'])
                c.title_lbl_detail.configure(text_color=COLORS['accent_green'])
            c.is_hidden = bool(book.get('is_hidden', False))
            # Подгрузим метаданные из истории если есть ссылка
            if book.get('rulate') and 'tl.rulate.ru/book/' in book.get('rulate', ''):
                threading.Thread(target=c.fetch_metadata, args=(book['rulate'],), daemon=True).start()
        self._relayout_book_grid()

    def start_all(self):
        tasks = [c.get_data() for c in self.cards
                 if c.get_data()['is_saved'] and c.get_data()['active'] and not getattr(c, 'is_hidden', False)]
        if not tasks:
            messagebox.showwarning('Внимание', 'Нет активных сохраненных книг! (Нажми зеленую галочку ✓)')
            return
        
        STOP_EVENT.clear()
        kill_chrome_processes(wait_sec=1)
            
        wait_time = int(self.ai_wait_ent.get() or 60)
        s_ai, s_tom, s_rul = (self.skip_ai.get(), self.skip_tom.get(), self.skip_rul.get())
        headless = self.headless_mode.get()

        if self.mode_var.get() == 'sequential':
            threading.Thread(target=self.sequential_manager, args=(tasks, wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()
        else:
            for t in tasks:
                threading.Thread(target=self.worker, args=(t, t['profile'], wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()

    def sequential_manager(self, tasks, wait_time, s_ai, s_tom, s_rul, headless=False):
        last_profile = None  # профиль, которым была занята предыдущая книга
        for i, t in enumerate(tasks):
            if STOP_EVENT.is_set(): break
            start_profile = t['profile']
            if i > 0:
                # Переход к следующей книге: предыдущий Chrome мог не успеть до конца
                # закрыться (файлы-блокировки профиля освобождаются с задержкой), из-за
                # чего новый Chrome с тем же профилем открывался и тут же закрывался
                # или падал с ошибками (в т.ч. "Cannot redefine property"/"target window
                # already closed"). Поэтому перед стартом следующей книги гарантированно
                # "добиваем" Chrome и чистим блокировки профиля(ей), которые понадобятся
                # этой книге.
                self.log('--- Готовлюсь к переходу на следующую книгу: закрываю Chrome... ---')
                kill_chrome_processes(wait_sec=3)
                for prof in (t.get('selected_profiles') or [t['profile']]):
                    clean_chrome_profile_lock(prof)

                # Дополнительно: не стартуем новую книгу на том же самом Chrome-профиле,
                # которым только что пользовалась предыдущая книга — даже после
                # kill_chrome_processes и чистки блокировок ОС не всегда успевает до
                # конца освободить файлы профиля, и повторное открытие того же
                # user-data-dir сразу же может привести к падению. Если у новой книги
                # в ротации есть другой аккаунт — стартуем с него, а тот, что
                # использовался только что, оставляем "на потом".
                if start_profile == last_profile:
                    alt_pool = [p for p in (t.get('selected_profiles') or []) if p != last_profile]
                    if alt_pool:
                        self.log(f"--- Профиль '{start_profile}' только что использовался предыдущей книгой — "
                                  f"начинаю эту книгу с '{alt_pool[0]}' вместо него ---")
                        start_profile = alt_pool[0]
                    else:
                        # Другого аккаунта нет — даём Chrome чуть больше времени
                        # долежать блокировки перед повторным использованием того же профиля.
                        time.sleep(3)
            self.log(f"--- НАЧИНАЮ КНИГУ: {t['r']} ---")
            # ВАЖНО: раньше здесь ждали worker_thread.is_alive() — но при смене
            # аккаунта (handoff) _worker_core запускает НОВЫЙ поток worker() для
            # той же книги и возвращает 'handoff', из-за чего ИСХОДНЫЙ поток
            # быстро умирает, хотя книга ещё реально переводится в новом потоке.
            # sequential_manager считал книгу готовой раньше времени и уходил
            # к следующей, убивая Chrome ещё работающего "осиротевшего" потока.
            # Теперь ждём общий book_done_event — его выставляет только тот
            # worker(), который завершился по-настоящему ('done'/'stopped'),
            # а при handoff событие передаётся дальше по цепочке новому потоку
            # (через data['book_done_event']) и НЕ считается завершением книги.
            book_done_event = threading.Event()
            t_run = dict(t)
            t_run['book_done_event'] = book_done_event
            worker_thread = threading.Thread(target=self.worker, args=(t_run, start_profile, wait_time, s_ai, s_tom, s_rul, headless), daemon=True)
            worker_thread.start()
            while not book_done_event.is_set():
                time.sleep(1)
                if STOP_EVENT.is_set(): break
            last_profile = start_profile
            if STOP_EVENT.is_set(): break

    # ==================== ЯДРО ====================

    def _update_rulate_cookies(self, driver, p_name):
        """Обновляет снимок кук для фонового монитора баланса. Дешёвый вызов из
        основного потока (тот же поток, что и весь Selenium) — потокобезопасность
        не нарушается, т.к. сам монитор Selenium не трогает вообще."""
        try:
            cookies = driver.get_cookies()
        except Exception:
            return
        with RULATE_COOKIE_LOCK:
            RULATE_COOKIE_SNAPSHOTS[p_name] = cookies

    def _ensure_balance_watch(self, p_name, rulate_url):
        """Запускает фоновый поток мониторинга баланса для ЛЮБОГО аккаунта,
        который только начал работу. Уведомления показываются для всех аккаунтов
        (а не для одного единственного, как было раньше), но ТОЛЬКО когда галочка
        'Уведомления о балансе' включена в настройках."""
        with BALANCE_WATCH_LOCK:
            th = BALANCE_WATCH_THREADS.get(p_name)
            if th and th.is_alive():
                return
            th = threading.Thread(target=_balance_watch_loop, args=(self, p_name, rulate_url), daemon=True)
            BALANCE_WATCH_THREADS[p_name] = th
            th.start()

    def worker(self, data, p_name, wait_time, s_ai, s_tom, s_rul, headless=False):
        """Супервизор: запускает _worker_core и, если тот завершился НЕ из-за
        успешного выполнения лимита глав и НЕ из-за ручной остановки — автоматически
        перезапускает задачу с той главы, на которой она остановилась (data['start'])."""
        consecutive_fails = 0
        last_start = data.get('start')
        book_done_event = data.get('book_done_event')  # общий на всю книгу, переживает handoff
        while True:
            # Регистрируем профиль как "активный" на время реальной работы с Chrome —
            # kill_chrome_processes() не будет трогать его браузер, даже если
            # sequential_manager в этот момент убирает Chrome другой книги.
            _register_active_profile(p_name)
            try:
                outcome = self._worker_core(data, p_name, wait_time, s_ai, s_tom, s_rul, headless)
            finally:
                _unregister_active_profile(p_name)

            if STOP_EVENT.is_set():
                if book_done_event: book_done_event.set()
                return  # пользователь нажал «Остановить» — не перезапускаем

            if outcome == 'handoff':
                # Задача уже продолжена в другом потоке (смена аккаунта) под другим
                # профилем — это НЕ конец книги, поэтому book_done_event специально
                # НЕ выставляем. Его выставит тот поток, что доведёт книгу до конца.
                return

            if outcome in ('done', 'stopped'):
                if book_done_event: book_done_event.set()
                return  # книга реально закончена (лимит глав) либо остановлена

            # Если с прошлой попытки реально продвинулись хотя бы на одну главу —
            # сбрасываем счётчик подряд идущих сбоев (это была не зацикленная поломка,
            # а обычная одиночная ошибка сети/сайта).
            if data.get('start') != last_start:
                consecutive_fails = 0
                last_start = data.get('start')
            consecutive_fails += 1

            # outcome in ('error', 'frozen', None) — сбой/ошибка, не завершение и не ручная остановка.
            # Прогрессивная задержка: если один и тот же сбой повторяется подряд на одной
            # и той же главе, не долбим браузер каждые 8 сек — это лишь усугубляет
            # ситуацию (Chrome не успевает освободить профиль), а увеличиваем паузу.
            if outcome == 'frozen':
                delay = RESTART_DELAY_FROZEN_SEC
            else:
                delay = min(RESTART_DELAY_SEC * (2 ** min(consecutive_fails - 1, 4)), 300)
            self.log(f"[{p_name}] ⟳ Задача прервана ({outcome}, подряд сбоев: {consecutive_fails}). "
                      f"Автоперезапуск через {delay} сек, продолжу с главы {data['start']}...")
            for _ in range(delay):
                if STOP_EVENT.is_set():
                    return
                time.sleep(1)
            if STOP_EVENT.is_set():
                return
            try:
                kill_chrome_processes(wait_sec=1)
                # Чистим блокировки не только текущего профиля, а всех профилей,
                # которые могут быть задействованы этой книгой (ротация/смена аккаунта).
                for prof in (data.get('selected_profiles') or [p_name]):
                    clean_chrome_profile_lock(prof)
            except:
                pass
            self.log(f"[{p_name}] ⟳ Перезапускаю перевод с главы {data['start']}...")

    def _worker_core(self, data, p_name, wait_time, s_ai, s_tom, s_rul, headless=False):
        self.log(f'[{p_name}] Поток запущен')
        driver = None
        # Список профилей для ротации — исключаем замороженные
        all_profiles = data.get('selected_profiles', [p_name])
        if not all_profiles:
            all_profiles = [p_name]
        book_profiles = [p for p in all_profiles if not is_account_frozen(p)]
        if not book_profiles:
            self.log(f'[{p_name}] ❄ Все выбранные аккаунты заморожены! Пропускаю задачу.')
            return 'frozen'
        if p_name not in book_profiles:
            p_name = book_profiles[0]
            self.log(f'Стартовый аккаунт заморожен. Начинаю с: {p_name}')
        profile_idx = book_profiles.index(p_name) if p_name in book_profiles else 0
        try:
            options = self.get_stealth_options(p_name, headless)
            driver = self._new_chrome_driver(options)
            try:
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': "try{Object.defineProperty(navigator,'webdriver',{get:()=>undefined,configurable:true});}catch(e){}"
                })
            except Exception:
                pass
            wait = WebDriverWait(driver, 45)
            
            # Tomato Navigation
            driver.get(data['t'])
            target_ch = data['start']
            r_start = ((data['start'] - 1) // 50) * 50 + 1
            range_text = f"Chapter {r_start} - {r_start + 49}"
            try:
                acc_xpath = f"//button[contains(@class, 'accordion-button') and .//b[contains(text(), '{range_text}')]]"
                acc_btn = wait.until(EC.presence_of_element_located((By.XPATH, acc_xpath)))
                if 'collapsed' in acc_btn.get_attribute('class'):
                    driver.execute_script('arguments[0].click();', acc_btn)
                    time.sleep(3)
            except: pass
            
            ch_xpath = f"//div[contains(@class, 'chapter-container') and .//span[text()='#{target_ch}']]"
            ch_cont = wait.until(EC.presence_of_element_located((By.XPATH, ch_xpath)))
            next_tom_url = ch_cont.find_element(By.TAG_NAME, 'a').get_attribute('href')
            
            driver.execute_script(f"window.open('{AI_STUDIO_URL}', 'ai_tab');")
            driver.execute_script(f"window.open('{data['r']}', 'rul_tab');")
            
            h_tom, h_ai, h_rul = (None, None, None)
            for h in driver.window_handles:
                driver.switch_to.window(h); url = driver.current_url.lower()
                if 'chat.deepseek.com' in url: h_ai = h
                elif 'tl.rulate' in url: h_rul = h
                elif 'tomatomtl' in url: h_tom = h
            
            def setup_ai_page(use_new_chat_btn=False):
                driver.switch_to.window(h_ai)
                if use_new_chat_btn:
                    clicked = False
                    try:
                        # Кнопка "New chat" в DeepSeek — div с классом _5a8ac7a и span "New chat"
                        new_chat_xpaths = [
                            '//div[contains(@class,"_5a8ac7a") and .//span[text()="New chat"]]',
                            '//div[contains(@class,"a084f19e") and .//span[text()="New chat"]]',
                            '//*[contains(@class,"_5a8ac7a")]',
                            '//span[text()="New chat"]/parent::div',
                            '//span[text()="New chat"]',
                        ]
                        for xpath in new_chat_xpaths:
                            try:
                                btn = driver.find_element(By.XPATH, xpath)
                                driver.execute_script('arguments[0].click();', btn)
                                clicked = True
                                self.log(f'[{p_name}] Нажата кнопка New Chat (DeepSeek)')
                                break
                            except:
                                continue
                        if not clicked:
                            self.log(f'[{p_name}] New Chat не найден — переходим по URL...')
                            driver.get(AI_STUDIO_URL)
                    except:
                        driver.get(AI_STUDIO_URL)
                    time.sleep(4 if not s_ai else 3)
                else:
                    driver.get(AI_STUDIO_URL)
                    time.sleep(6 if not s_ai else 4)
                # Отправляем промпт как первое сообщение
                with open(data['pr'], 'r', encoding='utf-8') as f: pr_text = f.read()
                self.send_ai(driver, pr_text, wait, p_name, True, wait_time)

            setup_ai_page()
            is_first_chapter = True

            chapters_done = 0
            chapters_on_profile = 0
            worker_outcome = None
            while chapters_done < data['limit']:
                if STOP_EVENT.is_set(): worker_outcome = 'stopped'; break
                
                # Авто-обновление каждые 7 запросов — нажимаем New Chat для обхода лимита DeepSeek
                if chapters_done > 0 and chapters_done % 10 == 0:
                    self.log(f"[{p_name}] Лимит 10 запросов DeepSeek. Открываю новый чат...")
                    setup_ai_page(use_new_chat_btn=True)
                    self.log(f'[{p_name}] Ждём 8 сек пока DeepSeek обработает промпт...')
                    for _ in range(8):
                        if STOP_EVENT.is_set(): break
                        time.sleep(1)

                driver.switch_to.window(h_tom); driver.get(next_tom_url); time.sleep(2 if not s_tom else 1)
                next_tom_url_current = driver.current_url  # запоминаем текущую страницу для fallback
                # Заголовок главы — несколько fallback-селекторов для разных шаблонов Tomato
                title = ''
                for sel in [
                    (By.ID, 'chapter_title'),
                    (By.CSS_SELECTOR, 'h1.chapter-title'),
                    (By.CSS_SELECTOR, 'h2.chapter-title'),
                    (By.CSS_SELECTOR, '.chapter-title'),
                    (By.CSS_SELECTOR, 'h1'),
                    (By.CSS_SELECTOR, '.titles h2'),
                ]:
                    try:
                        el = driver.find_element(*sel)
                        title = el.text.strip()
                        if title:
                            break
                    except:
                        continue
                if not title:
                    title = driver.title.strip() or f'Глава {data["start"] + chapters_done + 1}'
                
                # Raw text extract (Кнопка RAW) — несколько fallback-селекторов
                raw_text = ""
                raw_btn_xpaths = [
                    "//button[contains(@onclick, 'copyToClipboard1')]",
                    "//button[contains(@onclick, 'copyToClipboard')]",
                    "//button[normalize-space(text())='RAW' or normalize-space(text())='Raw']",
                    "//button[contains(@class,'raw') or contains(@id,'raw')]",
                    "//a[normalize-space(text())='RAW' or normalize-space(text())='Raw']",
                    "//button[contains(translate(text(),'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'RAW')]",
                ]
                raw_btn = None
                for xp in raw_btn_xpaths:
                    try:
                        raw_btn = WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.XPATH, xp)))
                        if raw_btn:
                            break
                    except:
                        continue

                if raw_btn:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", raw_btn)
                        time.sleep(0.3)
                        sentinel_raw = f'__RAW_SENTINEL_{time.time()}__'
                        with CLIPBOARD_LOCK:
                            # Кнопка RAW сама пишет в системный буфер обмена — этого не избежать,
                            # но мы сохраняем реальный буфер пользователя и вернём его обратно после чтения
                            _user_clip = self._clipboard_save()
                            pyperclip.copy(sentinel_raw)
                            # Пробуем JS-клик, затем обычный если не сработал
                            driver.execute_script('arguments[0].click();', raw_btn)
                            time.sleep(0.5)
                            try: driver.switch_to.alert.accept()
                            except: pass
                            # Ждём до 4 сек пока буфер изменится
                            for _ri in range(8):
                                time.sleep(0.5)
                                _clip = pyperclip.paste().strip()
                                if _clip and _clip != sentinel_raw and len(_clip) > 50:
                                    raw_text = _clip
                                    break
                            # Если JS-клик не помог — пробуем обычный клик
                            if not raw_text or len(raw_text) < 50:
                                pyperclip.copy(sentinel_raw)
                                try:
                                    raw_btn.click()
                                except:
                                    ActionChains(driver).move_to_element(raw_btn).click().perform()
                                time.sleep(0.5)
                                try: driver.switch_to.alert.accept()
                                except: pass
                                for _ri in range(8):
                                    time.sleep(0.5)
                                    _clip = pyperclip.paste().strip()
                                    if _clip and _clip != sentinel_raw and len(_clip) > 50:
                                        raw_text = _clip
                                        break
                            self._clipboard_restore(_user_clip)
                    except Exception as _re:
                        self.log(f'[{p_name}] RAW кнопка — ошибка: {_re}')

                if not raw_text or len(raw_text) < 100:
                    raw_text = driver.execute_script(
                        "return window.txt_content || "
                        "(document.getElementById('chapter_content') ? document.getElementById('chapter_content').innerText : '') || "
                        "(document.querySelector('.chapter-content,.text-content,#content') ? document.querySelector('.chapter-content,.text-content,#content').innerText : '');"
                    )
                
                # Очистка мусора Tomato
                if raw_text:
                    raw_text = re.sub(r"TomatoMTL – .*?(\n|$)", "", raw_text)
                    raw_text = re.sub(r"URL: https?://tomatomtl\.com/.*?(\n|$)", "", raw_text).strip()

                # Дописка к промпту инструкции
                msg_to_send = raw_text + "\n\nесли что то будет нарушать ваши правила и ограничения то замени фразы на соответствующую которая максимально близко передает первоначальный смысл соблюдая ваши ограничения и правила. Также ОБЯЗАТЕЛЬНО должны быть новые термины. ОБЯЗАТЕЛЬНО!! Когда ты переводишь ты должен следить за количеством предложений в абзаце. В абзаце должно быть МАКСИМУМ 2 предложения, не больше, и предложения не должны быть неоправданно длинными. "

                next_tom_url = None
                # Определяем URL следующей главы — берём кнопку next ПРЯМО со страницы главы.
                # НЕ возвращаемся на страницу книги — это экономит 1 полный page load каждый цикл.
                try:
                    driver.switch_to.window(h_tom)
                    # Страница главы уже открыта (next_tom_url_current) — ищем кнопку next
                    next_tom_url = None
                    for _nx_xpath in [
                        "//a[contains(@class,'next') and @href]",
                        "//a[@rel='next' and @href]",
                        "//a[contains(@title,'Next') or contains(@title,'Следующая')]",
                        "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'next chapter')]",
                    ]:
                        try:
                            _el = driver.find_element(By.XPATH, _nx_xpath)
                            _href = _el.get_attribute('href')
                            if _href and 'tomatomtl' in _href:
                                next_tom_url = _href
                                break
                        except:
                            continue

                    if next_tom_url:
                        self.log(f'[{p_name}] Следующая глава (next btn): {next_tom_url}')
                    else:
                        raise Exception('next button not found on chapter page')
                except Exception as e:
                    # Fallback: возвращаемся на страницу книги и ищем по номеру главы
                    self.log(f'[{p_name}] next кнопка не найдена, ищу в списке глав: {e}')
                    try:
                        # ВАЖНО: data['start'] на этом этапе — это номер ТЕКУЩЕЙ обрабатываемой
                        # главы (она увеличится только после публикации на RuLate ниже). Значит
                        # следующая глава, которую нам нужно найти здесь — data['start']+1.
                        current_ch_num = data['start'] + 1
                        r_next_start = ((current_ch_num - 1) // 50) * 50 + 1
                        range_text_next = f"Chapter {r_next_start} - {r_next_start + 49}"
                        driver.switch_to.window(h_tom)
                        driver.get(data['t'])
                        time.sleep(3)
                        try:
                            acc_xpath_next = f"//button[contains(@class, 'accordion-button') and .//b[contains(text(), '{range_text_next}')]]"
                            acc_btn_next = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, acc_xpath_next)))
                            if 'collapsed' in acc_btn_next.get_attribute('class'):
                                driver.execute_script('arguments[0].click();', acc_btn_next)
                                time.sleep(2)
                        except: pass
                        ch_xpath_next = f"//div[contains(@class, 'chapter-container') and .//span[text()='#{current_ch_num}']]"
                        next_cont = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, ch_xpath_next)))
                        next_tom_url = next_cont.find_element(By.TAG_NAME, 'a').get_attribute('href')
                        self.log(f'[{p_name}] Следующая глава (список) #{current_ch_num}: {next_tom_url}')
                    except Exception as e2:
                        self.log(f'[{p_name}] Не смог найти следующую главу: {e2}')
                        next_tom_url = next_tom_url_current

                # Небольшая задержка перед самой первой главой
                if is_first_chapter:
                    self.log(f'[{p_name}] Первая глава — ждём 12 сек пока DeepSeek обработает промпт...')
                    for _ in range(12):
                        if STOP_EVENT.is_set(): break
                        time.sleep(1)
                    is_first_chapter = False

                # AI Loop — 3 попытки. Проверяем: Content Blocked, Prohibited, теги, rate limit
                driver.switch_to.window(h_ai)
                translated_body = None
                title_from_ai = ''   # название главы из тега [T]
                success_ai = False
                prohibited_count = 0
                empty_count = 0
                retry_msg = (
                    'Перепиши эту главу заново. Требования:\n'
                    '1. Не должно быть Prohibited content и Content blocked\n'
                    '2. Замени всё нарушающее правила на подходящее по смыслу\n'
                    '3. Обязательно используй теги [G]...[/G], [T]...[/T], [B]...[/B]\n'
                    '4. В [G] обязательно укажи минимум 1 новый термин (имя/название/понятие) из главы\n'
                    '5. Сохрани смысл оригинала насколько возможно'
                )
                format_retry_msg = (
                    'Ответ получен, но не соответствует формату. Пришли главу снова используя ТОЛЬКО теги:\n'
                    '[G]глоссарий[/G]\n[T]название главы[/T]\n[B]текст перевода[/B]\n'
                    'Никакого лишнего текста вне тегов.'
                )
                glossary_retry_msg = (
                    'Формат в целом верный, но тег [G] пуст или не содержит новых терминов.\n'
                    'ОБЯЗАТЕЛЬНО пришли главу снова и укажи в [G] хотя бы ОДИН новый термин '
                    '(имя персонажа, название техники/места/предмета и т.п.), который встретился в этой главе, '
                    'с кратким переводом/пояснением. Пустой глоссарий или фразы вроде "новых терминов нет" не принимаются.\n'
                    'Формат ответа строго: [G]термин — пояснение[/G]\\n[T]название главы[/T]\\n[B]текст перевода[/B]'
                )
                need_retry = False
                last_fail_reason = ''
                for attempt in range(3):
                    self.log(f'[{p_name}] DeepSeek: Попытка {attempt + 1}/3...')
                    if need_retry:
                        # Пустой ответ — не перепись, просто ждём и повторяем ту же главу
                        if last_fail_reason == 'empty':
                            send_text = msg_to_send
                            self.log(f'[{p_name}] Пустой ответ — повторяю отправку главы...')
                        # Глоссарий без новых терминов — просим обязательно указать термин
                        elif last_fail_reason == 'no_glossary':
                            send_text = glossary_retry_msg
                        # Неверный формат тегов — просим прислать заново в правильном формате
                        elif last_fail_reason == 'format':
                            send_text = format_retry_msg
                        # Prohibited — просим переписать
                        else:
                            send_text = retry_msg
                    else:
                        send_text = msg_to_send
                    need_retry = False
                    last_fail_reason = ''

                    resp = self.send_ai(driver, send_text, wait, p_name, False, wait_time)

                    # Лимит запросов — переключаем профиль
                    if self.check_rate_limit(driver):
                        self.log(f'[{p_name}] ЛИМИТ ЗАПРОСОВ DeepSeek! Переключаю профиль...')
                        profile_idx = (profile_idx + 1) % len(book_profiles)
                        new_profile = book_profiles[profile_idx]
                        new_data = dict(data)
                        new_data['limit'] = data['limit'] - chapters_done
                        new_data['profile'] = new_profile
                        threading.Thread(target=self.worker, args=(new_data, new_profile, wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()
                        if driver: driver.quit()
                        return 'handoff'

                    if resp == '__RATE_LIMIT__':
                        self.log(f'[{p_name}] ЛИМИТ ЗАПРОСОВ DeepSeek! Переключаю профиль...')
                        profile_idx = (profile_idx + 1) % len(book_profiles)
                        new_profile = book_profiles[profile_idx]
                        new_data = dict(data)
                        new_data['limit'] = data['limit'] - chapters_done
                        new_data['profile'] = new_profile
                        threading.Thread(target=self.worker, args=(new_data, new_profile, wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()
                        if driver: driver.quit()
                        return 'handoff'

                    if resp == '__PROHIBITED__':
                        prohibited_count += 1
                        self.log(f'[{p_name}] Prohibited content на попытке {attempt + 1}')
                        need_retry = True
                        last_fail_reason = 'prohibited'
                        time.sleep(2)
                        continue

                    if not resp:
                        empty_count += 1
                        self.log(f'[{p_name}] Пустой ответ на попытке {attempt + 1} — повторяю без retry_msg')
                        need_retry = True
                        last_fail_reason = 'empty'
                        time.sleep(3)
                        continue

                    # DEBUG: сохраняем каждый ответ Gemini в файл
                    try:
                        _dbg = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'debug_resp_{attempt+1}.txt')
                        open(_dbg, 'w', encoding='utf-8').write(repr(resp))
                    except: pass

                    is_ok, reason = validate_ai_format(resp)
                    if not is_ok:
                        if 'Тег [G]' in reason:
                            self.log(f'[{p_name}] Нет новых терминов в глоссарии: {reason} — запрашиваю обязательный термин...')
                            need_retry = True
                            last_fail_reason = 'no_glossary'
                        else:
                            self.log(f'[{p_name}] Формат ответа неверный: {reason} — запрашиваю заново...')
                            need_retry = True
                            last_fail_reason = 'format'
                        time.sleep(3)
                        continue
                    if is_ok:
                        translated_body = extract_body(resp)
                        title_from_ai = extract_title(resp)
                        glossary_data = extract_glossary(resp)
                        if glossary_data:
                            append_new_glossary_terms(data['pr'], glossary_data)
                        translated_body = translated_body.replace('\r\n', '\n').replace('\r', '\n')
                        # Абзацы через \n — RuLate split_type=0 каждую строку = 1 фрагмент
                        _paras = [p.strip() for p in re.split(r'\n{2,}', translated_body) if p.strip()]
                        translated_body = '\n'.join(_paras)
                        success_ai = True
                        break
                    else:
                        preview = resp[:120].replace('\n', ' ')
                        self.log(f'[{p_name}] Неверный формат ({reason}) на попытке {attempt + 1}. Ответ: {repr(resp[:300])}')
                        need_retry = True
                        last_fail_reason = 'format'
                        time.sleep(5)

                # Все 3 попытки исчерпаны (Prohibited или другая ошибка) — JS Fallback с Tomato
                if not success_ai:
                    if prohibited_count >= 3:
                        self.log(f'[{p_name}] Глава заблокирована DeepSeek (Prohibited x3). Беру текст с Tomato напрямую...')
                    else:
                        self.log(f'[{p_name}] 3 попытки исчерпаны. JS Fallback с Tomato...')
                    # Открываем страницу главы — она могла не быть открыта если навигация шла через список
                    driver.switch_to.window(h_tom)
                    if driver.current_url != next_tom_url_current:
                        self.log(f'[{p_name}] Открываю страницу главы для JS Fallback...')
                        driver.get(next_tom_url_current)
                        time.sleep(5)
                    translated_body = driver.execute_script(
                        'var el = document.getElementById("chapter_content");'
                        ' if (!el) el = document.querySelector(".chapter-content,.text-content,#content");'
                        ' return el ? el.innerText : (window.txt_content || "");'
                    )
                    if translated_body:
                        translated_body = re.sub(r'TomatoMTL \u2013 .*?(\n|$)', '', translated_body)
                        translated_body = re.sub(r'URL: https?://tomatomtl\.com/.*?(\n|$)', '', translated_body).strip()
                    if not translated_body:
                        self.log(f'[{p_name}] JS Fallback пустой, пропускаю главу')
                        data['start'] += 1
                        chapters_done += 1
                        chapters_on_profile += 1
                        continue
                # RuLate Post
                # Нормализуем текст: сохраняем абзацы (двойные \n → разделители абзацев)
                if translated_body:
                    translated_body = translated_body.replace('\r\n', '\n').replace('\r', '\n')
                    _paras = [p.strip() for p in re.split(r'\n{2,}', translated_body) if p.strip()]
                    translated_body = '\n'.join(_paras)

                # ==================== ПРОВЕРКА НА ОСТАВШИЕСЯ КИТАЙСКИЕ ИЕРОГЛИФЫ ====================
                # Требование: текст, который уходит на RuLate, не должен содержать НИ ОДНОГО
                # китайского иероглифа. Проверяем это здесь — уже после того, как перевод готов
                # (не важно, пришёл ли он от DeepSeek или это JS Fallback с Tomato). Если иероглифы
                # найдены, НЕ публикуем как есть: показываем DeepSeek ровно те фрагменты, где они
                # встречаются, и просим переписать ВСЮ главу заново без них. Отдельный бюджет
                # попыток (MAX_CJK_FIX_ATTEMPTS) — не завязан на 3 попытки проверки формата выше,
                # чтобы не отнимать их у сложных глав.
                cjk_unresolved = False
                cjk_attempt = 0
                while translated_body:
                    cjk_fragments = extract_cjk_fragments(translated_body)
                    if not cjk_fragments:
                        break  # чисто — иероглифов не осталось
                    cjk_attempt += 1
                    self.log(f'[{p_name}] ⚠ В переводе остались китайские иероглифы '
                              f'({len(cjk_fragments)} фрагм.) — исправляю, попытка {cjk_attempt}/{MAX_CJK_FIX_ATTEMPTS}...')
                    if cjk_attempt > MAX_CJK_FIX_ATTEMPTS:
                        self.log(f'[{p_name}] ❌ Не удалось убрать иероглифы за {MAX_CJK_FIX_ATTEMPTS} попыток. '
                                 f'Глава будет сохранена как черновик БЕЗ публикации на RuLate — нужна ручная проверка.')
                        cjk_unresolved = True
                        break

                    driver.switch_to.window(h_ai)
                    cjk_retry_text = build_cjk_retry_msg(cjk_fragments)
                    resp = self.send_ai(driver, cjk_retry_text, wait, p_name, False, wait_time)

                    if self.check_rate_limit(driver):
                        self.log(f'[{p_name}] ЛИМИТ ЗАПРОСОВ DeepSeek! Переключаю профиль...')
                        profile_idx = (profile_idx + 1) % len(book_profiles)
                        new_profile = book_profiles[profile_idx]
                        new_data = dict(data)
                        new_data['limit'] = data['limit'] - chapters_done
                        new_data['profile'] = new_profile
                        threading.Thread(target=self.worker, args=(new_data, new_profile, wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()
                        if driver: driver.quit()
                        return 'handoff'

                    if not resp:
                        self.log(f'[{p_name}] Пустой ответ при исправлении иероглифов — пробую снова...')
                        time.sleep(3)
                        continue

                    is_ok_cjk, reason_cjk = validate_ai_format(resp)
                    if not is_ok_cjk:
                        self.log(f'[{p_name}] Ответ на исправление иероглифов пришёл в неверном формате ({reason_cjk}) — пробую снова...')
                        time.sleep(3)
                        continue

                    translated_body = extract_body(resp)
                    _title_fix = extract_title(resp)
                    if _title_fix:
                        title_from_ai = _title_fix
                    glossary_fix = extract_glossary(resp)
                    if glossary_fix:
                        append_new_glossary_terms(data['pr'], glossary_fix)
                    translated_body = translated_body.replace('\r\n', '\n').replace('\r', '\n')
                    _paras = [p.strip() for p in re.split(r'\n{2,}', translated_body) if p.strip()]
                    translated_body = '\n'.join(_paras)
                    # цикл повторит проверку translated_body на иероглифы с самого начала

                # ==================== ПРОВЕРКА ОФОРМЛЕНИЯ ПО СИМВОЛАМ ====================
                # DeepSeek иногда сливает слишком много предложений в один абзац или пишет
                # неоправданно длинные абзацы. Проверяем это по символам: 1) в абзаце
                # не должно быть больше SENTENCES_PER_PARAGRAPH_LIMIT предложений; 2) длина
                # самого абзаца не должна превышать фиксированный лимит PARAGRAPH_MAX_LENGTH.
                # Проверяем это здесь, уже после того как иероглифов в тексте не осталось
                # (иначе фрагменты для отправки DeepSeek были бы неактуальны). Если проблемы
                # находятся — просим DeepSeek переписать главу с исправлениями. Отдельный
                # бюджет попыток (MAX_PARAGRAPH_FIX_ATTEMPTS), не завязан на попытки проверки
                # формата/иероглифов.
                para_unresolved = False
                if not cjk_unresolved:
                    para_attempt = 0
                    while translated_body:
                        bad_paragraphs, long_paragraphs, max_len = find_layout_issues(translated_body)
                        if not bad_paragraphs and not long_paragraphs:
                            break  # с абзацами и длиной абзацев всё хорошо
                        para_attempt += 1
                        self.log(f'[{p_name}] ⚠ В переводе {len(bad_paragraphs)} абзац(ев) с избытком предложений '
                                  f'и {len(long_paragraphs)} слишком длинных абзацев (лимит '
                                  f'{max_len} симв.) — исправляю, попытка '
                                  f'{para_attempt}/{MAX_PARAGRAPH_FIX_ATTEMPTS}...')
                        if para_attempt > MAX_PARAGRAPH_FIX_ATTEMPTS:
                            self.log(f'[{p_name}] ❌ Не удалось исправить оформление за '
                                      f'{MAX_PARAGRAPH_FIX_ATTEMPTS} попыток. Глава будет сохранена как '
                                      f'черновик БЕЗ публикации на RuLate — нужна ручная проверка.')
                            para_unresolved = True
                            break

                        driver.switch_to.window(h_ai)
                        para_retry_text = build_layout_retry_msg(bad_paragraphs, long_paragraphs, max_len)
                        resp = self.send_ai(driver, para_retry_text, wait, p_name, False, wait_time)

                        if self.check_rate_limit(driver):
                            self.log(f'[{p_name}] ЛИМИТ ЗАПРОСОВ DeepSeek! Переключаю профиль...')
                            profile_idx = (profile_idx + 1) % len(book_profiles)
                            new_profile = book_profiles[profile_idx]
                            new_data = dict(data)
                            new_data['limit'] = data['limit'] - chapters_done
                            new_data['profile'] = new_profile
                            threading.Thread(target=self.worker, args=(new_data, new_profile, wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()
                            if driver: driver.quit()
                            return 'handoff'

                        if not resp:
                            self.log(f'[{p_name}] Пустой ответ при исправлении разбивки на абзацы — пробую снова...')
                            time.sleep(3)
                            continue

                        is_ok_para, reason_para = validate_ai_format(resp)
                        if not is_ok_para:
                            self.log(f'[{p_name}] Ответ на исправление абзацев пришёл в неверном формате ({reason_para}) — пробую снова...')
                            time.sleep(3)
                            continue

                        translated_body = extract_body(resp)
                        _title_fix2 = extract_title(resp)
                        if _title_fix2:
                            title_from_ai = _title_fix2
                        glossary_fix2 = extract_glossary(resp)
                        if glossary_fix2:
                            append_new_glossary_terms(data['pr'], glossary_fix2)
                        translated_body = translated_body.replace('\r\n', '\n').replace('\r', '\n')
                        _paras = [p.strip() for p in re.split(r'\n{2,}', translated_body) if p.strip()]
                        translated_body = '\n'.join(_paras)
                        # цикл повторит проверку translated_body на абзацы с самого начала

                # ==================== ПРОВЕРКА КОЛИЧЕСТВА СТРОК ====================
                lines_unresolved = False
                if not cjk_unresolved and not para_unresolved:
                    lines_attempt = 0
                    while translated_body:
                        line_count = count_lines_in_text(translated_body)
                        if line_count >= MIN_LINES_PER_CHAPTER:
                            break  # строк достаточно
                        lines_attempt += 1
                        self.log(f'[{p_name}] ⚠ В переводе всего {line_count} строк(и), '
                                  f'нужно минимум {MIN_LINES_PER_CHAPTER} — '
                                  f'расширяю, попытка {lines_attempt}/{MAX_LINES_FIX_ATTEMPTS}...')
                        if lines_attempt > MAX_LINES_FIX_ATTEMPTS:
                            self.log(f'[{p_name}] ❌ Не удалось расширить главу до {MIN_LINES_PER_CHAPTER} строк за '
                                      f'{MAX_LINES_FIX_ATTEMPTS} попыток. Глава будет сохранена как черновик '
                                      f'БЕЗ публикации на RuLate — нужна ручная проверка.')
                            lines_unresolved = True
                            break

                        driver.switch_to.window(h_ai)
                        lines_retry_text = build_lines_retry_msg(line_count, MIN_LINES_PER_CHAPTER)
                        resp = self.send_ai(driver, lines_retry_text, wait, p_name, False, wait_time)

                        if self.check_rate_limit(driver):
                            self.log(f'[{p_name}] ЛИМИТ ЗАПРОСОВ DeepSeek! Переключаю профиль...')
                            profile_idx = (profile_idx + 1) % len(book_profiles)
                            new_profile = book_profiles[profile_idx]
                            new_data = dict(data)
                            new_data['limit'] = data['limit'] - chapters_done
                            new_data['profile'] = new_profile
                            threading.Thread(target=self.worker, args=(new_data, new_profile, wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()
                            if driver: driver.quit()
                            return 'handoff'

                        if not resp:
                            self.log(f'[{p_name}] Пустой ответ при расширении строк — пробую снова...')
                            time.sleep(3)
                            continue

                        is_ok_lines, reason_lines = validate_ai_format(resp)
                        if not is_ok_lines:
                            self.log(f'[{p_name}] Ответ на расширение строк неверного формата ({reason_lines}) — пробую снова...')
                            time.sleep(3)
                            continue

                        translated_body = extract_body(resp)
                        _title_fix3 = extract_title(resp)
                        if _title_fix3:
                            title_from_ai = _title_fix3
                        glossary_fix3 = extract_glossary(resp)
                        if glossary_fix3:
                            append_new_glossary_terms(data['pr'], glossary_fix3)
                        translated_body = translated_body.replace('\r\n', '\n').replace('\r', '\n')
                        _paras = [p.strip() for p in re.split(r'\n{2,}', translated_body) if p.strip()]
                        translated_body = '\n'.join(_paras)
                        # цикл повторит проверку строк с самого начала

                final_title = title_from_ai if title_from_ai else title
                if title_from_ai:
                    self.log(f'[{p_name}] Название из [T]: {title_from_ai}')

                # Локально сохраняем главу для вкладки "Редактор" — независимо от того,
                # успешно ли она потом опубликуется на RuLate (posted=False пока что)
                _ch_num_local = data['start']
                try:
                    save_chapter_local(data['r'], data['t'], _ch_num_local, final_title, translated_body,
                                        data['is_paid'], data['is_delayed'], posted=False,
                                        book_title=data.get('book_title'), cover_url=data.get('cover_url'))
                except Exception as _se:
                    self.log(f'[{p_name}] Не удалось сохранить главу локально: {_se}')

                # Иероглифы так и не убрали за отведённые попытки — публикацию на RuLate
                # пропускаем полностью (глава уже сохранена черновиком выше), переходим
                # к следующей главе, но НЕ засчитываем её в лимит аккаунта, т.к. реально
                # ничего не опубликовано.
                if cjk_unresolved or para_unresolved or lines_unresolved:
                    data['start'] += 1; chapters_done += 1
                    data['card'].after(0, lambda v=data['start']: data['card'].update_counter(v))
                    h = load_json(HISTORY_FILE, {})
                    h[data['r']] = {'tomato': data['t'], 'prompt': data['pr'], 'start': data['start'], 'profile': p_name, 'limit': data['limit']}
                    save_json(HISTORY_FILE, h)
                    reasons = []
                    if cjk_unresolved: reasons.append('остались иероглифы')
                    if para_unresolved: reasons.append('не исправлена разбивка на абзацы')
                    if lines_unresolved: reasons.append(f'менее {MIN_LINES_PER_CHAPTER} строк')
                    self.log(f'[{p_name}] Глава #{_ch_num_local} НЕ опубликована ({", ".join(reasons)}). '
                             f'Откройте её во вкладке "Редактор", поправьте и опубликуйте вручную кнопкой.')
                    continue

                driver.switch_to.window(h_rul); driver.get(data['r']); time.sleep(2.5 if not s_rul else 1)
                self._update_rulate_cookies(driver, p_name)
                self._ensure_balance_watch(p_name, data['r'])
                try:
                    # ШАГ 1: Добавить главы — заполняем название, статус, галочки, жмём yt0
                    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Добавить главы')]"))).click()
                    time.sleep(1.5)
                    wait.until(EC.presence_of_element_located((By.ID, 'Chapter_title'))).send_keys(final_title)
                    Select(driver.find_element(By.ID, 'Chapter_status')).select_by_value('3')
                    if data['is_delayed']:
                        chk = driver.find_element(By.NAME, 'Chapter[post_open]')
                        if not chk.is_selected(): driver.execute_script('arguments[0].click();', chk)
                    if data['is_paid']:
                        chk = driver.find_element(By.NAME, 'Chapter[subscription]')
                        if not chk.is_selected(): driver.execute_script('arguments[0].click();', chk)
                    # Кнопка «Сохранить» на форме создания главы — name=yt0, class=btn-primary btn-small click-wait
                    btn_create = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@name='yt0' and contains(@class,'btn-primary')]"))  )
                    driver.execute_script('arguments[0].click();', btn_create)
                    time.sleep(2.5)

                    # ШАГ 2: находим ссылку «импортировать текст» в строке новой главы —
                    # пробуем сразу опубликовать напрямую HTTP-запросами (без открытия
                    # страниц импорта в браузере вообще), и только если не получилось —
                    # откатываемся на клики как раньше
                    import_link = wait.until(EC.element_to_be_clickable((By.XPATH,
                        "//a[contains(@href,'/import') and (contains(text(),'импортировать') or contains(text(),'Import'))]"))  )
                    import_href = import_link.get_attribute('href')

                    fast_ok = self._rulate_fast_import(driver, import_href, translated_body, p_name)
                    if fast_ok:
                        self.log(f'[{p_name}] ⚡ Глава импортирована и сохранена напрямую (без ожидания страниц)')
                    else:
                        driver.execute_script('arguments[0].click();', import_link)
                        time.sleep(1.5)

                        # ШАГ 3: Вставляем текст в textarea и жмём «Далее»
                        # Страница: form#form-prepare-text → textarea или div.tabbable
                        # Кнопка Далее: button.btn.btn-primary.pull-right (type=submit)
                        fld = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea, #TextSource_text')))
                        fld.click()
                        time.sleep(0.2)
                        self._js_paste(driver, fld, translated_body)
                        time.sleep(0.8)
                        try:
                            split_sel = driver.find_element(By.CSS_SELECTOR,
                                'select[name="TextSource[split_type]"], select#TextSource_split_type')
                            Select(split_sel).select_by_value('0')
                        except: pass
                        time.sleep(0.3)
                        btn_next = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                            "button.btn-primary.pull-right, button[type='submit'].btn-primary"))  )
                        driver.execute_script('arguments[0].click();', btn_next)
                        time.sleep(2)

                        # ШАГ 4: Ставим галочку «Добавить как перевод» (input#set_translate)
                        chk = wait.until(EC.presence_of_element_located((By.ID, 'set_translate')))
                        if not chk.is_selected():
                            driver.execute_script('arguments[0].click();', chk)
                        time.sleep(0.5)

                        # ШАГ 5: Кнопка «Сохранить» — class=btn btn-primary pull-right save, onclick=C.save()
                        btn_save = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                            "button.btn-primary.pull-right.save, button.save.btn-primary"))  )
                        driver.execute_script('arguments[0].click();', btn_save)
                        time.sleep(3)
                    
                    try:
                        save_chapter_local(data['r'], data['t'], _ch_num_local, final_title, translated_body,
                                            data['is_paid'], data['is_delayed'], posted=True,
                                            book_title=data.get('book_title'), cover_url=data.get('cover_url'))
                    except Exception as _se:
                        self.log(f'[{p_name}] Не удалось обновить статус главы в редакторе: {_se}')

                    data['start'] += 1; chapters_done += 1
                    data['card'].after(0, lambda v=data['start']: data['card'].update_counter(v))
                    # Учитываем главу в статистике аккаунта (заморозка при ≥50)
                    acct_stat = add_chapter_to_account(p_name)
                    if acct_stat.get('frozen'):
                        self.log(f'[{p_name}] ❄ Аккаунт заморожен после {CHAPTERS_FREEZE_LIMIT} глав до {acct_stat.get("freeze_until", "12:00")}. Переключаю профиль...')
                        # Ищем следующий незамороженный профиль
                        switched = False
                        for _ in range(len(book_profiles)):
                            profile_idx = (profile_idx + 1) % len(book_profiles)
                            candidate = book_profiles[profile_idx]
                            if not is_account_frozen(candidate):
                                self.log(f'[{p_name}] Переключаюсь на: {candidate}')
                                new_data = dict(data)
                                new_data['limit'] = data['limit'] - chapters_done
                                new_data['profile'] = candidate
                                threading.Thread(target=self.worker, args=(new_data, candidate, wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()
                                if driver: driver.quit()
                                switched = True
                                break
                        if switched:
                            return 'handoff'
                        self.log(f'[{p_name}] Все аккаунты заморожены! Останавливаю задачу.')
                        worker_outcome = 'frozen'
                        break
                    h = load_json(HISTORY_FILE, {})
                    h[data['r']] = {'tomato': data['t'], 'prompt': data['pr'], 'start': data['start'], 'profile': p_name, 'limit': data['limit']}
                    save_json(HISTORY_FILE, h)
                    chapters_on_profile += 1
                    self.log(f'[{p_name}] Глава готова! ({chapters_done}/{data["limit"]})')

                    # Автопереход на следующий профиль каждые CHAPTERS_FREEZE_LIMIT глав
                    if chapters_on_profile >= CHAPTERS_FREEZE_LIMIT and chapters_done < data['limit']:
                        self.log(f'[{p_name}] {CHAPTERS_FREEZE_LIMIT} глав — переключаю профиль...')
                        profile_idx = (profile_idx + 1) % len(book_profiles)
                        new_profile = book_profiles[profile_idx]
                        self.log(f'[{p_name}] Переключаюсь на: {new_profile}')
                        new_data = dict(data)
                        new_data['limit'] = data['limit'] - chapters_done
                        new_data['profile'] = new_profile
                        threading.Thread(target=self.worker, args=(new_data, new_profile, wait_time, s_ai, s_tom, s_rul, headless), daemon=True).start()
                        if driver: driver.quit()
                        return 'handoff'
                except Exception as e:
                    self.log(f'Ошибка RuLate: {e}')
            
            if driver: driver.quit()
            if worker_outcome is None:
                worker_outcome = 'done' if chapters_done >= data['limit'] else 'error'
            return worker_outcome
        except Exception as e:
            self.log(f'Ошибка: {e}')
            if driver: driver.quit()
            return 'error'

    def _clipboard_save(self):
        """Сохраняет текущее содержимое системного буфера обмена (то, что мог скопировать
        сам пользователь), чтобы потом вернуть его на место после внутренних операций скрипта."""
        try:
            return pyperclip.paste()
        except Exception:
            return None

    def _clipboard_restore(self, snapshot):
        """Возвращает буфер обмена к тому, что было до внутренних операций скрипта."""
        if snapshot is not None:
            try:
                pyperclip.copy(snapshot)
            except Exception:
                pass

    def _rulate_fast_import(self, driver, import_href, text, p_name=''):
        """Публикует текст главы напрямую HTTP-запросами (в обход отрисовки страниц
        браузером) — вместо клика по 'импортировать текст', ожидания загрузки формы,
        вставки текста, клика 'Далее', ожидания страницы разбивки, галочки и клика
        'Сохранить'. Использует куки уже открытой Selenium-сессии (та же авторизация),
        CSRF-поля в этих двух запросах у RuLate нет — проверка идёт по куке YII_CSRF_TOKEN,
        которая уходит вместе с остальными куками.

        Логика в двух запросах:
        1) POST .../import — отправляем текст, RuLate возвращает HTML-страницу разбивки
           на фрагменты (по одному текстовому полю t[txt][N] на строку/абзац).
        2) POST .../import_text_save — забираем ИМЕННО ТЕ значения t[txt][N], которые
           вернул сервер на шаге 1 (не режем текст сами!), и отправляем их обратно с
           set_translate=1 — это финальное сохранение перевода.

        Если хоть что-то в ответе не совпало с ожидаемым (сайт поменял вёрстку, сессия
        протухла, антибот и т.п.) — возвращает False, и вызывающий код должен откатиться
        на проверенный способ через клики Selenium. Никогда не бросает исключение наружу."""
        try:
            m = re.search(r'/book/(\d+)/(\d+)/import', import_href or '')
            if not m:
                return False
            base = f'https://tl.rulate.ru/book/{m.group(1)}/{m.group(2)}'

            sess = requests.Session()
            for c in driver.get_cookies():
                try:
                    sess.cookies.set(c['name'], c['value'], domain='tl.rulate.ru')
                except Exception:
                    pass
            try:
                ua = driver.execute_script('return navigator.userAgent;') or ''
            except Exception:
                ua = ''
            headers = {'Origin': 'https://tl.rulate.ru', 'Referer': base + '/import'}
            if ua:
                headers['User-Agent'] = ua

            # Шаг 1: импорт текста (multipart, как настоящая форма из браузера)
            files = {
                'TextSource[src_type]': (None, '1'),
                'TextSource[text]': (None, text),
                'TextSource[file]': ('', b''),
                'TextSource[encoding]': (None, 'UTF-8'),
                'TextSource[split_type]': (None, '0'),  # каждая строка = 1 фрагмент
                'TextSource[chopper]': (None, '1'),
            }
            r1 = sess.post(base + '/import', files=files, headers=headers, timeout=20)
            if r1.status_code != 200 or 't[txt][' not in r1.text:
                return False

            # Достаём готовые фрагменты ровно такими, какими их вернул сервер —
            # не пересчитываем сами, чтобы не разойтись с тем, что реально ожидает шаг 2
            frags = re.findall(r'name="t\[txt\]\[(\d+)\]"[^>]*>(.*?)</textarea>', r1.text, re.S)
            if not frags:
                frags = re.findall(r'name="t\[txt\]\[(\d+)\]"[^>]*?\svalue="(.*?)"', r1.text, re.S)
            if not frags:
                return False

            data = {'set_translate': '1'}
            for idx, val in frags:
                data[f't[txt][{idx}]'] = html_lib.unescape(val)

            # Шаг 2: финальное сохранение перевода
            r2 = sess.post(base + '/import_text_save', data=data, headers=headers, timeout=20)
            if r2.status_code != 200:
                return False
            if 'TextSource[text]' in r2.text or 't[txt][' in r2.text:
                # Похоже, снова вернулись на форму импорта/правки — сохранение не прошло
                return False
            return True
        except Exception as e:
            if p_name:
                self.log(f'[{p_name}] Быстрая публикация не сработала ({e}), использую обычный способ через клики...')
            return False

    def _post_chapter_to_rulate(self, driver, wait, rulate_url, title, text, is_paid, is_delayed, s_rul=False, p_name=''):
        """Публикует ОДНУ главу на RuLate: создаёт главу с названием/статусом/галочками,
        импортирует текст перевода и сохраняет. Повторяет логику из worker(), но как
        самостоятельный метод — используется кнопкой "Добавить на RuLate" в Редакторе.
        Возвращает True при успехе, False при ошибке."""
        try:
            driver.get(rulate_url)
            time.sleep(2.5 if not s_rul else 1)
            if p_name:
                self._update_rulate_cookies(driver, p_name)
                self._ensure_balance_watch(p_name, rulate_url)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Добавить главы')]"))).click()
            time.sleep(1.5)
            wait.until(EC.presence_of_element_located((By.ID, 'Chapter_title'))).send_keys(title)
            Select(driver.find_element(By.ID, 'Chapter_status')).select_by_value('3')
            if is_delayed:
                chk = driver.find_element(By.NAME, 'Chapter[post_open]')
                if not chk.is_selected(): driver.execute_script('arguments[0].click();', chk)
            if is_paid:
                chk = driver.find_element(By.NAME, 'Chapter[subscription]')
                if not chk.is_selected(): driver.execute_script('arguments[0].click();', chk)
            btn_create = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@name='yt0' and contains(@class,'btn-primary')]")))
            driver.execute_script('arguments[0].click();', btn_create)
            time.sleep(2.5)

            import_link = wait.until(EC.element_to_be_clickable((By.XPATH,
                "//a[contains(@href,'/import') and (contains(text(),'импортировать') or contains(text(),'Import'))]")))
            import_href = import_link.get_attribute('href')

            if self._rulate_fast_import(driver, import_href, text):
                return True

            # Быстрый способ не сработал (или недоступен) — обычный способ через клики
            driver.execute_script('arguments[0].click();', import_link)
            time.sleep(1.5)

            fld = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea, #TextSource_text')))
            fld.click()
            time.sleep(0.2)
            self._js_paste(driver, fld, text)
            time.sleep(0.8)
            try:
                split_sel = driver.find_element(By.CSS_SELECTOR,
                    'select[name="TextSource[split_type]"], select#TextSource_split_type')
                Select(split_sel).select_by_value('0')
            except: pass
            time.sleep(0.3)
            btn_next = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                "button.btn-primary.pull-right, button[type='submit'].btn-primary")))
            driver.execute_script('arguments[0].click();', btn_next)
            time.sleep(2)

            chk = wait.until(EC.presence_of_element_located((By.ID, 'set_translate')))
            if not chk.is_selected():
                driver.execute_script('arguments[0].click();', chk)
            time.sleep(0.5)

            btn_save = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                "button.btn-primary.pull-right.save, button.save.btn-primary")))
            driver.execute_script('arguments[0].click();', btn_save)
            time.sleep(3)
            return True
        except Exception as e:
            self.log(f'Ошибка публикации главы на RuLate: {e}')
            return False

    def _delete_chapter_from_rulate(self, driver, wait, rulate_url, title):
        """Удаляет ОДНУ главу с RuLate по названию: открывает страницу книги,
        в таблице «Оглавление» ищет строку с этим названием (class="chapter_row"),
        нажимает на карандашик (иконка ".icon-pencil", подсказка "Редактировать") —
        под строкой раскрывается форма редактирования главы с тремя кнопками:
        "Сохранить" (btn-primary), "Удалить" (id="btn-remove", onclick="E.rm()")
        и "Отмена" (onclick="CE.cancel()"). Нажимает именно "Удалить".
        Возвращает True при успехе."""
        try:
            driver.get(rulate_url)
            time.sleep(2.5)
            title_lit = self._xpath_literal(title)

            # Строка с нужной главой в таблице оглавления, найденная по названию
            row = wait.until(EC.presence_of_element_located((
                By.XPATH,
                f"//tr[contains(@class,'chapter_row')][.//td[contains(normalize-space(.), {title_lit})]]"
                f" | //tr[.//td[contains(normalize-space(.), {title_lit})]]"
            )))
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', row)
            time.sleep(0.3)

            # Карандашик "Редактировать" внутри этой строки
            pencil = row.find_element(By.CSS_SELECTOR, 'i.icon-pencil, a i.icon-pencil, [title="Редактировать"] i.icon-pencil')
            driver.execute_script('arguments[0].click();', pencil)
            time.sleep(1.3)

            # После клика раскрывается форма редактирования. Кнопка удаления
            # имеет id="btn-remove" и onclick="E.rm()" — ищем именно её, а не
            # кнопку "Отмена" (onclick="CE.cancel()") рядом с ней.
            del_btn = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, '#btn-remove, button[onclick="E.rm()"], button[onclick*="E.rm"]'
            )))
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', del_btn)
            driver.execute_script('arguments[0].click();', del_btn)
            time.sleep(0.8)

            # На случай, если сайт показывает нативное окно подтверждения confirm()
            try:
                driver.switch_to.alert.accept()
            except Exception:
                pass
            time.sleep(2)
            return True
        except Exception as e:
            self.log(f'Ошибка удаления главы с RuLate: {e}')
            return False

    @staticmethod
    def _xpath_literal(s):
        """Безопасно оборачивает строку в XPath-литерал, даже если в ней
        встречаются одинарные и/или двойные кавычки."""
        s = s or ''
        if "'" not in s:
            return f"'{s}'"
        if '"' not in s:
            return f'"{s}"'
        parts = s.split("'")
        return "concat('" + "', \"'\", '".join(parts) + "')"

    def _js_paste(self, driver, element, text):
        """Вставляет текст в поле (textarea/input/contenteditable) напрямую через JS,
        НЕ используя системный буфер обмена ОС. Это полностью изолирует работу скрипта
        от того, что пользователь копирует у себя на компьютере в этот момент, и наоборот —
        скрипт больше не трогает и не перезаписывает настоящий буфер обмена пользователя."""
        driver.execute_script(
            """
            var el = arguments[0], text = arguments[1];
            el.focus();
            try {
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, text);
            } catch (e) {
                // Фоллбек для случаев, когда execCommand недоступен
                if ('value' in el) {
                    el.value = text;
                } else {
                    el.innerText = text;
                }
            }
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            """,
            element, text
        )

    def check_rate_limit(self, driver):
        """Проверяет наличие ошибки лимита запросов DeepSeek."""
        try:
            page_src = driver.page_source.lower()
            rate_limit_phrases = [
                'rate limit', 'quota exceeded', 'too many requests',
                'you\'ve reached your', 'reached your rate',
                'resource has been exhausted', 'try again later',
                'something went wrong', 'please slow down',
                'request limit', 'daily limit',
            ]
            return any(phrase in page_src for phrase in rate_limit_phrases)
        except:
            return False

    def send_ai(self, driver, text, wait, p_name, is_prompt, wait_time):
        """Отправляет текст в chat.deepseek.com и возвращает ответ через кнопку copy."""
        try:
            # Поле ввода DeepSeek — textarea с id="chat-input" или placeholder
            input_selectors = [
                (By.CSS_SELECTOR, 'textarea#chat-input'),
                (By.CSS_SELECTOR, 'textarea[placeholder]'),
                (By.CSS_SELECTOR, 'div[contenteditable="true"]'),
                (By.CSS_SELECTOR, 'textarea'),
            ]
            textarea = None
            for sel in input_selectors:
                try:
                    el = WebDriverWait(driver, 15).until(EC.presence_of_element_located(sel))
                    if el:
                        textarea = el
                        break
                except:
                    continue
            if not textarea:
                self.log(f'[{p_name}] Поле ввода DeepSeek не найдено!')
                return ''

            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', textarea)

            # Считаем кнопки copy ДО отправки
            copy_xpath = (
                '//div[contains(@class,"ds-icon") and .//*[local-name()="svg"]]' 
                '[ancestor::div[contains(@class,"action") or contains(@class,"copy")]]' 
                ' | //button[contains(@class,"copy")]' 
                ' | //*[@data-testid="copy-button"]' 
            )
            # Xpath для блоков ответа и xpath кнопки Stop
            msg_xpath = '//div[contains(@class,"ds-markdown") or contains(@class,"markdown-body") or contains(@class,"_a_e6bf8")]'
            stop_xpath = (
                '//button[@aria-label="Stop" or @aria-label="Stop generating"]'
                ' | //div[@role="button" and contains(@class,"stop")]'
                ' | //button[.//*[local-name()="rect" and @width="10"]]'
            )

            # Вставляем текст через буфер обмена (Ctrl+V) — DeepSeek поддерживает paste.
            # ВАЖНО: конвертация в файл, которая раньше происходила, была вызвана не
            # самим способом вставки, а огромным размером промта (промт-файл рос
            # без остановки из-за бага с дозаписью глоссария — см. функцию
            # append_new_glossary_terms). Теперь, когда промт-файл больше не
            # раздувается до мегабайт, обычная вставка через буфер обмена
            # передаёт текст как текст, а не как файл.
            with CLIPBOARD_LOCK:
                pyperclip.copy(text)
                actions = ActionChains(driver)
                actions.move_to_element(textarea).click().perform()
                time.sleep(0.3)
                actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                time.sleep(0.2)
                actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(1.0)

            def _still_in_textarea():
                """Проверяет, остался ли текст в поле ввода (значит, отправка
                не сработала)."""
                try:
                    val = driver.execute_script(
                        "var el = arguments[0]; return ('value' in el) ? el.value : el.innerText;",
                        textarea
                    ) or ''
                    return len(val.strip()) > 10
                except:
                    return False

            # Отправляем — сначала Enter (DeepSeek: Enter = отправить)
            try:
                textarea.send_keys(Keys.ENTER)
            except:
                try:
                    ActionChains(driver).move_to_element(textarea).send_keys(Keys.ENTER).perform()
                except:
                    pass
            time.sleep(1.0)

            # Фоллбек — если после Enter текст всё ещё стоит в поле ввода (не
            # отправился сам), явно ищем кнопку отправки и кликаем по ней через JS.
            # Это устраняет ситуацию, когда промт "зависает" в поле и не уходит.
            if _still_in_textarea():
                send_btn_xpaths = [
                    '//button[@aria-label="Send message" or @aria-label="Send"]',
                    '//*[@data-testid="send-button" or @data-testid="chat-send-button"]',
                    '//div[@role="button" and (contains(@aria-label,"Send") or contains(@class,"send"))]',
                    '//button[contains(@class,"send") and not(contains(@class,"stop"))]',
                ]
                for _bx in send_btn_xpaths:
                    try:
                        btns = [b for b in driver.find_elements(By.XPATH, _bx)
                                if b.is_displayed() and b.is_enabled()]
                        if btns:
                            driver.execute_script('arguments[0].click();', btns[-1])
                            time.sleep(1.0)
                            break
                    except:
                        continue
                # Если и кнопка не нашлась/не помогла — пробуем Enter ещё раз
                if _still_in_textarea():
                    try:
                        textarea.send_keys(Keys.ENTER)
                    except:
                        pass
                    time.sleep(1.0)

            if is_prompt:
                # Ждём что DeepSeek начал отвечать, потом ждём конца
                time.sleep(3)
                for _w in range(90):
                    if STOP_EVENT.is_set(): return None
                    try:
                        # Кнопка Stop в DeepSeek — svg с квадратом внутри или aria-label
                        stop_btns = driver.find_elements(By.XPATH,
                            '//button[@aria-label="Stop" or @aria-label="Stop generating"]' 
                            ' | //div[@role="button" and contains(@class,"stop")]' 
                            ' | //button[.//*[local-name()="rect" and @width="10"]]' 
                        )
                        if not stop_btns:
                            break
                    except:
                        break
                    time.sleep(1)
                return 'OK'

            # Сбрасываем буфер обмена уникальной меткой
            sentinel = f'__WAITING_RESPONSE_{time.time()}__'
            with CLIPBOARD_LOCK:
                pyperclip.copy(sentinel)

            # Ждём начальную паузу
            time.sleep(wait_time)

            def scroll_chat_to_bottom():
                try:
                    driver.execute_script('''
                        var chat = document.querySelector(
                            "div.dad65929, div[class*=chat-content], " +
                            "div[class*=conversation], div._7f0aee40, " +
                            "div[class*=message-list]"
                        );
                        if (chat) chat.scrollTop = chat.scrollHeight + 9999;
                        window.scrollTo(0, document.body.scrollHeight + 9999);
                    ''')
                except: pass

            for _outer in range(45):
                if STOP_EVENT.is_set(): return None
                try:
                    try: driver.switch_to.alert.accept()
                    except: pass

                    # Проверяем ошибки DeepSeek
                    try:
                        page_src = driver.page_source.lower()
                        rate_limit_phrases = [
                            "please slow down", "too many requests", "rate limit",
                            "daily limit", "request limit", "try again later",
                            "something went wrong"
                        ]
                        if any(p in page_src for p in rate_limit_phrases):
                            return '__RATE_LIMIT__'
                    except:
                        pass

                    # Шаг 1: ждём появления кнопки Stop (DeepSeek начал генерировать)
                    stop_appeared = False
                    for _s in range(30):
                        if STOP_EVENT.is_set(): return None
                        try:
                            if driver.find_elements(By.XPATH, stop_xpath):
                                stop_appeared = True
                                break
                        except: pass
                        time.sleep(1)

                    # Если Stop не появился — возможно DeepSeek уже сгенерировал мгновенно,
                    # продолжаем в любом случае
                    # Шаг 2: ждём исчезновения кнопки Stop (генерация закончена)
                    for _w in range(120):
                        if STOP_EVENT.is_set(): return None
                        try:
                            if not driver.find_elements(By.XPATH, stop_xpath):
                                break
                        except:
                            break
                        if _w % 3 == 0:
                            scroll_chat_to_bottom()
                        time.sleep(1)

                    # Финальный скролл + пауза
                    scroll_chat_to_bottom()
                    time.sleep(1.5)

                    # Ищем кнопку copy у последнего ответа DeepSeek
                    # DeepSeek показывает кнопку copy при наведении на блок ответа
                    scroll_chat_to_bottom()
                    time.sleep(0.5)

                    # Берём текст последнего ответа DeepSeek напрямую через JS
                    # (надёжнее чем кнопка copy которая требует hover)
                    try:
                        last_text = driver.execute_script('''
                            // Ищем все блоки с ответом ассистента
                            var selectors = [
                                "div.ds-markdown",
                                "div.markdown-body", 
                                ".assistant-message div[class*=content]",
                                "div[data-virtual-list-item-key] div[class*=assistant] div[class*=content]",
                                ".ds-message-container div.ds-markdown",
                            ];
                            for (var s of selectors) {
                                var els = document.querySelectorAll(s);
                                if (els.length) return els[els.length-1].innerText;
                            }
                            // fallback: последний div с большим текстом
                            var all = document.querySelectorAll("div[class*=\'4f98f79\'], div[class*=\'63c77b1\']");
                            if (all.length) return all[all.length-1].innerText;
                            return \'\';
                        ''')
                        if last_text and len(last_text.strip()) > 80:
                            return last_text.strip()
                    except: pass

                    # Если JS не сработал — пробуем кнопку copy через hover
                    msgs = driver.find_elements(By.XPATH, msg_xpath)
                    if not msgs:
                        time.sleep(5)
                        continue
                    last_msg = msgs[-1]
                    try:
                        ActionChains(driver).move_to_element(last_msg).perform()
                        time.sleep(1.0)
                    except: pass

                    # DeepSeek: кнопки под ответом — первая кнопка в блоке actions последнего сообщения
                    # Классы из devtools: ds-button ds-button--iconLabelTertiary ds-button-icon
                    copy_btn = None
                    copy_xpaths = [
                        # Первая кнопка в панели действий последнего assistant-сообщения (copy = первая)
                        '(//div[contains(@class,"_4f98f79") or contains(@class,"_63c77b1")])[last()]//button[contains(@class,"ds-button")][1]',
                        # По aria-label
                        '(//button[@aria-label="Copy" or @aria-label="copy" or @title="Copy"])[last()]',
                        # ds-button с svg внутри в последнем сообщении
                        '(//div[@data-virtual-list-item-key])[last()]//button[contains(@class,"ds-button")][1]',
                        # Любая кнопка ds-button-icon в последнем сообщении
                        '(//div[contains(@class,"ds-button--iconLabelTertiary")])[last()]',
                    ]
                    for cp_xpath in copy_xpaths:
                        try:
                            cp_els = driver.find_elements(By.XPATH, cp_xpath)
                            if cp_els:
                                copy_btn = cp_els[-1]
                                break
                        except:
                            continue

                    if copy_btn:
                        with CLIPBOARD_LOCK:
                            pyperclip.copy(sentinel)
                            driver.execute_script(
                                'arguments[0].scrollIntoView({block:"center"}); arguments[0].click();',
                                copy_btn
                            )
                            res = sentinel
                            for _c in range(20):
                                time.sleep(0.5)
                                res = pyperclip.paste().strip()
                                if res and res != sentinel and len(res) > 80:
                                    break
                            if res and res != sentinel and len(res) > 80:
                                return res

                    time.sleep(5)

                except:
                    pass
                time.sleep(5)
        except:
            pass
        return ''

if __name__ == '__main__':
    App().mainloop()
