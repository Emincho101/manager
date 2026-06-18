import tkinter as tk
from tkinter import Listbox, Scrollbar, Button, Frame, Entry, Menu, messagebox, Toplevel
import json
import os
import sys
from datetime import datetime

HISTORY_FILE = "history.json"
SETTINGS_FILE = "settings.json"
MAX_DEFAULT = 120

class ClipboardManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Менеджер буфера обмена")
        self.root.geometry("600x480")
        self.root.minsize(400, 300)
        self.root.attributes('-topmost', False)

        self.settings = self.load_settings()
        self.max_history = self.settings.get("max", MAX_DEFAULT)

        self.history = []
        self.pinned = self.settings.get("pinned", [])
        self.load_history()

        self.last_clipboard = self.get_clipboard_text()

        self.build_interface()
        self.refresh_listbox()
        self.check_clipboard()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def get_clipboard_text(self):
        try:
            return self.root.clipboard_get()
        except tk.TclError:
            return ""

    def set_clipboard_text(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"max": MAX_DEFAULT, "pinned": []}

    def save_settings(self):
        self.settings["max"] = self.max_history
        self.settings["pinned"] = self.pinned
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            self.history.append({"text": item, "time": ""})
                        else:
                            self.history.append(item)
                else:
                    self.history = data.get("history", [])
                    self.pinned = data.get("pinned", [])
            except:
                self.history = []

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "history": self.history,
                    "pinned": self.pinned
                }, f, ensure_ascii=False, indent=2)
        except:
            pass

    def build_interface(self):
        top = Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(top, text="Поиск:").pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_listbox())
        Entry(top, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)

        Button(top, text="✕", command=lambda: self.search_var.set("")).pack(side=tk.LEFT)

        self.fav_btn = Button(top, text="★", command=self.toggle_favorite)
        self.fav_btn.pack(side=tk.RIGHT)

        mid = Frame(self.root)
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sb = Scrollbar(mid)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = Listbox(mid, yscrollcommand=sb.set, selectmode=tk.EXTENDED, font=("Consolas", 10))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.listbox.yview)

        self.menu = Menu(self.root, tearoff=0)
        self.menu.add_command(label="Копировать", command=self.copy_selected)
        self.menu.add_command(label="Удалить", command=self.delete_selected)
        self.menu.add_separator()
        self.menu.add_command(label="Закрепить/Открепить", command=self.toggle_favorite)
        self.listbox.bind("<Button-3>", self.show_menu)

        self.listbox.bind("<Double-Button-1>", self.copy_selected)
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.listbox.bind("<Control-a>", lambda e: self.listbox.select_set(0, tk.END))

        bot = Frame(self.root)
        bot.pack(fill=tk.X, padx=10, pady=(0, 10))

        Button(bot, text="Очистить всё", command=self.clear_history).pack(side=tk.LEFT)
        Button(bot, text="Удалить дубликаты", command=self.remove_duplicates).pack(side=tk.LEFT, padx=5)
        Button(bot, text="Экспорт", command=self.export_history).pack(side=tk.LEFT)
        Button(bot, text="Импорт", command=self.import_history).pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(bot, text="", anchor=tk.W)
        self.status.pack(side=tk.RIGHT)

        Button(bot, text="Настройки", command=self.open_settings).pack(side=tk.RIGHT, padx=5)
        Button(bot, text="О программе", command=self.show_about).pack(side=tk.RIGHT)
        Button(bot, text="Обновить", command=self.refresh_listbox).pack(side=tk.RIGHT)

    def get_display_items(self):
        q = self.search_var.get().lower()
        result = []
        for item in reversed(self.pinned):
            text = item["text"] if isinstance(item, dict) else item
            if not q or q in text.lower():
                time_str = ""
                if isinstance(item, dict) and item.get("time"):
                    try:
                        dt = datetime.fromisoformat(item["time"])
                        time_str = dt.strftime("%H:%M") + " "
                    except:
                        pass
                result.append(("📌", time_str + text))
        for item in reversed(self.history):
            text = item["text"] if isinstance(item, dict) else item
            if not q or q in text.lower():
                time_str = ""
                if isinstance(item, dict) and item.get("time"):
                    try:
                        dt = datetime.fromisoformat(item["time"])
                        time_str = dt.strftime("%H:%M") + " "
                    except:
                        pass
                result.append(("", time_str + text))
        return result

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        items = self.get_display_items()
        for prefix, item in items:
            display = item if len(item) <= 100 else item[:100] + "..."
            self.listbox.insert(tk.END, prefix + display)
        total = len(self.history) + len(self.pinned)
        shown = self.listbox.size()
        self.status.config(text=f"Всего: {total}, показано: {shown}")

    def get_selected_real_text(self):
        sel = self.listbox.curselection()
        if not sel:
            return None, None
        idx = sel[0]
        line = self.listbox.get(idx)
        is_pinned = line.startswith("📌")
        clean = line.removeprefix("📌").strip()
        if clean and len(clean) > 6 and clean[2] == ':':
            clean = clean[6:]
        for item in (self.pinned if is_pinned else self.history):
            text = item["text"] if isinstance(item, dict) else item
            if text == clean or (len(clean) >= 95 and text.startswith(clean[:95])):
                return text, is_pinned
        return clean, is_pinned

    def copy_selected(self, event=None):
        text, _ = self.get_selected_real_text()
        if text:
            self.set_clipboard_text(text)
            self.root.title("Скопировано!")
            self.root.after(1000, lambda: self.root.title("Менеджер буфера обмена"))

    def delete_selected(self):
        indices = self.listbox.curselection()
        if not indices:
            return
        for idx in reversed(indices):
            line = self.listbox.get(idx)
            is_pinned = line.startswith("📌")
            clean = line.removeprefix("📌").strip()
            if clean and len(clean) > 6 and clean[2] == ':':
                clean = clean[6:]
            if is_pinned:
                for item in self.pinned:
                    text = item["text"] if isinstance(item, dict) else item
                    if text == clean or (len(clean) >= 95 and text.startswith(clean[:95])):
                        self.pinned.remove(item)
                        break
            else:
                for item in self.history:
                    text = item["text"] if isinstance(item, dict) else item
                    if text == clean or (len(clean) >= 95 and text.startswith(clean[:95])):
                        self.history.remove(item)
                        break
        self.save_all()
        self.refresh_listbox()

    def toggle_favorite(self):
        text, is_pinned = self.get_selected_real_text()
        if text is None:
            return
        if is_pinned:
            for item in self.pinned:
                if (item["text"] if isinstance(item, dict) else item) == text:
                    self.pinned.remove(item)
                    break
            self.history.insert(0, {"text": text, "time": datetime.now().isoformat()})
        else:
            for item in self.history:
                if (item["text"] if isinstance(item, dict) else item) == text:
                    self.history.remove(item)
                    break
            self.pinned.append({"text": text, "time": datetime.now().isoformat()})
        self.save_all()
        self.refresh_listbox()

    def show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def clear_history(self):
        if messagebox.askyesno("Очистка", "Удалить всю историю и закреплённые?"):
            self.history.clear()
            self.pinned.clear()
            self.refresh_listbox()
            self.save_all()

    def remove_duplicates(self):
        if not messagebox.askyesno("Удаление дубликатов", "Удалить повторяющиеся записи, оставив только самые свежие?"):
            return
        seen_texts = {}
        for item in self.history:
            text = item["text"] if isinstance(item, dict) else item
            time = item.get("time", "") if isinstance(item, dict) else ""
            if text not in seen_texts:
                seen_texts[text] = item
            else:
                existing_time = seen_texts[text].get("time", "") if isinstance(seen_texts[text], dict) else ""
                if time and existing_time and time > existing_time:
                    seen_texts[text] = item
        new_history = [seen_texts[text] for text in seen_texts]
        self.history = new_history
        while len(self.history) > self.max_history:
            self.history.pop(0)
        self.save_all()
        self.refresh_listbox()

    def export_history(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Текст", "*.txt")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("=== Закреплённые ===\n")
                for item in self.pinned:
                    text = item["text"] if isinstance(item, dict) else item
                    f.write(text + "\n")
                f.write("=== История ===\n")
                for item in self.history:
                    text = item["text"] if isinstance(item, dict) else item
                    f.write(text + "\n")
            messagebox.showinfo("Готово", "Экспортировано.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def import_history(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("Текст", "*.txt")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            section = None
            for line in lines:
                line = line.strip()
                if line == "=== Закреплённые ===":
                    section = "pinned"
                    continue
                elif line == "=== История ===":
                    section = "history"
                    continue
                if line and section == "pinned":
                    if not any((item["text"] if isinstance(item, dict) else item) == line for item in self.pinned):
                        self.pinned.append({"text": line, "time": datetime.now().isoformat()})
                elif line and section == "history":
                    if not any((item["text"] if isinstance(item, dict) else item) == line for item in self.history):
                        self.history.append({"text": line, "time": datetime.now().isoformat()})
            self.save_all()
            self.refresh_listbox()
            messagebox.showinfo("Готово", "Импортировано.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def open_settings(self):
        win = Toplevel(self.root)
        win.title("Настройки")
        win.geometry("300x150")
        win.resizable(False, False)

        tk.Label(win, text="Макс. записей:").pack(pady=(15, 5))
        var = tk.IntVar(value=self.max_history)
        Entry(win, textvariable=var, width=10).pack()

        def apply():
            try:
                new_val = var.get()
                if new_val > 0:
                    self.max_history = new_val
                    while len(self.history) > self.max_history:
                        self.history.pop(0)
                    self.save_settings()
                    self.refresh_listbox()
                    win.destroy()
                else:
                    messagebox.showwarning("Ошибка", "Число должно быть > 0")
            except:
                messagebox.showwarning("Ошибка", "Введите число")

        Button(win, text="Применить", command=apply).pack(pady=10)

    def show_about(self):
        win = Toplevel(self.root)
        win.title("О программе")
        win.geometry("300x200")
        win.resizable(False, False)
        tk.Label(win, text="Менеджер буфера обмена", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(win, text="Версия 1.2").pack()
        tk.Label(win, text="Автор: [твоё имя]").pack()
        tk.Label(win, text="Следит за буфером, хранит историю.").pack()
        tk.Label(win, text=f"Python {sys.version_info.major}.{sys.version_info.minor}").pack()
        Button(win, text="Закрыть", command=win.destroy).pack(pady=10)

    def add_to_history(self, text):
        text = text.strip()
        if not text or any((item["text"] if isinstance(item, dict) else item) == text for item in self.pinned):
            return
        if self.history:
            last = self.history[-1]
            last_text = last["text"] if isinstance(last, dict) else last
            if last_text == text:
                return
        entry = {"text": text, "time": datetime.now().isoformat()}
        self.history.append(entry)
        while len(self.history) > self.max_history:
            self.history.pop(0)
        self.refresh_listbox()
        self.save_all()

    def save_all(self):
        self.save_history()
        self.save_settings()

    def check_clipboard(self):
        cur = self.get_clipboard_text()
        if cur != self.last_clipboard:
            self.last_clipboard = cur
            self.add_to_history(cur)
        self.root.after(500, self.check_clipboard)

    def on_close(self):
        self.save_all()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ClipboardManager(root)
    root.mainloop()