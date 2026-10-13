import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import os
import sys
import json
import uuid
import shutil

def app_dir():
    if getattr(sys, 'frozen', False):
        d = os.path.dirname(sys.executable)
        if os.path.basename(d) == 'dist':
            return os.path.dirname(d)
        return d
    return os.path.dirname(os.path.abspath(__file__))

BASE = app_dir()
PROFILES_JSON = os.path.join(BASE, 'profiles.json')
BOT_PATH = os.path.join(BASE, 'nakrutka_bot.exe')
PROF_DIR = os.path.join(BASE, 'profiles')

os.makedirs(PROF_DIR, exist_ok=True)

class RulateApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Rulate Накрутка')
        self.root.geometry('720x620')
        self.root.configure(bg='#1a1a2e')
        self.profiles = []
        self.process = None
        self.setup_ui()
        self.load()

    def setup_ui(self):
        main = tk.Frame(self.root, bg='#1a1a2e', padx=15, pady=15)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(main, text='Rulate Накрутка', font=('Segoe UI', 20, 'bold'),
                 fg='#e94560', bg='#1a1a2e').pack(anchor=tk.W, pady=(0, 10))

        pf = tk.LabelFrame(main, text=' Профили ', font=('Segoe UI', 10),
                           fg='#aaa', bg='#1a1a2e', padx=10, pady=8, bd=1, relief=tk.SOLID)
        pf.pack(fill=tk.BOTH, pady=(0, 10))

        btn_row = tk.Frame(pf, bg='#1a1a2e')
        btn_row.pack(fill=tk.X, pady=(0, 5))

        tk.Button(btn_row, text='+ Добавить профиль', font=('Segoe UI', 9),
                  bg='#0f3460', fg='#e94560', padx=10, pady=2, bd=0, cursor='hand2',
                  command=self.add_profile).pack(side=tk.LEFT)

        tk.Button(btn_row, text='Удалить выбранные', font=('Segoe UI', 9),
                  bg='#0f3460', fg='#888', padx=10, pady=2, bd=0, cursor='hand2',
                  command=self.delete_selected).pack(side=tk.LEFT, padx=(5, 0))

        self.status_label = tk.Label(btn_row, text='', font=('Segoe UI', 8),
                                     bg='#1a1a2e', fg='#666')
        self.status_label.pack(side=tk.RIGHT)

        cv_frame = tk.Frame(pf, bg='#0f3460', bd=0, highlightthickness=0)
        cv_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(cv_frame, bg='#0f3460', bd=0, highlightthickness=0, height=140)
        sb = tk.Scrollbar(cv_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg='#0f3460')
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0, 0), window=self.inner, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        uf = tk.LabelFrame(main, text=' Ссылка на книгу ', font=('Segoe UI', 10),
                           fg='#aaa', bg='#1a1a2e', padx=10, pady=5, bd=1, relief=tk.SOLID)
        uf.pack(fill=tk.X, pady=(0, 10))

        self.url_entry = tk.Entry(uf, font=('Segoe UI', 11), bg='#0f3460', fg='#fff',
                                  insertbackground='#fff', bd=0, highlightthickness=1,
                                  highlightcolor='#1a4a7a', highlightbackground='#1a4a7a')
        self.url_entry.pack(fill=tk.X, ipady=6, pady=5)
        self.url_entry.insert(0, 'https://tl.rulate.ru/book/')

        self.start_btn = tk.Button(main, text='ЗАПУСТИТЬ', font=('Segoe UI', 13, 'bold'),
                                   bg='#e94560', fg='#fff', padx=20, pady=8, bd=0, cursor='hand2',
                                   command=self.start_bot)
        self.start_btn.pack(pady=(0, 10))

        lf = tk.LabelFrame(main, text=' Лог ', font=('Segoe UI', 10),
                           fg='#aaa', bg='#1a1a2e', padx=5, pady=5, bd=1, relief=tk.SOLID)
        lf.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(lf, font=('Consolas', 10), bg='#0a0a1a',
                                                   fg='#0f0', insertbackground='#0f0', bd=0,
                                                   relief=tk.FLAT, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    def load(self):
        self.profiles = []
        if os.path.exists(PROFILES_JSON):
            with open(PROFILES_JSON, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            for p in raw:
                self.profiles.append({
                    'name': p['name'],
                    'path': p['path'],
                    'logged': p.get('logged', False),
                    'checked': tk.BooleanVar(value=True)
                })
        self.render()
        self.status_label.config(text=f'Папка: {BASE}')

    def save(self):
        data = []
        for p in self.profiles:
            data.append({
                'name': p['name'],
                'path': p['path'],
                'logged': p['logged']
            })
        with open(PROFILES_JSON, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def render(self):
        for w in self.inner.winfo_children():
            w.destroy()
        if not self.profiles:
            tk.Label(self.inner, text='Нет профилей. Нажми "+ Добавить профиль"',
                     bg='#0f3460', fg='#666', font=('Segoe UI', 10), padx=10, pady=20).pack()
            return

        for i, prof in enumerate(self.profiles):
            row = tk.Frame(self.inner, bg='#0f3460')
            row.pack(fill=tk.X, pady=2)

            cb = tk.Checkbutton(row, variable=prof['checked'], bg='#0f3460', fg='#ddd',
                                selectcolor='#0f3460', activebackground='#0f3460',
                                activeforeground='#fff', bd=0)
            cb.pack(side=tk.LEFT)

            tk.Label(row, text=prof['name'], font=('Segoe UI', 10, 'bold'),
                     bg='#0f3460', fg='#ddd', padx=5).pack(side=tk.LEFT)

            st = '✅' if prof['logged'] else '❌'
            tk.Label(row, text=st, font=('Segoe UI', 10), bg='#0f3460', fg='#aaa').pack(side=tk.LEFT, padx=(5, 0))

            tk.Button(row, text='Открыть Rulate', font=('Segoe UI', 8),
                      bg='#1a4a7a', fg='#fff', padx=6, pady=1, bd=0, cursor='hand2',
                      command=lambda idx=i: self.open_rulate(idx)).pack(side=tk.RIGHT, padx=(2, 0))

            tk.Button(row, text='Проверить', font=('Segoe UI', 8),
                      bg='#1a4a7a', fg='#fff', padx=6, pady=1, bd=0, cursor='hand2',
                      command=lambda idx=i: self.check_profile(idx)).pack(side=tk.RIGHT, padx=(2, 0))

            tk.Frame(self.inner, bg='#0a2740', height=1).pack(fill=tk.X, pady=1)

        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def add_profile(self):
        d = tk.Toplevel(self.root)
        d.title('Новый профиль')
        d.geometry('350x110')
        d.configure(bg='#1a1a2e')
        d.resizable(False, False)
        d.transient(self.root)
        d.grab_set()

        tk.Label(d, text='Название профиля:', font=('Segoe UI', 10),
                 fg='#aaa', bg='#1a1a2e').pack(pady=(12, 5), padx=15, anchor=tk.W)

        entry = tk.Entry(d, font=('Segoe UI', 11), bg='#0f3460', fg='#fff',
                         insertbackground='#fff', bd=0, highlightthickness=1,
                         highlightcolor='#1a4a7a', highlightbackground='#1a4a7a')
        entry.pack(fill=tk.X, padx=15, ipady=4)
        entry.focus_set()

        def do_save():
            name = entry.get().strip()
            if not name:
                messagebox.showwarning('', 'Введи название')
                return
            for p in self.profiles:
                if p['name'] == name:
                    messagebox.showwarning('', 'Такое имя уже есть')
                    return
            dir_name = 'rp_' + name.replace(' ', '_') + '_' + str(uuid.uuid4())[:6]
            self.profiles.append({
                'name': name,
                'path': os.path.join(PROF_DIR, dir_name),
                'logged': False,
                'checked': tk.BooleanVar(value=True)
            })
            self.save()
            self.render()
            d.destroy()

        tk.Button(d, text='Создать', font=('Segoe UI', 10), bg='#e94560', fg='#fff',
                  padx=20, pady=4, bd=0, cursor='hand2', command=do_save).pack(pady=(8, 0))
        entry.bind('<Return>', lambda e: do_save())

    def delete_selected(self):
        idxs = [i for i, p in enumerate(self.profiles) if p['checked'].get()]
        if not idxs:
            messagebox.showinfo('', 'Нет выбранных')
            return
        if not messagebox.askyesno('', f'Удалить {len(idxs)} профиль(ей)?'):
            return
        for i in reversed(idxs):
            if os.path.exists(self.profiles[i]['path']):
                shutil.rmtree(self.profiles[i]['path'], ignore_errors=True)
            self.profiles.pop(i)
        self.save()
        self.render()

    def find_chrome(self):
        candidates = [
            'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
            'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
            'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
            'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
            'C:\\Program Files\\Yandex\\YandexBrowser\\Application\\browser.exe',
            os.environ.get('LOCALAPPDATA', '') + '\\Google\\Chrome\\Application\\chrome.exe',
            os.environ.get('LOCALAPPDATA', '') + '\\Yandex\\YandexBrowser\\Application\\browser.exe',
            os.environ.get('LOCALAPPDATA', '') + '\\Microsoft\\Edge\\Application\\msedge.exe',
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def open_rulate(self, idx):
        prof = self.profiles[idx]
        os.makedirs(prof['path'], exist_ok=True)
        chrome = self.find_chrome()
        if not chrome:
            messagebox.showerror('', 'Chrome не найден')
            return
        subprocess.Popen([chrome, f'--user-data-dir={prof["path"]}', '--no-sandbox', 'https://tl.rulate.ru/'])
        self.log('Открыт Rulate в профиле "' + prof['name'] + '". Войди и закрой Chrome')

    def check_profile(self, idx):
        prof = self.profiles[idx]
        if not os.path.exists(prof['path']):
            messagebox.showinfo('', 'Сначала открой Rulate')
            return
        self.log('Проверка "' + prof['name'] + '"...')

        def check():
            chrome = self.find_chrome()
            if not chrome:
                self.log('Chrome не найден')
                return
            script = '''
const p = require('puppeteer-core');
async function main() {
  const b = await p.launch({executablePath: process.argv[2], headless: true, userDataDir: process.argv[3], args: ['--no-sandbox']});
  const page = await b.newPage();
  await page.goto('https://tl.rulate.ru/', {waitUntil: 'networkidle2', timeout: 20000});
  await new Promise(r => setTimeout(r, 2000));
  const r = await page.evaluate("document.querySelector('input[name=\\\"login[login]\\\"]') === null ? 'OK' : 'NO'");
  console.log(r);
  await b.close();
}
main().catch(e => { console.log('ERR:'+e.message); process.exit(1); });
'''
            sp = os.path.join(BASE, '_chk.js')
            with open(sp, 'w', encoding='utf-8') as f:
                f.write(script)
            try:
                r = subprocess.run(['node', sp, chrome, prof['path']],
                                   capture_output=True, text=True, timeout=30000)
                if 'OK' in r.stdout:
                    prof['logged'] = True
                    self.log('✅ ' + prof['name'] + ' — авторизован')
                else:
                    prof['logged'] = False
                    self.log('❌ ' + prof['name'] + ' — не авторизован')
                self.save()
                self.render()
            except Exception as e:
                self.log('Ошибка: ' + str(e))
            finally:
                if os.path.exists(sp):
                    os.remove(sp)

        threading.Thread(target=check, daemon=True).start()

    def start_bot(self):
        url = self.url_entry.get().strip()
        if not url or 'tl.rulate.ru/book/' not in url:
            self.log('Ошибка: некорректная ссылка')
            return
        selected = [p for p in self.profiles if p['checked'].get()]
        if not selected:
            self.log('Ошибка: выбери профиль')
            return
        not_logged = [p['name'] for p in selected if not p['logged']]
        if not_logged and not messagebox.askyesno('', 'Профили не проверены:\n' + '\n'.join(not_logged) + '\n\nЗапустить?'):
            return

        self.start_btn.config(state=tk.DISABLED, text='ВЫПОЛНЯЕТСЯ...')
        self.log('Запуск для ' + str(len(selected)) + ' профилей...')

        paths = '|'.join([p['path'] for p in selected])

        def run():
            try:
                proc = subprocess.Popen([BOT_PATH, paths, url],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding='utf-8', bufsize=1)
                self.process = proc
                for line in proc.stdout:
                    txt = line[4:].rstrip() if line.startswith('LOG:') else line.rstrip()
                    self.log(txt)
                proc.wait()
            except Exception as e:
                self.log('Ошибка: ' + str(e))
            finally:
                self.process = None
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL, text='ЗАПУСТИТЬ'))

        threading.Thread(target=run, daemon=True).start()

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()

    def on_close(self):
        self.save()
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.root.destroy()

if __name__ == '__main__':
    tk.Tk().withdraw()
    root = tk.Tk()
    app = RulateApp(root)
    root.mainloop()