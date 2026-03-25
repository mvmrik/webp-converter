import os
import pathlib
import logging
import shutil
import threading
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

LOG_FILE = str(pathlib.Path.home() / "webp_converter.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}


def _fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / 1024 / 1024:.1f} MB"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WebP Converter")
        self.geometry("720x640")
        self.minsize(600, 580)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)
        self._converting = False
        self._build_ui()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="WebP Converter", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        # Folder row
        ff = ctk.CTkFrame(self)
        ff.grid(row=1, column=0, padx=20, pady=8, sticky="ew")
        ff.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ff, text="Папка:").grid(row=0, column=0, padx=12, pady=12)
        self._folder_var = ctk.StringVar()
        ctk.CTkEntry(
            ff,
            textvariable=self._folder_var,
            placeholder_text="Изберете папка с изображения…",
        ).grid(row=0, column=1, padx=8, pady=12, sticky="ew")
        ctk.CTkButton(ff, text="Избери", width=90, command=self._browse).grid(
            row=0, column=2, padx=12, pady=12
        )
        ctk.CTkLabel(
            ff,
            text="Внимание: влезте в папката с двойно кликване, после натиснете OK",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")

        # Settings row
        sf = ctk.CTkFrame(self)
        sf.grid(row=2, column=0, padx=20, pady=8, sticky="ew")
        sf.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(sf, text="Качество:").grid(row=0, column=0, padx=12, pady=12)
        self._quality_var = ctk.IntVar(value=90)
        self._quality_label = ctk.CTkLabel(sf, text="90", width=35)
        ctk.CTkSlider(
            sf,
            from_=0,
            to=100,
            variable=self._quality_var,
            number_of_steps=100,
            command=lambda v: self._quality_label.configure(text=str(int(float(v)))),
        ).grid(row=0, column=1, padx=8, pady=12, sticky="ew")
        self._quality_label.grid(row=0, column=2, padx=12, pady=12)

        self._transp_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            sf, text="Запази прозрачност", variable=self._transp_var
        ).grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 6), sticky="w")

        self._delete_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            sf, text="Изтриване на оригинала", variable=self._delete_var
        ).grid(row=2, column=0, columnspan=3, padx=12, pady=(0, 12), sticky="w")

        # Prefix row
        pxf = ctk.CTkFrame(self)
        pxf.grid(row=3, column=0, padx=20, pady=8, sticky="ew")
        pxf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pxf, text="Префикс:").grid(row=0, column=0, padx=12, pady=12)
        self._prefix_var = ctk.StringVar()
        ctk.CTkEntry(
            pxf,
            textvariable=self._prefix_var,
            placeholder_text="Незадължително — напр. site1",
        ).grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        self._rename_only_var = ctk.BooleanVar(value=False)
        self._rename_only_cb = ctk.CTkCheckBox(
            pxf,
            text="Само преименуване",
            variable=self._rename_only_var,
            state="disabled",
        )
        self._rename_only_cb.grid(
            row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="w"
        )

        self._prefix_var.trace_add("write", self._on_prefix_change)

        # Start button
        self._btn = ctk.CTkButton(
            self,
            text="Старт",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=("#2d9e52", "#2d9e52"),
            hover_color=("#246e3a", "#246e3a"),
            command=self._start,
        )
        self._btn.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        # Progress row
        pf = ctk.CTkFrame(self)
        pf.grid(row=5, column=0, padx=20, pady=(0, 8), sticky="ew")
        pf.grid_columnconfigure(0, weight=1)
        self._bar = ctk.CTkProgressBar(pf)
        self._bar.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="ew")
        self._bar.set(0)
        self._status = ctk.CTkLabel(pf, text="Готов")
        self._status.grid(row=1, column=0, padx=12, pady=(0, 10))

        # Log area
        lf = ctk.CTkFrame(self)
        lf.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="nsew")
        lf.grid_columnconfigure(0, weight=1)
        lf.grid_rowconfigure(0, weight=1)
        self._log_box = ctk.CTkTextbox(lf)
        self._log_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # --------------------------------------------------------- UI helpers --

    def _browse(self):
        folder = filedialog.askdirectory(title="Изберете папка с изображения")
        if folder:
            self._folder_var.set(folder)

    def _on_prefix_change(self, *_):
        has_prefix = bool(self._prefix_var.get().strip())
        if has_prefix:
            self._rename_only_cb.configure(state="normal")
        else:
            self._rename_only_var.set(False)
            self._rename_only_cb.configure(state="disabled")

    def _log(self, msg: str):
        self.after(0, self._append, msg)

    def _append(self, msg: str):
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")

    def _set_progress(self, value: float, text: str):
        def _do(v=value, t=text):
            self._bar.set(v)
            self._status.configure(text=t)
        self.after(0, _do)

    # ------------------------------------------------------- Conversion --

    def _start(self):
        if self._converting:
            return
        folder = self._folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            self._append("Грешка: изберете валидна папка.")
            return
        self._converting = True
        self._btn.configure(state="disabled", text="Работи…")
        self._bar.set(0)
        self._log_box.delete("1.0", "end")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        folder = self._folder_var.get().strip()
        quality = self._quality_var.get()
        preserve = self._transp_var.get()
        delete_orig = self._delete_var.get()
        prefix = self._prefix_var.get().strip()
        rename_only = self._rename_only_var.get() and bool(prefix)

        parts = []
        if rename_only:
            parts.append(f"само преименуване с префикс='{prefix}'")
        else:
            parts.append(f"качество={quality}")
            parts.append("прозрачност=" + ("запазена" if preserve else "не запазена"))
            if prefix:
                parts.append(f"префикс='{prefix}'")
        if delete_orig:
            parts.append("оригиналът ще бъде изтрит")

        logging.info(f"Start: folder={folder} " + ", ".join(parts))
        self._log("Начало: " + ", ".join(parts))

        done, total = self._process(folder, quality, preserve, delete_orig, prefix, rename_only)
        logging.info(f"Done: {done}/{total}")
        self.after(0, self._done, done, total, rename_only)

    def _done(self, done: int, total: int, rename_only: bool):
        self._bar.set(1.0)
        verb = "преименувани" if rename_only else "конвертирани"
        self._status.configure(text=f"Готово: {done}/{total} файла {verb}")
        self._append(f"\nГотово! {done}/{total} файла {verb}.")
        self._converting = False
        self._btn.configure(state="normal", text="Старт")

    def _prepare_output_folder(self, input_folder: str) -> str | None:
        parent = os.path.dirname(input_folder)
        name = os.path.basename(input_folder)
        new_folder = os.path.join(parent, f"new_{name}")

        if os.path.exists(new_folder):
            msg = f"Грешка: '{new_folder}' вече съществува — моля изтрийте я."
            logging.error(msg)
            self._log(msg)
            return None

        try:
            os.makedirs(new_folder)
            logging.info(f"Created: {new_folder}")
            self._log(f"Създадена папка: new_{name}")
        except Exception as e:
            msg = f"Грешка при създаване на папка: {e}"
            logging.error(msg)
            self._log(msg)
            return None

        return new_folder

    def _process(
        self,
        input_folder: str,
        quality: int,
        preserve: bool,
        delete_orig: bool,
        prefix: str,
        rename_only: bool,
    ):
        new_folder = self._prepare_output_folder(input_folder)
        if not new_folder:
            return 0, 0

        total = sum(
            1
            for _, _, files in os.walk(input_folder)
            for f in files
            if pathlib.Path(f).suffix.lower() in SUPPORTED_EXT
        )
        self._log(f"Намерени {total} поддържани файла.")

        done = 0
        current = 0

        for root, _, files in os.walk(input_folder):
            rel = os.path.relpath(root, input_folder)
            dest_dir = os.path.join(new_folder, rel)
            os.makedirs(dest_dir, exist_ok=True)

            for filename in files:
                p = pathlib.Path(filename)
                ext = p.suffix.lower()
                if ext not in SUPPORTED_EXT:
                    self._log(f"  Пропуснат: {filename}")
                    logging.info(f"Skipped: {filename}")
                    continue

                current += 1
                src = os.path.join(root, filename)
                size_before = os.path.getsize(src)

                if rename_only:
                    out_name = f"{prefix}_{p.stem}{ext}"
                    dst = os.path.join(dest_dir, out_name)
                    try:
                        shutil.copy2(src, dst)
                        size_after = os.path.getsize(dst)
                        done += 1
                        pct = current / total if total > 0 else 1.0
                        msg = (
                            f"  OK: {filename} → {out_name}"
                            f"  ({_fmt_size(size_before)})"
                            f"  ({current}/{total}, {pct*100:.0f}%)"
                        )
                        logging.info(msg.strip())
                        self._log(msg)
                        self._set_progress(pct, f"{current}/{total} ({pct*100:.0f}%)")
                    except Exception as e:
                        err = f"  Грешка: {filename}: {e}"
                        logging.error(err.strip())
                        self._log(err)
                else:
                    out_name = (f"{prefix}_{p.stem}" if prefix else p.stem) + ".webp"
                    dst = os.path.join(dest_dir, out_name)
                    try:
                        img = Image.open(src)
                        if not preserve and img.mode in ("RGBA", "LA"):
                            bg = Image.new("RGB", img.size, (255, 255, 255))
                            bg.paste(img, mask=img.split()[-1])
                            img = bg
                        img.save(dst, "WEBP", quality=quality)
                        size_after = os.path.getsize(dst)
                        saving = (1 - size_after / size_before) * 100 if size_before else 0
                        done += 1
                        pct = current / total if total > 0 else 1.0
                        msg = (
                            f"  OK: {filename} → {out_name}"
                            f"  {_fmt_size(size_before)} → {_fmt_size(size_after)}"
                            f"  (-{saving:.0f}%)"
                            f"  ({current}/{total}, {pct*100:.0f}%)"
                        )
                        logging.info(msg.strip())
                        self._log(msg)
                        self._set_progress(pct, f"{current}/{total} ({pct*100:.0f}%)")
                    except Exception as e:
                        err = f"  Грешка: {filename}: {e}"
                        logging.error(err.strip())
                        self._log(err)

        if delete_orig:
            try:
                shutil.rmtree(input_folder)
                logging.info(f"Deleted original: {input_folder}")
                self._log(f"  Оригиналната папка изтрита: {os.path.basename(input_folder)}")
            except Exception as e:
                err = f"  Грешка при изтриване на оригинала: {e}"
                logging.error(err)
                self._log(err)

        return done, total


if __name__ == "__main__":
    app = App()
    app.mainloop()
