#!/usr/bin/env python3
# ui_light.py — Pure Tkinter UI, zero extra installs
# Run: python ui_light.py

import os, sys, json, zipfile, threading, subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

os.environ["CUDA_VISIBLE_DEVICES"]  = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BG     = "#0f1117"
BG2    = "#1a1d27"
BG3    = "#222638"
ACCENT = "#4f8ef7"
GREEN  = "#34d399"
TEXT   = "#e2e8f0"
MUTED  = "#64748b"
RED    = "#f87171"
YELLOW = "#fbbf24"
BORDER = "#2d3748"
HOVER  = "#2a3045"

FT_SM  = ("Helvetica", 10)
FT_B   = ("Helvetica", 11, "bold")
FT_TIT = ("Helvetica", 16, "bold")
FT_MON = ("Courier", 10)


def load_thumb(folder, size=110):
    if not HAS_PIL:
        return None
    try:
        photos = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith(('.jpg','.jpeg','.png','.bmp','.webp'))
        ], key=lambda f: os.path.getsize(os.path.join(folder, f)))
        if not photos:
            return None
        img  = Image.open(os.path.join(folder, photos[0])).convert("RGB")
        w, h = img.size
        side = min(w, h)
        img  = img.crop(((w-side)//2,(h-side)//2,(w+side)//2,(h+side)//2))
        img  = img.resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def count_photos(folder):
    if not os.path.exists(folder): return 0
    return len([f for f in os.listdir(folder)
                if f.lower().endswith(('.jpg','.jpeg','.png','.bmp','.webp'))])


def load_meta(folder):
    p = os.path.join(folder, ".meta.json")
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return None


class PersonCard(tk.Frame):
    def __init__(self, parent, name, folder, on_download, **kw):
        super().__init__(parent, bg=BG2,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", **kw)
        self.name=name; self.folder=folder
        self.on_download=on_download; self._img=None
        self._build(); self._hover()

    def _build(self):
        thumb = load_thumb(self.folder)
        if thumb:
            self._img = thumb
            lbl = tk.Label(self, image=thumb, bg=BG3, cursor="hand2")
        else:
            lbl = tk.Label(self, text="👤", font=("Helvetica",36),
                           bg=BG3, fg=MUTED, width=8, height=3, cursor="hand2")
        lbl.pack(padx=10, pady=(10,5), fill="x")
        lbl.bind("<Button-1>", lambda e: self._open())

        tk.Label(self, text=self.name.replace("_"," "),
                 bg=BG2, fg=TEXT, font=FT_B).pack()

        n    = count_photos(self.folder)
        meta = load_meta(self.folder)
        sub  = f"{n} photos"
        if meta and not meta.get("downloaded"):
            sub = f"{meta.get('total',0)} photos · tap ⬇ to download"
        tk.Label(self, text=sub, bg=BG2, fg=MUTED,
                 font=("Helvetica",9)).pack(pady=(0,4))

        self.btn = tk.Button(self, text="⬇  Download",
            bg=BG3, fg=ACCENT, font=("Helvetica",9,"bold"),
            relief="flat", bd=0, padx=8, pady=5, cursor="hand2",
            activebackground=ACCENT, activeforeground="white",
            command=self._dl)
        self.btn.pack(fill="x", padx=10, pady=(0,10))

    def _hover(self):
        def enter(e):
            self.configure(bg=HOVER, highlightbackground=ACCENT)
            for w in self.winfo_children():
                try:
                    if w != self.btn: w.configure(bg=HOVER)
                except: pass
        def leave(e):
            self.configure(bg=BG2, highlightbackground=BORDER)
            for w in self.winfo_children():
                try:
                    w.configure(bg=BG2 if w!=self.btn else BG3)
                except: pass
        self.bind("<Enter>", enter); self.bind("<Leave>", leave)

    def _open(self):
        if os.path.exists(self.folder):
            subprocess.Popen(["xdg-open", self.folder])

    def _dl(self):
        self.btn.configure(text="⏳  Working...", state="disabled")
        if self.on_download:
            self.on_download(self.name, self.folder, self._reset)

    def _reset(self):
        self.btn.configure(text="⬇  Download", state="normal")


class FaceOrganizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Face Organizer")
        self.geometry("1080x700")
        self.minsize(860,560)
        self.configure(bg=BG)
        self._cards=[]; self._cfg=self._load_cfg()
        self._build(); self._reload()

    def _load_cfg(self):
        d = {"output_dir":"output","batch_size":100,
             "eps":0.6,"min_samples":2,"last_link":""}
        try:
            if os.path.exists("data/ui_cfg.json"):
                with open("data/ui_cfg.json") as f: d.update(json.load(f))
        except: pass
        return d

    def _save_cfg(self):
        os.makedirs("data", exist_ok=True)
        with open("data/ui_cfg.json","w") as f: json.dump(self._cfg,f,indent=2)

    def _build(self):
        # header
        bar = tk.Frame(self, bg=BG2, height=52)
        bar.pack(fill="x"); bar.pack_propagate(False)
        tk.Label(bar, text="👤  Face Organizer", bg=BG2, fg=TEXT,
                 font=FT_TIT).pack(side="left", padx=18, pady=10)
        self._st_dot = tk.Label(bar, text="●", bg=BG2, fg=GREEN,
                                font=("Helvetica",16))
        self._st_dot.pack(side="right", padx=(0,18))
        self._st_var = tk.StringVar(value="Ready")
        tk.Label(bar, textvariable=self._st_var, bg=BG2, fg=MUTED,
                 font=FT_SM).pack(side="right")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # sidebar
        side = tk.Frame(body, bg=BG2, width=260)
        side.pack(side="left", fill="y"); side.pack_propagate(False)
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        pad = tk.Frame(side, bg=BG2)
        pad.pack(fill="both", expand=True, padx=14, pady=16)

        def lbl(t): tk.Label(pad, text=t, bg=BG2, fg=MUTED,
            font=("Helvetica",9,"bold")).pack(anchor="w", pady=(10,2))
        def inp(var):
            e = tk.Entry(pad, textvariable=var, bg=BG3, fg=TEXT,
                insertbackground=TEXT, relief="flat", bd=6, font=FT_SM)
            e.pack(fill="x", ipady=5); return e

        lbl("GOOGLE DRIVE LINK")
        self._link = tk.StringVar(value=self._cfg.get("last_link",""))
        inp(self._link)
        lbl("OUTPUT FOLDER")
        self._out = tk.StringVar(value=self._cfg["output_dir"])
        inp(self._out)

        tk.Frame(pad, bg=BG2, height=6).pack()
        self._run_btn = tk.Button(pad, text="▶   Run Face Organizer",
            bg=ACCENT, fg="white", font=("Helvetica",12,"bold"),
            relief="flat", bd=0, pady=10, cursor="hand2",
            activebackground="#6ba3f9", activeforeground="white",
            command=self._run)
        self._run_btn.pack(fill="x")
        tk.Frame(pad, bg=BG2, height=5).pack()
        tk.Button(pad, text="↻   Reload Results", bg=BG3, fg=MUTED,
            font=FT_SM, relief="flat", bd=0, pady=7, cursor="hand2",
            activebackground=BG3, activeforeground=TEXT,
            command=self._reload).pack(fill="x")
        tk.Frame(pad, bg=BG2, height=6).pack()

        style = ttk.Style(); style.theme_use("default")
        style.configure("T.Horizontal.TProgressbar",
            troughcolor=BG3, background=ACCENT, thickness=4)
        self._pbar = ttk.Progressbar(pad, mode="indeterminate",
            style="T.Horizontal.TProgressbar")

        lbl("LOG")
        lw = tk.Frame(pad, bg=BG3, highlightbackground=BORDER, highlightthickness=1)
        lw.pack(fill="both", expand=True)
        self._log_box = tk.Text(lw, bg=BG3, fg=MUTED, font=FT_MON,
            relief="flat", bd=6, wrap="word", state="disabled", cursor="arrow")
        self._log_box.pack(fill="both", expand=True)
        for tag, col in [("ok",GREEN),("err",RED),("warn",YELLOW),
                         ("hi",ACCENT),("dim",MUTED)]:
            self._log_box.tag_configure(tag, foreground=col)

        # right panel
        self._right = tk.Frame(body, bg=BG)
        self._right.pack(side="left", fill="both", expand=True)

        rh = tk.Frame(self._right, bg=BG)
        rh.pack(fill="x", padx=20, pady=(18,6))
        tk.Label(rh, text="People Found", bg=BG, fg=TEXT,
                 font=FT_TIT).pack(side="left")
        self._badge_var = tk.StringVar()
        self._badge = tk.Label(rh, textvariable=self._badge_var,
            bg=ACCENT, fg="white", font=("Helvetica",10,"bold"), padx=10, pady=3)
        self._dlall_btn = tk.Button(rh, text="⬇  Download All",
            bg=BG, fg=GREEN, font=("Helvetica",10,"bold"),
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            highlightbackground=GREEN, highlightthickness=1,
            activebackground=GREEN, activeforeground=BG,
            command=self._download_all)

        self._hint = tk.Label(self._right,
            text="Click photo to open folder  ·  Click ⬇ to save as zip",
            bg=BG, fg=MUTED, font=FT_SM)

        self._empty = tk.Label(self._right,
            text="No results yet.\n\nPaste your Google Drive link\nand click  ▶ Run",
            bg=BG, fg=MUTED, font=("Helvetica",13), justify="center")
        self._empty.pack(expand=True)

        self._cv = tk.Canvas(self._right, bg=BG, highlightthickness=0)
        self._vsb = tk.Scrollbar(self._right, orient="vertical", command=self._cv.yview)
        self._cv.configure(yscrollcommand=self._vsb.set)
        self._cf = tk.Frame(self._cv, bg=BG)
        self._cv.create_window((0,0), window=self._cf, anchor="nw")
        self._cf.bind("<Configure>", lambda e:
            self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.bind_all("<MouseWheel>", lambda e:
            self._cv.yview_scroll(-1*(e.delta//120),"units"))

    def _log(self, msg, tag=None):
        if tag is None:
            if any(x in msg for x in ("✅","Done","DONE")): tag="ok"
            elif any(x in msg for x in ("❌","Error","error","failed")): tag="err"
            elif "⚠" in msg: tag="warn"
            elif any(x in msg for x in ("STEP","===","🚀","Step")): tag="hi"
            else: tag="dim"
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg+"\n", tag)
        self._log_box.configure(state="disabled")
        self._log_box.see("end")

    def _status(self, text, color=MUTED):
        self._st_var.set(text); self._st_dot.configure(fg=color)

    def _run(self):
        link = self._link.get().strip()
        out  = self._out.get().strip() or "output"
        if not link:
            messagebox.showwarning("Missing","Paste your Google Drive link first!")
            return
        self._cfg["last_link"]=link; self._cfg["output_dir"]=out; self._save_cfg()
        self._run_btn.configure(text="⏳  Running...", state="disabled")
        self._pbar.pack(fill="x", pady=(0,6)); self._pbar.start(12)
        self._status("Processing...", YELLOW)
        self._log("🚀 Starting pipeline...", "hi")

        def worker():
            import builtins; orig=builtins.print
            def patch(*a,**kw):
                msg=" ".join(str(x) for x in a)
                if msg.strip(): self.after(0,self._log,msg)
                orig(*a,**kw)
            builtins.print=patch
            try:
                from cors.pipeline import run_pipeline
                ok=run_pipeline(drive_link=link,output_dir=out,
                    batch_size=self._cfg["batch_size"],
                    eps=self._cfg["eps"],min_samples=self._cfg["min_samples"])
            except Exception as e:
                self.after(0,self._log,f"❌ {e}"); ok=False
            finally: builtins.print=orig
            self.after(0,self._done,ok,out)
        threading.Thread(target=worker,daemon=True).start()

    def _done(self, ok, out):
        self._pbar.stop(); self._pbar.pack_forget()
        self._run_btn.configure(text="▶   Run Face Organizer",state="normal")
        if ok: self._status("Done!",GREEN); self._log("✅ Pipeline complete!"); self._reload(out)
        else: self._status("Error!",RED)

    def _reload(self, out=None):
        if out is None: out=self._out.get().strip() or "output"
        for w in self._cf.winfo_children(): w.destroy()
        self._cards=[]
        if not os.path.exists(out): self._show_empty(); return
        folders=sorted([f for f in os.listdir(out)
            if os.path.isdir(os.path.join(out,f)) and not f.startswith(".")])
        if not folders: self._show_empty(); return
        self._show_grid()
        people=[f for f in folders if f!="Unknown"]
        self._badge_var.set(f"{len(people)} people")
        self._badge.pack(side="right", padx=(6,0))
        self._dlall_btn.pack(side="right", padx=(6,0))
        COLS=5
        for i,name in enumerate(folders):
            path=os.path.join(out,name)
            card=PersonCard(self._cf,name,path,on_download=self._download_one)
            card.grid(row=i//COLS,column=i%COLS,padx=10,pady=10,sticky="nw")
            self._cards.append(card)
        self._log(f"📂 {len(folders)} folders loaded")

    def _show_empty(self):
        self._hint.pack_forget(); self._badge.pack_forget()
        self._dlall_btn.pack_forget(); self._cv.pack_forget()
        self._vsb.pack_forget(); self._empty.pack(expand=True)

    def _show_grid(self):
        self._empty.pack_forget()
        self._hint.pack(anchor="w",padx=20,pady=(0,6))
        self._vsb.pack(side="right",fill="y")
        self._cv.pack(side="left",fill="both",expand=True,padx=(20,0),pady=(0,16))

    def _download_one(self, name, folder, reset_cb):
        save=filedialog.asksaveasfilename(title=f"Save {name} as zip",
            initialfile=f"{name}_photos.zip",defaultextension=".zip",
            filetypes=[("Zip files","*.zip")])
        if not save: self.after(0,reset_cb); return
        self._log(f"📦 Preparing {name}...")
        def worker():
            try:
                meta=load_meta(folder)
                if meta and not meta.get("downloaded"):
                    self.after(0,self._log,f"  ⬇ Downloading {name} photos...")
                    try:
                        from core.organizer import download_person_folder
                        download_person_folder(folder)
                    except Exception as e:
                        self.after(0,self._log,f"  ⚠ {e}")
                n=0
                with zipfile.ZipFile(save,"w",zipfile.ZIP_DEFLATED) as zf:
                    for f in os.listdir(folder):
                        if f.lower().endswith((".jpg",".jpeg",".png",".bmp",".webp")):
                            zf.write(os.path.join(folder,f),f); n+=1
                mb=os.path.getsize(save)/(1024*1024)
                self.after(0,self._log,f"✅ Saved {n} photos ({mb:.1f} MB)")
                self.after(0,lambda: subprocess.Popen(["xdg-open",os.path.dirname(save)]))
            except Exception as e:
                self.after(0,self._log,f"❌ {e}")
            finally:
                self.after(0,reset_cb)
        threading.Thread(target=worker,daemon=True).start()

    def _download_all(self):
        out=self._out.get().strip() or "output"
        save=filedialog.asksaveasfilename(title="Save all as zip",
            initialfile="all_people.zip",defaultextension=".zip",
            filetypes=[("Zip files","*.zip")])
        if not save: return
        self._dlall_btn.configure(text="⏳ Zipping...",state="disabled")
        self._log("📦 Zipping all folders...")
        def worker():
            try:
                n=0
                with zipfile.ZipFile(save,"w",zipfile.ZIP_DEFLATED) as zf:
                    for root,_,files in os.walk(out):
                        for fn in files:
                            if fn.lower().endswith((".jpg",".jpeg",".png",".bmp",".webp")):
                                fp=os.path.join(root,fn)
                                zf.write(fp,os.path.relpath(fp,out)); n+=1
                mb=os.path.getsize(save)/(1024*1024)
                self.after(0,self._log,f"✅ Saved {n} photos ({mb:.1f} MB)")
                self.after(0,lambda: subprocess.Popen(["xdg-open",os.path.dirname(save)]))
            except Exception as e:
                self.after(0,self._log,f"❌ {e}")
            finally:
                self.after(0,lambda: self._dlall_btn.configure(
                    text="⬇  Download All",state="normal"))
        threading.Thread(target=worker,daemon=True).start()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    FaceOrganizerApp().mainloop()