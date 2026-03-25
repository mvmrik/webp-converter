import os
import pathlib
import logging
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

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WebP Converter")
        self.geometry("720x620")
        self.minsize(600, 560)
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
            sf,
            text="Запази прозрачност",
            variable=self._transp_var,
        ).grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 6), sticky="w")

        self._delete_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            sf,
            text="Изтриване на оригинала",
            variable=self._delete_var,
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

        # Convert button
        self._btn = ctk.CTkButton(
            self,
            text="Конвертирай в WebP",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
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

    def _log(self, msg: str):
        """Thread-safe: schedule text append on the main thread."""
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
        self._btn.configure(state="disabled", text="Конвертиране…")
        self._bar.set(0)
        self._log_box.delete("1.0", "end")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        folder = self._folder_var.get().strip()
        quality = self._quality_var.get()
        preserve = self._transp_var.get()
        delete_orig = self._delete_var.get()
        prefix = self._prefix_var.get().strip()
        logging.info(
            f"Start: folder={folder} quality={quality} "
            f"preserve={preserve} delete_orig={delete_orig} prefix='{prefix}'"
        )
        parts = [f"качество={quality}"]
        parts.append("прозрачност=" + ("запазена" if preserve else "не запазена"))
        if prefix:
            parts.append(f"префикс='{prefix}'")
        if delete_orig:
            parts.append("оригиналът ще бъде изтрит")
        self._log("Начало: " + ", ".join(parts))
        converted, total = self._convert(folder, quality, preserve, delete_orig, prefix)
        logging.info(f"Done: {converted}/{total}")
        self.after(0, self._done, converted, total)

    def _done(self, converted: int, total: int):
        self._bar.set(1.0)
        self._status.configure(text=f"Готово: {converted}/{total} файла конвертирани")
        self._append(f"\nГотово! Конвертирани {converted}/{total} файла.")
        self._converting = False
        self._btn.configure(state="normal", text="Конвертирай в WebP")

    def _prepare_folders(self, input_folder: str):
        parent = os.path.dirname(input_folder)
        name = os.path.basename(input_folder)
        old_folder = os.path.join(parent, f"{name}_old")
        new_folder = os.path.join(parent, name)

        if os.path.exists(old_folder):
            msg = f"Грешка: '{old_folder}' вече съществува — моля преименувайте я."
            logging.error(msg)
            self._log(msg)
            return None, None

        try:
            os.rename(input_folder, old_folder)
            logging.info(f"Renamed to: {old_folder}")
            self._log(f"Оригинална папка преименувана на: {os.path.basename(old_folder)}")
        except Exception as e:
            msg = f"Грешка при преименуване: {e}"
            logging.error(msg)
            self._log(msg)
            return None, None

        try:
            os.makedirs(new_folder, exist_ok=True)
            logging.info(f"Created: {new_folder}")
            self._log(f"Създадена нова папка: {os.path.basename(new_folder)}")
        except Exception as e:
            msg = f"Грешка при създаване на папка: {e}"
            logging.error(msg)
            self._log(msg)
            try:
                os.rename(old_folder, input_folder)
            except Exception:
                pass
            return None, None

        return new_folder, old_folder

    def _convert(
        self,
        input_folder: str,
        quality: int,
        preserve: bool,
        delete_orig: bool,
        prefix: str,
    ):
        new_folder, old_folder = self._prepare_folders(input_folder)
        if not new_folder:
            return 0, 0

        total = sum(
            1
            for _, _, files in os.walk(old_folder)
            for f in files
            if pathlib.Path(f).suffix.lower() in SUPPORTED_EXT
        )
        self._log(f"Намерени {total} поддържани файла.")

        converted = 0
        current = 0

        for root, _, files in os.walk(old_folder):
            rel = os.path.relpath(root, old_folder)
            dest_dir = os.path.join(new_folder, rel)
            os.makedirs(dest_dir, exist_ok=True)

            for filename in files:
                ext = pathlib.Path(filename).suffix.lower()
                if ext not in SUPPORTED_EXT:
                    self._log(f"  Пропуснат: {filename}")
                    logging.info(f"Skipped: {filename}")
                    continue

                current += 1
                src = os.path.join(root, filename)
                stem = pathlib.Path(filename).stem
                out_name = (f"{prefix}_{stem}" if prefix else stem) + ".webp"
                dst = os.path.join(dest_dir, out_name)

                try:
                    img = Image.open(src)

                    if not preserve and img.mode in ("RGBA", "LA"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[-1])
                        img = bg

                    img.save(dst, "WEBP", quality=quality)
                    converted += 1

                    pct = current / total if total > 0 else 1.0
                    msg = f"  OK: {filename} → {out_name}  ({current}/{total}, {pct*100:.0f}%)"
                    logging.info(msg.strip())
                    self._log(msg)
                    self._set_progress(pct, f"{current}/{total} ({pct*100:.0f}%)")

                except Exception as e:
                    err = f"  Грешка: {filename}: {e}"
                    logging.error(err.strip())
                    self._log(err)

        if delete_orig:
            try:
                import shutil
                shutil.rmtree(old_folder)
                logging.info(f"Deleted original: {old_folder}")
                self._log(f"  Оригиналната папка изтрита: {os.path.basename(old_folder)}")
            except Exception as e:
                err = f"  Грешка при изтриване на оригинала: {e}"
                logging.error(err)
                self._log(err)

        return converted, total


if __name__ == "__main__":
    app = App()
    app.mainloop()
