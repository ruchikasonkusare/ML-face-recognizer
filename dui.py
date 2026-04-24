# #!/usr/bin/env python3
# # ui_final.py
# # - Reads groups.json to show all people
# # - Shows face thumbnail cropped using bbox (cached in memory, never saved to disk)
# # - Output folder is NEVER touched until user clicks Download
# # - Progress bar for both thumbnail loading and photo downloading
# # Run: python ui_final.py

# import os, sys, json, zipfile, threading, shutil, subprocess
# import tkinter as tk
# from tkinter import ttk, filedialog, messagebox
# from concurrent.futures import ThreadPoolExecutor, as_completed

# os.environ["CUDA_VISIBLE_DEVICES"]  = "-1"
# os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"
# os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# try:
#     from PIL import Image, ImageTk, ImageDraw
#     HAS_PIL = True
# except ImportError:
#     HAS_PIL = False

# # ── Colors ────────────────────────────────────────────────
# BG      = "#0f1117"
# SB      = "#141720"
# CARD    = "#1c2030"
# CARD_H  = "#232840"
# CARD_S  = "#1a2038"
# BORDER  = "#272d40"
# ACCENT  = "#5c8ef5"
# GREEN   = "#3ecf8e"
# YELLOW  = "#f5c542"
# RED     = "#f06c6c"
# TEXT    = "#e0e6f0"
# MUTED   = "#5a6380"
# DIM     = "#2a3050"
# WHITE   = "#f5f8ff"
# FONT    = "Helvetica"

# def F(sz, b=False):
#     return (FONT, sz, "bold") if b else (FONT, sz)

# # in-memory thumbnail cache: name → PIL Image
# _THUMB_CACHE = {}
# # in-memory PhotoImage refs (must keep alive)
# _TK_REFS = {}

# AVATAR_SZ = 56
# TILE_SZ   = 150
# COLS      = 5


# # ══════════════════════════════════════════════════════════
# #  IMAGE UTILS
# # ══════════════════════════════════════════════════════════

# def sq(pil_img, size):
#     w, h = pil_img.size
#     s = min(w, h)
#     img = pil_img.crop(((w-s)//2,(h-s)//2,(w+s)//2,(h+s)//2))
#     return img.resize((size, size), Image.LANCZOS)

# def circle(pil_img, size):
#     img  = sq(pil_img, size).convert("RGBA")
#     mask = Image.new("L", (size, size), 0)
#     ImageDraw.Draw(mask).ellipse([0,0,size-1,size-1], fill=255)
#     img.putalpha(mask)
#     return ImageTk.PhotoImage(img)

# def to_tk(pil_img, size):
#     return ImageTk.PhotoImage(sq(pil_img, size))

# def load_pil(path):
#     try:    return Image.open(path).convert("RGB")
#     except: return None

# def parse_bbox(bbox):
#     """Handle bbox as dict {'x','y','w','h'} OR list [x,y,w,h]."""
#     if not bbox:
#         return None
#     try:
#         if isinstance(bbox, dict):
#             return (int(bbox["x"]), int(bbox["y"]),
#                     int(bbox["w"]), int(bbox["h"]))
#         else:
#             vals = [int(v) for v in bbox]
#             return tuple(vals[:4])
#     except:
#         return None

# def crop_face(img, bbox):
#     """Crop face region from PIL image using bbox."""
#     b = parse_bbox(bbox)
#     if not b:
#         return img
#     try:
#         x, y, w, h = b
#         pad = int(max(w, h) * 0.45)
#         return img.crop((
#             max(0, x-pad), max(0, y-pad),
#             min(img.width,  x+w+pad),
#             min(img.height, y+h+pad)))
#     except:
#         return img

# def best_face(faces):
#     """Return face with largest bbox area."""
#     best = None
#     best_a = 0
#     for f in faces:
#         b = parse_bbox(f.get("bbox"))
#         if b:
#             try:
#                 _, _, w, h = b
#                 if w*h > best_a:
#                     best_a = w*h
#                     best = f
#             except: pass
#     return best or (faces[0] if faces else None)

# def fetch_face_pil(faces):
#     """
#     Get a face PIL image.
#     Strategy:
#       1. Already in _THUMB_CACHE → return instantly
#       2. Photo already exists anywhere on disk → crop and return
#       3. Download ONE photo from Drive → crop → delete → return
#     NEVER writes to output folder.
#     """
#     if not faces or not HAS_PIL:
#         return None

#     face     = best_face(faces)
#     filename = face.get("filename", "")
#     file_id  = face.get("file_id", "")
#     bbox     = face.get("bbox")

#     # ── 1. check temp_batch and any existing downloads ────
#     search_dirs = ["data/temp_batch", "output", "."]
#     for sdir in search_dirs:
#         if not os.path.exists(sdir):
#             continue
#         for root, dirs, files in os.walk(sdir):
#             if filename in files:
#                 path = os.path.join(root, filename)
#                 try:
#                     if os.path.getsize(path) > 30_000:
#                         img = load_pil(path)
#                         if img:
#                             return crop_face(img, bbox)
#                 except: pass
#             # limit depth
#             if root.count(os.sep) - sdir.count(os.sep) > 2:
#                 dirs[:] = []

#     # ── 2. download from Drive into a truly temp file ─────
#     if not file_id:
#         return None
#     try:
#         from cors.downloader import download_one_image
#         tmp = download_one_image(file_id, filename)
#         if tmp and os.path.exists(tmp):
#             img = load_pil(tmp)
#             try: os.remove(tmp)
#             except: pass
#             if img:
#                 return crop_face(img, bbox)
#     except Exception as e:
#         print(f"  [thumb] download fail {filename}: {e}")

#     return None


# # ══════════════════════════════════════════════════════════
# #  PERSON ROW WIDGET
# # ══════════════════════════════════════════════════════════

# class PersonRow(tk.Frame):
#     def __init__(self, parent, name,
#                  n_photos, n_faces,
#                  on_select, on_download, **kw):
#         super().__init__(parent, bg=SB,
#             cursor="hand2", **kw)
#         self.name        = name
#         self.on_select   = on_select
#         self.on_download = on_download
#         self._selected   = False
#         self._tk_img     = None
#         self._build(n_photos, n_faces)
#         self._bind_hover()

#     def _build(self, n_photos, n_faces):
#         # avatar
#         self._av = tk.Label(self,
#             text="👤", font=F(24),
#             bg=DIM, fg=MUTED,
#             width=AVATAR_SZ,
#             height=AVATAR_SZ)
#         self._av.pack(side="left",
#                       padx=(10,8), pady=9)
#         self._av.bind("<Button-1>",
#             lambda e: self.on_select(self.name))

#         # text block
#         tf = tk.Frame(self, bg=SB)
#         tf.pack(side="left", fill="both",
#                 expand=True, pady=10)
#         self._nlbl = tk.Label(tf,
#             text=self.name.replace("_"," "),
#             bg=SB, fg=TEXT,
#             font=F(11, b=True), anchor="w")
#         self._nlbl.pack(anchor="w")
#         sub = (f"{n_photos} photo{'s' if n_photos!=1 else ''}"
#                f"  ·  {n_faces} face{'s' if n_faces!=1 else ''}")
#         self._slbl = tk.Label(tf,
#             text=sub, bg=SB,
#             fg=MUTED, font=F(9), anchor="w")
#         self._slbl.pack(anchor="w")
#         self._tf = tf

#         # download icon
#         self._dl = tk.Label(self, text="⬇",
#             bg=SB, fg=ACCENT,
#             font=F(16), cursor="hand2",
#             padx=10)
#         self._dl.pack(side="right", padx=(0,4))
#         self._dl.bind("<Button-1>",
#             lambda e: self._do_dl())

#         # separator
#         tk.Frame(self, bg=BORDER, height=1
#             ).place(x=0, rely=1.0,
#                     relwidth=1.0, anchor="sw")

#         # click to select
#         for w in [self, tf,
#                   self._nlbl, self._slbl]:
#             w.bind("<Button-1>",
#                 lambda e: self.on_select(self.name))

#     def _do_dl(self):
#         self._dl.configure(text="⏳", fg=YELLOW)
#         self.on_download(self.name,
#                          callback=self._dl_done)

#     def _dl_done(self, ok):
#         if ok:
#             self._dl.configure(text="✅", fg=GREEN)
#         else:
#             self._dl.configure(text="⬇", fg=ACCENT)

#     def set_avatar(self, tk_img):
#         self._tk_img = tk_img
#         self._av.configure(
#             image=tk_img, text="",
#             width=AVATAR_SZ,
#             height=AVATAR_SZ)

#     def select(self, on):
#         self._selected = on
#         bg = CARD_S if on else SB
#         bdr= ACCENT  if on else BORDER
#         self.configure(bg=bg,
#             highlightbackground=bdr,
#             highlightthickness=2 if on else 0)
#         self._av.configure(bg=DIM if not on else DIM)
#         self._tf.configure(bg=bg)
#         self._nlbl.configure(bg=bg)
#         self._slbl.configure(bg=bg)
#         self._dl.configure(bg=bg)

#     def _bind_hover(self):
#         def on(e):
#             if not self._selected:
#                 self._set_bg(CARD_H)
#         def off(e):
#             if not self._selected:
#                 self._set_bg(SB)
#         for w in [self, self._nlbl,
#                   self._slbl, self._tf]:
#             w.bind("<Enter>", on)
#             w.bind("<Leave>", off)

#     def _set_bg(self, bg):
#         self.configure(bg=bg)
#         self._tf.configure(bg=bg)
#         self._nlbl.configure(bg=bg)
#         self._slbl.configure(bg=bg)
#         self._dl.configure(bg=bg)


# # ══════════════════════════════════════════════════════════
# #  PHOTO TILE WIDGET
# # ══════════════════════════════════════════════════════════

# class Tile(tk.Frame):
#     def __init__(self, parent, filepath, **kw):
#         super().__init__(parent, bg=CARD,
#             highlightbackground=BORDER,
#             highlightthickness=1,
#             cursor="hand2", **kw)
#         self.filepath = filepath
#         self._img = None
#         self._build()

#     def _build(self):
#         self._lbl = tk.Label(self,
#             bg=DIM, text="⏳",
#             font=F(20), fg=MUTED,
#             width=TILE_SZ, height=TILE_SZ)
#         self._lbl.pack()
#         self._lbl.bind("<Button-1>",
#             lambda e: subprocess.Popen(
#                 ["xdg-open", self.filepath]))
#         name = os.path.basename(self.filepath)
#         if len(name)>16: name=name[:14]+"…"
#         tk.Label(self, text=name,
#             bg=CARD, fg=MUTED,
#             font=F(8)).pack(pady=(2,5))
#         self._hover()

#     def set_img(self, tk_img):
#         self._img = tk_img
#         self._lbl.configure(
#             image=tk_img, text="",
#             width=TILE_SZ, height=TILE_SZ)

#     def set_err(self):
#         self._lbl.configure(
#             text="✗", fg=RED, font=F(22))

#     def _hover(self):
#         def on(e):
#             self.configure(bg=CARD_H,
#                 highlightbackground=ACCENT)
#             for w in self.winfo_children():
#                 try: w.configure(bg=CARD_H)
#                 except: pass
#         def off(e):
#             self.configure(bg=CARD,
#                 highlightbackground=BORDER)
#             for w in self.winfo_children():
#                 try: w.configure(bg=CARD)
#                 except: pass
#         self.bind("<Enter>", on)
#         self.bind("<Leave>", off)


# # ══════════════════════════════════════════════════════════
# #  SCROLLABLE FRAME HELPER
# # ══════════════════════════════════════════════════════════

# class ScrollFrame(tk.Frame):
#     def __init__(self, parent, bg=BG, **kw):
#         super().__init__(parent, bg=bg, **kw)
#         self.cv  = tk.Canvas(self, bg=bg,
#             highlightthickness=0, bd=0)
#         self.vsb = tk.Scrollbar(self,
#             orient="vertical",
#             command=self.cv.yview)
#         self.cv.configure(
#             yscrollcommand=self.vsb.set)
#         self.vsb.pack(side="right", fill="y")
#         self.cv.pack(side="left",
#             fill="both", expand=True)
#         self.inner = tk.Frame(self.cv, bg=bg)
#         self._win  = self.cv.create_window(
#             (0,0), window=self.inner, anchor="nw")
#         self.inner.bind("<Configure>",
#             lambda e: self.cv.configure(
#                 scrollregion=self.cv.bbox("all")))
#         self.cv.bind("<Configure>",
#             lambda e: self.cv.itemconfig(
#                 self._win, width=e.width))
#         for ev, d in [("<Button-4>",-1),
#                       ("<Button-5>", 1)]:
#             self.cv.bind(ev,
#                 lambda e, d=d:
#                     self.cv.yview_scroll(d,"units"))
#         self.cv.bind("<MouseWheel>",
#             lambda e: self.cv.yview_scroll(
#                 -1*(e.delta//120),"units"))


# # ══════════════════════════════════════════════════════════
# #  MAIN APP
# # ══════════════════════════════════════════════════════════

# class App(tk.Tk):
#     def __init__(self):
#         super().__init__()
#         self.title("Face Organizer")
#         self.geometry("1280x800")
#         self.minsize(1000, 620)
#         self.configure(bg=BG)
#         self._cfg      = self._load_cfg()
#         self._groups   = {}
#         self._rows     = {}
#         self._selected = None
#         self._tile_refs= []
#         self._build()
#         self._load_groups()

#     # ── Config ────────────────────────────────────────────

#     def _load_cfg(self):
#         d = {"output_dir":"output","batch_size":100,
#              "eps":0.6,"min_samples":2,"last_link":""}
#         try:
#             if os.path.exists("data/ui_cfg.json"):
#                 with open("data/ui_cfg.json") as f:
#                     d.update(json.load(f))
#         except: pass
#         return d

#     def _save_cfg(self):
#         os.makedirs("data", exist_ok=True)
#         with open("data/ui_cfg.json","w") as f:
#             json.dump(self._cfg, f, indent=2)

#     # ── Build layout ──────────────────────────────────────

#     def _build(self):
#         # ── topbar ───────────────────────────────────
#         top = tk.Frame(self, bg=SB, height=52)
#         top.pack(fill="x")
#         top.pack_propagate(False)
#         tk.Frame(self, bg=BORDER, height=1
#             ).pack(fill="x")

#         tk.Label(top, text="FACE  ORGANIZER",
#             bg=SB, fg=ACCENT,
#             font=(FONT,13,"bold")
#         ).pack(side="left", padx=20)

#         self._st_dot = tk.Label(top,
#             text="●", bg=SB, fg=GREEN,
#             font=F(13))
#         self._st_dot.pack(side="right", padx=(0,16))
#         self._st_var = tk.StringVar(value="Ready")
#         tk.Label(top, textvariable=self._st_var,
#             bg=SB, fg=MUTED, font=F(10)
#         ).pack(side="right", padx=(0,4))

#         tk.Button(top, text="↻  Reload",
#             bg=BG, fg=MUTED, font=F(10),
#             relief="flat", bd=0,
#             padx=12, pady=5, cursor="hand2",
#             activebackground=DIM,
#             activeforeground=TEXT,
#             command=self._load_groups
#         ).pack(side="right", pady=8, padx=4)

#         self._run_btn = tk.Button(top,
#             text="▶  Run Pipeline",
#             bg=ACCENT, fg=WHITE,
#             font=F(10,b=True),
#             relief="flat", bd=0,
#             padx=16, pady=5, cursor="hand2",
#             activebackground="#7aaaf8",
#             activeforeground=WHITE,
#             command=self._toggle_panel)
#         self._run_btn.pack(
#             side="right", pady=8, padx=4)

#         # ── collapsible run panel ─────────────────────
#         self._rpanel     = tk.Frame(self, bg=SB)
#         self._rpanel_open= False
#         tk.Frame(self._rpanel,
#             bg=BORDER, height=1).pack(fill="x")
#         ri = tk.Frame(self._rpanel, bg=SB)
#         ri.pack(fill="x", padx=20, pady=10)

#         tk.Label(ri, text="Drive Link",
#             bg=SB, fg=MUTED,
#             font=F(9,b=True)).pack(side="left")
#         self._link_var = tk.StringVar(
#             value=self._cfg.get("last_link",""))
#         tk.Entry(ri, textvariable=self._link_var,
#             bg=CARD, fg=TEXT,
#             insertbackground=TEXT,
#             relief="flat", bd=6,
#             font=F(10), width=52
#         ).pack(side="left", padx=(6,18), ipady=4)

#         tk.Label(ri, text="Output",
#             bg=SB, fg=MUTED,
#             font=F(9,b=True)).pack(side="left")
#         self._out_var = tk.StringVar(
#             value=self._cfg["output_dir"])
#         tk.Entry(ri, textvariable=self._out_var,
#             bg=CARD, fg=TEXT,
#             insertbackground=TEXT,
#             relief="flat", bd=6,
#             font=F(10), width=10
#         ).pack(side="left", padx=(6,16), ipady=4)

#         self._go_btn = tk.Button(ri,
#             text="▶  Start",
#             bg=ACCENT, fg=WHITE,
#             font=F(10,b=True),
#             relief="flat", bd=0,
#             padx=14, pady=5, cursor="hand2",
#             activebackground="#7aaaf8",
#             activeforeground=WHITE,
#             command=self._run)
#         self._go_btn.pack(side="left")

#         # ── pipeline progress bar ─────────────────────
#         self._ppf = tk.Frame(self, bg=SB)
#         style = ttk.Style()
#         style.theme_use("default")
#         style.configure("A.Horizontal.TProgressbar",
#             troughcolor=BORDER, background=ACCENT,
#             thickness=5)
#         style.configure("G.Horizontal.TProgressbar",
#             troughcolor=BORDER, background=GREEN,
#             thickness=6)
#         self._ppbar = ttk.Progressbar(self._ppf,
#             mode="indeterminate",
#             style="A.Horizontal.TProgressbar")
#         self._ppbar.pack(fill="x")
#         self._pplbl = tk.Label(self._ppf,
#             text="", bg=SB, fg=MUTED, font=F(9))
#         self._pplbl.pack(anchor="w", padx=8)

#         # ── body ─────────────────────────────────────
#         body = tk.Frame(self, bg=BG)
#         body.pack(fill="both", expand=True)

#         # ── LEFT: person list ─────────────────────────
#         self._sb_frame = tk.Frame(
#             body, bg=SB, width=278)
#         self._sb_frame.pack(side="left", fill="y")
#         self._sb_frame.pack_propagate(False)
#         tk.Frame(body, bg=BORDER, width=1
#             ).pack(side="left", fill="y")

#         # sidebar header
#         sh = tk.Frame(self._sb_frame, bg=SB)
#         sh.pack(fill="x", padx=14, pady=(14,4))
#         self._ph_lbl = tk.Label(sh,
#             text="People",
#             bg=SB, fg=TEXT,
#             font=F(13,b=True))
#         self._ph_lbl.pack(side="left")
#         self._badge = tk.Label(sh, text="",
#             bg=ACCENT, fg=WHITE,
#             font=F(9,b=True), padx=9, pady=2)

#         # thumbnail loading progress
#         self._av_frame = tk.Frame(self._sb_frame, bg=SB)
#         self._av_bar = ttk.Progressbar(self._av_frame,
#             mode="determinate",
#             style="A.Horizontal.TProgressbar")
#         self._av_bar.pack(fill="x", padx=12)
#         self._av_lbl = tk.Label(self._av_frame,
#             text="Loading thumbnails...",
#             bg=SB, fg=MUTED, font=F(8))
#         self._av_lbl.pack(anchor="w", padx=12, pady=(0,4))

#         # scrollable list
#         self._person_sf = ScrollFrame(
#             self._sb_frame, bg=SB)
#         self._person_sf.pack(
#             fill="both", expand=True)
#         self._person_list = self._person_sf.inner

#         # ── RIGHT: photo panel ────────────────────────
#         right = tk.Frame(body, bg=BG)
#         right.pack(side="left",
#             fill="both", expand=True)
#         self._right = right

#         # right header
#         rh = tk.Frame(right, bg=BG)
#         rh.pack(fill="x", padx=22, pady=(16,4))
#         self._rh = rh

#         self._r_name = tk.Label(rh, text="",
#             bg=BG, fg=WHITE, font=F(17,b=True))
#         self._r_name.pack(side="left")

#         self._r_sub = tk.Label(rh, text="",
#             bg=BG, fg=MUTED, font=F(10))
#         self._r_sub.pack(side="left", padx=(12,0))

#         self._dl_btn = tk.Button(rh,
#             text="⬇  Download Photos",
#             bg=BG, fg=ACCENT,
#             font=F(10,b=True),
#             relief="flat", bd=0,
#             padx=14, pady=5, cursor="hand2",
#             highlightbackground=ACCENT,
#             highlightthickness=1,
#             activebackground=ACCENT,
#             activeforeground=WHITE,
#             command=self._dl_selected)

#         # download progress bar
#         self._dlf = tk.Frame(right, bg=BG)
#         self._dlbar = ttk.Progressbar(self._dlf,
#             mode="determinate",
#             style="G.Horizontal.TProgressbar",
#             maximum=100)
#         self._dlbar.pack(fill="x",
#             padx=22, pady=(4,0))
#         self._dllbl = tk.Label(self._dlf,
#             text="", bg=BG, fg=GREEN, font=F(9))
#         self._dllbl.pack(anchor="w", padx=22)

#         # welcome
#         self._welcome = tk.Label(right,
#             text="← Select a person",
#             bg=BG, fg=MUTED, font=F(14))
#         self._welcome.pack(expand=True)

#         # photo grid scroll
#         self._grid_sf = ScrollFrame(right, bg=BG)
#         self._grid_inner = self._grid_sf.inner

#     # ── Status ────────────────────────────────────────────

#     def _st(self, text, color=MUTED):
#         self._st_var.set(text)
#         self._st_dot.configure(fg=color)

#     # ── Run panel toggle ──────────────────────────────────

#     def _toggle_panel(self):
#         if self._rpanel_open:
#             self._rpanel.pack_forget()
#             self._rpanel_open = False
#             self._run_btn.configure(
#                 text="▶  Run Pipeline")
#         else:
#             self._rpanel.pack(fill="x")
#             self._rpanel_open = True
#             self._run_btn.configure(text="✕  Close")

#     # ── Run pipeline ──────────────────────────────────────

#     def _run(self):
#         link = self._link_var.get().strip()
#         out  = self._out_var.get().strip() or "output"
#         if not link:
#             messagebox.showwarning(
#                 "Missing",
#                 "Paste your Google Drive link!")
#             return
#         self._cfg["last_link"]  = link
#         self._cfg["output_dir"] = out
#         self._save_cfg()

#         self._go_btn.configure(
#             text="⏳ Running...",
#             state="disabled")
#         self._ppf.pack(fill="x")
#         self._ppbar.start(12)
#         self._st("Processing...", YELLOW)

#         def worker():
#             import builtins; orig = builtins.print
#             def patch(*a, **kw):
#                 msg = " ".join(str(x) for x in a)
#                 if msg.strip():
#                     self.after(0,
#                         self._pplbl.configure,
#                         {"text": msg[:88]})
#                 orig(*a, **kw)
#             builtins.print = patch
#             try:
#                 from cors.pipeline import run_pipeline
#                 ok = run_pipeline(
#                     drive_link  = link,
#                     output_dir  = out,
#                     batch_size  = self._cfg["batch_size"],
#                     eps         = self._cfg["eps"],
#                     min_samples = self._cfg["min_samples"])
#             except Exception as e:
#                 self.after(0,
#                     self._pplbl.configure,
#                     {"text": f"❌ {e}"})
#                 ok = False
#             finally:
#                 builtins.print = orig
#             self.after(0, self._run_done, ok)

#         threading.Thread(
#             target=worker, daemon=True).start()

#     def _run_done(self, ok):
#         self._ppbar.stop()
#         self._ppf.pack_forget()
#         self._go_btn.configure(
#             text="▶  Start", state="normal")
#         if ok:
#             self._st("Done!", GREEN)
#             self._load_groups()
#         else:
#             self._st("Error!", RED)

#     # ── Load groups.json ──────────────────────────────────

#     def _load_groups(self):
#         # clear everything
#         for w in self._person_list.winfo_children():
#             w.destroy()
#         self._rows     = {}
#         self._selected = None
#         self._groups   = {}
#         _THUMB_CACHE.clear()
#         _TK_REFS.clear()
#         self._clear_photos()
#         self._welcome.pack(expand=True)

#         gf = "data/groups.json"
#         if not os.path.exists(gf):
#             self._ph_lbl.configure(
#                 text="No groups yet")
#             self._badge.pack_forget()
#             self._st("Run pipeline first", YELLOW)
#             return

#         try:
#             with open(gf) as f:
#                 self._groups = json.load(f)
#         except Exception as e:
#             self._st(f"Error: {e}", RED)
#             return

#         if not self._groups:
#             self._ph_lbl.configure(text="Empty")
#             return

#         names  = sorted(self._groups.keys(),
#             key=lambda x: (x=="Unknown", x))
#         people = [n for n in names
#                   if n != "Unknown"]

#         self._ph_lbl.configure(text="People  ")
#         self._badge.configure(text=str(len(people)))
#         self._badge.pack(side="left")

#         # build all rows immediately with 👤
#         for name in names:
#             faces    = self._groups[name]
#             n_photos = len(set(
#                 f["filename"] for f in faces))
#             n_faces  = len(faces)
#             row = PersonRow(
#                 self._person_list,
#                 name, n_photos, n_faces,
#                 on_select   = self._select,
#                 on_download = self._dl_person)
#             row.pack(fill="x")
#             self._rows[name] = row

#         self._st(f"{len(people)} people", GREEN)

#         # load thumbnails in background
#         if HAS_PIL:
#             self._load_avatars(names)
#         else:
#             self._ph_lbl.configure(
#                 text="People  (install Pillow for thumbnails)")

#     # ── Avatar loading ────────────────────────────────────

#     def _load_avatars(self, names):
#         total = len(names)
#         done  = [0]

#         self._av_bar.configure(maximum=total, value=0)
#         self._av_frame.pack(fill="x", pady=(0,4))

#         def load_one(name):
#             faces = self._groups.get(name, [])
#             img   = fetch_face_pil(faces)
#             return name, img

#         def run():
#             with ThreadPoolExecutor(max_workers=3) as ex:
#                 futs = {
#                     ex.submit(load_one, n): n
#                     for n in names}
#                 for fut in as_completed(futs):
#                     try:
#                         name, pil = fut.result()
#                     except Exception:
#                         name = futs[fut]
#                         pil  = None
#                     done[0] += 1
#                     self.after(0,
#                         self._av_bar.configure,
#                         {"value": done[0]})
#                     self.after(0,
#                         self._av_lbl.configure,
#                         {"text":
#                          f"Loading thumbnails  "
#                          f"{done[0]} / {total}"})
#                     if pil and name in self._rows:
#                         tk_img = circle(pil, AVATAR_SZ)
#                         _TK_REFS[name] = tk_img
#                         self.after(0,
#                             self._rows[name].set_avatar,
#                             tk_img)
#             self.after(0,
#                 self._av_frame.pack_forget)
#             self.after(0,
#                 self._st,
#                 f"{len([n for n in names if n!='Unknown'])} people  •  thumbnails ready",
#                 GREEN)

#         threading.Thread(
#             target=run, daemon=True).start()

#     # ── Select person ─────────────────────────────────────

#     def _select(self, name):
#         if self._selected and \
#                 self._selected in self._rows:
#             self._rows[self._selected].select(False)
#         self._selected = name
#         self._rows[name].select(True)

#         faces    = self._groups.get(name, [])
#         n_photos = len(set(
#             f["filename"] for f in faces))
#         n_faces  = len(faces)

#         self._r_name.configure(
#             text=name.replace("_", " "))
#         self._r_sub.configure(
#             text=f"{n_photos} photos  ·  {n_faces} faces")
#         self._dl_btn.pack(side="right")

#         # stream photos into memory — never touch output/
#         self._stream_photos(name, faces)

#     # ── Stream photos into grid (memory only) ─────────────

#     def _stream_photos(self, name, faces):
#         """
#         Downloads each photo into memory ONE BY ONE,
#         shows it in the grid immediately.
#         NOTHING is saved to output/ folder.
#         """
#         self._clear_photos()
#         self._welcome.pack_forget()
#         self._grid_sf.pack(fill="both", expand=True)

#         unique = {}
#         for face in faces:
#             fn  = face.get("filename", "")
#             fid = face.get("file_id", "")
#             if fn and fid and fn not in unique:
#                 unique[fn] = fid

#         total = len(unique)
#         items = list(unique.items())

#         # show progress bar
#         self._dlbar.configure(maximum=total, value=0)
#         self._dlf.pack(after=self._rh)
#         self._dllbl.configure(
#             text=f"Loading  0 / {total} photos...")
#         self._st(f"Loading {name}...", YELLOW)

#         # pre-create all tiles as placeholders
#         tiles = {}
#         for i, (fn, _) in enumerate(items):
#             ph = tk.Frame(self._grid_inner,
#                 bg=CARD,
#                 highlightbackground=BORDER,
#                 highlightthickness=1,
#                 width=TILE_SZ,
#                 height=TILE_SZ + 28)
#             ph.grid(row=i//COLS, column=i%COLS,
#                     padx=8, pady=8)
#             ph.pack_propagate(False)
#             lbl = tk.Label(ph, text="⏳",
#                 font=F(22), bg=CARD, fg=MUTED)
#             lbl.pack(expand=True)
#             name_lbl = tk.Label(ph,
#                 text=fn[:14]+"…" if len(fn)>16 else fn,
#                 bg=CARD, fg=MUTED, font=F(8))
#             name_lbl.pack(pady=(0,4))
#             tiles[fn] = (ph, lbl, name_lbl)

#         def update_tile(fn, pil_img):
#             """Called from main thread to update one tile."""
#             if fn not in tiles:
#                 return
#             ph, lbl, name_lbl = tiles[fn]
#             if pil_img and HAS_PIL:
#                 tk_img = to_tk(pil_img, TILE_SZ)
#                 self._tile_refs.append(tk_img)
#                 lbl.configure(
#                     image=tk_img, text="",
#                     width=TILE_SZ, height=TILE_SZ)
#                 lbl.bind("<Button-1>",
#                     lambda e, p=pil_img:
#                         self._open_pil(p, fn))
#             else:
#                 lbl.configure(text="✗", fg=RED)

#         def worker():
#             from cors.downloader import download_one_image
#             done = 0
#             for fn, fid in items:
#                 pil_img = None
#                 try:
#                     tmp = download_one_image(fid, fn)
#                     if tmp and os.path.exists(tmp):
#                         pil_img = load_pil(tmp)
#                         try: os.remove(tmp)
#                         except: pass
#                 except Exception as e:
#                     print(f"  stream fail {fn}: {e}")

#                 done += 1
#                 pct  = int(done / total * 100)
#                 self.after(0, update_tile, fn, pil_img)
#                 self.after(0,
#                     self._dlbar.configure,
#                     {"value": done})
#                 self.after(0,
#                     self._dllbl.configure,
#                     {"text":
#                      f"Loading  {done} / {total}"
#                      f"  ({pct}%)"})

#             self.after(0, self._stream_done,
#                        name, done, total, items)

#         threading.Thread(
#             target=worker, daemon=True).start()

#     def _stream_done(self, name, done, total, items):
#         self._dllbl.configure(
#             text=f"✅  {done} / {total} photos loaded  "
#                  f"(not saved — click ⬇ to save)")
#         self._st(f"{name}  —  {done} photos", GREEN)

#         # store items for later download
#         self._loaded_items = {
#             "name":  name,
#             "items": items,
#         }

#     def _open_pil(self, pil_img, filename):
#         """Show PIL image in a popup window."""
#         win = tk.Toplevel(self)
#         win.title(filename)
#         win.configure(bg=BG)
#         try:
#             w = min(pil_img.width,  1200)
#             h = min(pil_img.height, 900)
#             img    = pil_img.copy()
#             img.thumbnail((w, h), Image.LANCZOS)
#             tk_img = ImageTk.PhotoImage(img)
#             lbl    = tk.Label(win, image=tk_img, bg=BG)
#             lbl.image = tk_img  # keep ref
#             lbl.pack(padx=10, pady=10)
#         except Exception:
#             tk.Label(win, text=filename,
#                 bg=BG, fg=TEXT).pack(padx=20, pady=20)

#     def _clear_photos(self):
#         for w in self._grid_inner.winfo_children():
#             w.destroy()
#         self._grid_sf.pack_forget()
#         self._dlf.pack_forget()
#         self._tile_refs  = []
#         self._loaded_items = {}

#     # ── Download button — saves to output/ + zips ─────────

#     def _dl_selected(self):
#         if not self._selected:
#             return
#         items = getattr(self, "_loaded_items", {})
#         if not items or items.get("name") != self._selected:
#             messagebox.showinfo(
#                 "Select first",
#                 "Click on a person first to load their photos,\n"
#                 "then click Download to save them.")
#             return
#         self._save_to_output(
#             items["name"], items["items"])

#     def _dl_person(self, name, callback=None):
#         """Called from sidebar ⬇ icon."""
#         faces  = self._groups.get(name, [])
#         unique = {}
#         for face in faces:
#             fn  = face.get("filename", "")
#             fid = face.get("file_id", "")
#             if fn and fid and fn not in unique:
#                 unique[fn] = fid
#         items = list(unique.items())
#         self._save_to_output(name, items,
#                              callback=callback)

#     def _save_to_output(self, name, items,
#                         callback=None):
#         """Download photos and save to output/name/ folder."""
#         out    = self._out_var.get().strip() or "output"
#         folder = os.path.join(out, name)
#         os.makedirs(folder, exist_ok=True)
#         total  = len(items)

#         self._dlbar.configure(maximum=total, value=0)
#         self._dlf.pack(after=self._rh)
#         self._dllbl.configure(
#             text=f"Saving  0 / {total}...")
#         self._dl_btn.configure(
#             text="⏳  Saving...", state="disabled")
#         self._st(f"Saving {name}...", YELLOW)

#         def worker():
#             from cors.downloader import download_one_image
#             done = 0
#             for fn, fid in items:
#                 dest = os.path.join(folder, fn)
#                 if (os.path.exists(dest) and
#                         os.path.getsize(dest) > 50_000):
#                     done += 1
#                 else:
#                     try:
#                         tmp = download_one_image(fid, fn)
#                         if tmp and os.path.exists(tmp):
#                             shutil.move(tmp, dest)
#                             done += 1
#                     except Exception as e:
#                         print(f"  save fail {fn}: {e}")

#                 pct = int(done / total * 100)
#                 self.after(0,
#                     self._dlbar.configure,
#                     {"value": done})
#                 self.after(0,
#                     self._dllbl.configure,
#                     {"text":
#                      f"Saved  {done} / {total}"
#                      f"  ({pct}%)"})

#             self.after(0, self._save_done,
#                 name, folder, done, total, callback)

#         threading.Thread(
#             target=worker, daemon=True).start()

#     def _save_done(self, name, folder,
#                    done, total, callback):
#         self._dl_btn.configure(
#             text="⬇  Download Photos",
#             state="normal")
#         self._dllbl.configure(
#             text=f"✅  {done} / {total} saved to {folder}")
#         self._st(f"Saved {done} photos", GREEN)

#         if callback:
#             callback(done > 0)

#         # ask to zip
#         if done > 0 and messagebox.askyesno(
#                 "Save as Zip?",
#                 f"{done} photos saved to:\n{folder}\n\n"
#                 f"Also save as zip file?"):
#             self._save_zip(name, folder)

#     def _save_zip(self, name, folder):
#         save = filedialog.asksaveasfilename(
#             title=f"Save {name} as zip",
#             initialfile=f"{name}_photos.zip",
#             defaultextension=".zip",
#             filetypes=[("Zip", "*.zip")])
#         if not save: return
#         n = 0
#         with zipfile.ZipFile(save, "w",
#                 zipfile.ZIP_DEFLATED) as zf:
#             for fn in os.listdir(folder):
#                 if fn.lower().endswith((
#                         ".jpg",".jpeg",".png",
#                         ".bmp",".webp")):
#                     zf.write(
#                         os.path.join(folder, fn), fn)
#                     n += 1
#         mb = os.path.getsize(save) / (1024*1024)
#         self._st(
#             f"Saved {n} photos ({mb:.1f} MB)", GREEN)
#         subprocess.Popen([
#             "xdg-open", os.path.dirname(save)])


# # ── Entry ─────────────────────────────────────────────────
# if __name__ == "__main__":
#     os.chdir(os.path.dirname(
#         os.path.abspath(__file__)))
#     App().mainloop()

#!/usr/bin/env python3
# ui_final.py

import os, sys, json, zipfile, threading, shutil, subprocess, tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ["CUDA_VISIBLE_DEVICES"]  = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

try:
    from PIL import Image, ImageTk, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Colors ────────────────────────────────────────────────
BG      = "#0f1117"
SB      = "#141720"
CARD    = "#1c2030"
CARD_H  = "#232840"
CARD_S  = "#1a2038"
BORDER  = "#272d40"
ACCENT  = "#5c8ef5"
GREEN   = "#3ecf8e"
YELLOW  = "#f5c542"
RED     = "#f06c6c"
TEXT    = "#e0e6f0"
MUTED   = "#5a6380"
DIM     = "#2a3050"
WHITE   = "#f5f8ff"
FONT    = "Helvetica"

def F(sz, b=False):
    return (FONT, sz, "bold") if b else (FONT, sz)

_THUMB_CACHE = {}
_TK_REFS     = {}

AVATAR_SZ = 56
TILE_SZ   = 150
COLS      = 5


# ══════════════════════════════════════════════════════════
#  IMAGE UTILS  (unchanged)
# ══════════════════════════════════════════════════════════

def sq(pil_img, size):
    w, h = pil_img.size
    s = min(w, h)
    img = pil_img.crop(((w-s)//2,(h-s)//2,(w+s)//2,(h+s)//2))
    return img.resize((size, size), Image.LANCZOS)

def circle(pil_img, size):
    img  = sq(pil_img, size).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0,0,size-1,size-1], fill=255)
    img.putalpha(mask)
    return ImageTk.PhotoImage(img)

def to_tk(pil_img, size):
    return ImageTk.PhotoImage(sq(pil_img, size))

def load_pil(path):
    try:    return Image.open(path).convert("RGB")
    except: return None

def parse_bbox(bbox):
    if not bbox: return None
    try:
        if isinstance(bbox, dict):
            return (int(bbox["x"]), int(bbox["y"]),
                    int(bbox["w"]), int(bbox["h"]))
        vals = [int(v) for v in bbox]
        return tuple(vals[:4])
    except: return None

def crop_face(img, bbox):
    b = parse_bbox(bbox)
    if not b: return img
    try:
        x, y, w, h = b
        pad = int(max(w, h) * 0.45)
        return img.crop((
            max(0, x-pad), max(0, y-pad),
            min(img.width,  x+w+pad),
            min(img.height, y+h+pad)))
    except: return img

def best_face(faces):
    best = None; best_a = 0
    for f in faces:
        b = parse_bbox(f.get("bbox"))
        if b:
            try:
                _, _, w, h = b
                if w*h > best_a: best_a=w*h; best=f
            except: pass
    return best or (faces[0] if faces else None)

def fetch_face_pil(faces):
    if not faces or not HAS_PIL: return None
    face     = best_face(faces)
    filename = face.get("filename", "")
    file_id  = face.get("file_id", "")
    bbox     = face.get("bbox")

    # check disk first — no download needed
    for sdir in ["data/temp_batch", "output", "."]:
        if not os.path.exists(sdir): continue
        for root, dirs, files in os.walk(sdir):
            if filename in files:
                path = os.path.join(root, filename)
                try:
                    if os.path.getsize(path) > 30_000:
                        img = load_pil(path)
                        if img: return crop_face(img, bbox)
                except: pass
            if root.count(os.sep) - sdir.count(os.sep) > 2:
                dirs[:] = []

    if not file_id: return None
    try:
        from cors.downloader import download_one_image  # ✅ FIXED: was cors
        tmp = download_one_image(file_id, filename)
        if tmp and os.path.exists(tmp):
            img = load_pil(tmp)
            try: os.remove(tmp)
            except: pass
            if img: return crop_face(img, bbox)
    except Exception as e:
        print(f"  [thumb] {filename}: {e}")
    return None


# ══════════════════════════════════════════════════════════
#  PERSON ROW WIDGET
# ══════════════════════════════════════════════════════════

class PersonRow(tk.Frame):
    def __init__(self, parent, name,
                 n_photos, n_faces,
                 on_select, on_download, **kw):
        super().__init__(parent, bg=SB,
            cursor="hand2", **kw)
        self.name        = name
        self.on_select   = on_select
        self.on_download = on_download
        self._selected   = False
        self._tk_img     = None
        self._build(n_photos, n_faces)
        self._bind_hover()

    def _build(self, n_photos, n_faces):
        self._av = tk.Label(self, text="👤", font=F(24),
            bg=DIM, fg=MUTED, width=AVATAR_SZ, height=AVATAR_SZ)
        self._av.pack(side="left", padx=(10,8), pady=9)

        tf = tk.Frame(self, bg=SB)
        tf.pack(side="left", fill="both", expand=True, pady=10)
        self._nlbl = tk.Label(tf,
            text=self.name.replace("_"," "),
            bg=SB, fg=TEXT, font=F(11,b=True), anchor="w")
        self._nlbl.pack(anchor="w")
        sub = (f"{n_photos} photo{'s' if n_photos!=1 else ''}"
               f"  ·  {n_faces} face{'s' if n_faces!=1 else ''}")
        self._slbl = tk.Label(tf, text=sub, bg=SB,
            fg=MUTED, font=F(9), anchor="w")
        self._slbl.pack(anchor="w")
        self._tf = tf

        self._dl = tk.Label(self, text="⬇", bg=SB, fg=ACCENT,
            font=F(16), cursor="hand2", padx=10)
        self._dl.pack(side="right", padx=(0,4))
        self._dl.bind("<Button-1>", lambda e: self._do_dl())

        tk.Frame(self, bg=BORDER, height=1
            ).place(x=0, rely=1.0, relwidth=1.0, anchor="sw")

        # ✅ FIXED: capture name=self.name to avoid closure bug
        # Without this ALL rows call on_select with the LAST name
        _name = self.name
        for w in [self, self._av, tf, self._nlbl, self._slbl]:
            w.bind("<Button-1>",
                lambda e, n=_name: self.on_select(n))

    def _do_dl(self):
        self._dl.configure(text="⏳", fg=YELLOW)
        self.on_download(self.name, callback=self._dl_done)

    def _dl_done(self, ok):
        self._dl.configure(
            text="✅" if ok else "⬇",
            fg=GREEN if ok else ACCENT)

    def set_avatar(self, tk_img):
        self._tk_img = tk_img
        self._av.configure(image=tk_img, text="",
                           width=AVATAR_SZ, height=AVATAR_SZ)

    def select(self, on):
        self._selected = on
        bg  = CARD_S if on else SB
        bdr = ACCENT  if on else BORDER
        self.configure(bg=bg,
            highlightbackground=bdr,
            highlightthickness=2 if on else 0)
        self._av.configure(bg=DIM)
        self._tf.configure(bg=bg)
        self._nlbl.configure(bg=bg)
        self._slbl.configure(bg=bg)
        self._dl.configure(bg=bg)

    def _bind_hover(self):
        def on(e):
            if not self._selected: self._set_bg(CARD_H)
        def off(e):
            if not self._selected: self._set_bg(SB)
        for w in [self, self._nlbl, self._slbl, self._tf]:
            w.bind("<Enter>", on)
            w.bind("<Leave>", off)

    def _set_bg(self, bg):
        self.configure(bg=bg)
        self._tf.configure(bg=bg)
        self._nlbl.configure(bg=bg)
        self._slbl.configure(bg=bg)
        self._dl.configure(bg=bg)


# ══════════════════════════════════════════════════════════
#  PHOTO TILE WIDGET  (unchanged)
# ══════════════════════════════════════════════════════════

class Tile(tk.Frame):
    def __init__(self, parent, filepath, **kw):
        super().__init__(parent, bg=CARD,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", **kw)
        self.filepath = filepath
        self._img = None
        self._build()

    def _build(self):
        self._lbl = tk.Label(self, bg=DIM, text="⏳",
            font=F(20), fg=MUTED, width=TILE_SZ, height=TILE_SZ)
        self._lbl.pack()
        self._lbl.bind("<Button-1>",
            lambda e: subprocess.Popen(["xdg-open", self.filepath]))
        name = os.path.basename(self.filepath)
        if len(name)>16: name=name[:14]+"…"
        tk.Label(self, text=name, bg=CARD, fg=MUTED,
                 font=F(8)).pack(pady=(2,5))
        self._hover()

    def set_img(self, tk_img):
        self._img = tk_img
        self._lbl.configure(image=tk_img, text="",
                             width=TILE_SZ, height=TILE_SZ)

    def set_err(self):
        self._lbl.configure(text="✗", fg=RED, font=F(22))

    def _hover(self):
        def on(e):
            self.configure(bg=CARD_H, highlightbackground=ACCENT)
            for w in self.winfo_children():
                try: w.configure(bg=CARD_H)
                except: pass
        def off(e):
            self.configure(bg=CARD, highlightbackground=BORDER)
            for w in self.winfo_children():
                try: w.configure(bg=CARD)
                except: pass
        self.bind("<Enter>", on); self.bind("<Leave>", off)


# ══════════════════════════════════════════════════════════
#  SCROLLABLE FRAME HELPER  (unchanged)
# ══════════════════════════════════════════════════════════

class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg=BG, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.cv  = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.cv, bg=bg)
        self._win  = self.cv.create_window((0,0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
            lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>",
            lambda e: self.cv.itemconfig(self._win, width=e.width))
        for ev, d in [("<Button-4>",-1), ("<Button-5>",1)]:
            self.cv.bind(ev, lambda e, d=d: self.cv.yview_scroll(d,"units"))
        self.cv.bind("<MouseWheel>",
            lambda e: self.cv.yview_scroll(-1*(e.delta//120),"units"))


# ══════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Face Organizer")
        self.geometry("1280x800")
        self.minsize(1000, 620)
        self.configure(bg=BG)
        self._cfg      = self._load_cfg()
        self._groups   = {}
        self._rows     = {}
        self._selected = None
        self._tile_refs= []
        self._build()
        self._load_groups()

    def _load_cfg(self):
        d = {"output_dir":"output","batch_size":100,
             "eps":0.6,"min_samples":2,"last_link":""}
        try:
            if os.path.exists("data/ui_cfg.json"):
                with open("data/ui_cfg.json") as f:
                    d.update(json.load(f))
        except: pass
        return d

    def _save_cfg(self):
        os.makedirs("data", exist_ok=True)
        with open("data/ui_cfg.json","w") as f:
            json.dump(self._cfg, f, indent=2)

    def _build(self):
        top = tk.Frame(self, bg=SB, height=52)
        top.pack(fill="x"); top.pack_propagate(False)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        tk.Label(top, text="FACE  ORGANIZER", bg=SB, fg=ACCENT,
            font=(FONT,13,"bold")).pack(side="left", padx=20)

        self._st_dot = tk.Label(top, text="●", bg=SB, fg=GREEN, font=F(13))
        self._st_dot.pack(side="right", padx=(0,16))
        self._st_var = tk.StringVar(value="Ready")
        tk.Label(top, textvariable=self._st_var, bg=SB, fg=MUTED,
            font=F(10)).pack(side="right", padx=(0,4))

        tk.Button(top, text="↻  Reload", bg=BG, fg=MUTED, font=F(10),
            relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
            activebackground=DIM, activeforeground=TEXT,
            command=self._load_groups).pack(side="right", pady=8, padx=4)

        self._run_btn = tk.Button(top, text="▶  Run Pipeline",
            bg=ACCENT, fg=WHITE, font=F(10,b=True), relief="flat", bd=0,
            padx=16, pady=5, cursor="hand2",
            activebackground="#7aaaf8", activeforeground=WHITE,
            command=self._toggle_panel)
        self._run_btn.pack(side="right", pady=8, padx=4)

        self._rpanel      = tk.Frame(self, bg=SB)
        self._rpanel_open = False
        tk.Frame(self._rpanel, bg=BORDER, height=1).pack(fill="x")
        ri = tk.Frame(self._rpanel, bg=SB)
        ri.pack(fill="x", padx=20, pady=10)

        tk.Label(ri, text="Drive Link", bg=SB, fg=MUTED,
            font=F(9,b=True)).pack(side="left")
        self._link_var = tk.StringVar(value=self._cfg.get("last_link",""))
        tk.Entry(ri, textvariable=self._link_var, bg=CARD, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=6,
            font=F(10), width=52).pack(side="left", padx=(6,18), ipady=4)

        tk.Label(ri, text="Output", bg=SB, fg=MUTED,
            font=F(9,b=True)).pack(side="left")
        self._out_var = tk.StringVar(value=self._cfg["output_dir"])
        tk.Entry(ri, textvariable=self._out_var, bg=CARD, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=6,
            font=F(10), width=10).pack(side="left", padx=(6,16), ipady=4)

        self._go_btn = tk.Button(ri, text="▶  Start", bg=ACCENT, fg=WHITE,
            font=F(10,b=True), relief="flat", bd=0, padx=14, pady=5,
            cursor="hand2", activebackground="#7aaaf8", activeforeground=WHITE,
            command=self._run)
        self._go_btn.pack(side="left")

        self._ppf = tk.Frame(self, bg=SB)
        style = ttk.Style(); style.theme_use("default")
        style.configure("A.Horizontal.TProgressbar",
            troughcolor=BORDER, background=ACCENT, thickness=5)
        style.configure("G.Horizontal.TProgressbar",
            troughcolor=BORDER, background=GREEN, thickness=6)
        self._ppbar = ttk.Progressbar(self._ppf, mode="indeterminate",
            style="A.Horizontal.TProgressbar")
        self._ppbar.pack(fill="x")
        self._pplbl = tk.Label(self._ppf, text="", bg=SB, fg=MUTED, font=F(9))
        self._pplbl.pack(anchor="w", padx=8)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self._sb_frame = tk.Frame(body, bg=SB, width=278)
        self._sb_frame.pack(side="left", fill="y")
        self._sb_frame.pack_propagate(False)
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        sh = tk.Frame(self._sb_frame, bg=SB)
        sh.pack(fill="x", padx=14, pady=(14,4))
        self._ph_lbl = tk.Label(sh, text="People", bg=SB, fg=TEXT,
            font=F(13,b=True))
        self._ph_lbl.pack(side="left")
        self._badge = tk.Label(sh, text="", bg=ACCENT, fg=WHITE,
            font=F(9,b=True), padx=9, pady=2)

        self._av_frame = tk.Frame(self._sb_frame, bg=SB)
        self._av_bar = ttk.Progressbar(self._av_frame, mode="determinate",
            style="A.Horizontal.TProgressbar")
        self._av_bar.pack(fill="x", padx=12)
        self._av_lbl = tk.Label(self._av_frame,
            text="Loading thumbnails...", bg=SB, fg=MUTED, font=F(8))
        self._av_lbl.pack(anchor="w", padx=12, pady=(0,4))

        self._person_sf   = ScrollFrame(self._sb_frame, bg=SB)
        self._person_sf.pack(fill="both", expand=True)
        self._person_list = self._person_sf.inner

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self._right = right

        rh = tk.Frame(right, bg=BG)
        rh.pack(fill="x", padx=22, pady=(16,4))
        self._rh = rh

        self._r_name = tk.Label(rh, text="", bg=BG, fg=WHITE, font=F(17,b=True))
        self._r_name.pack(side="left")
        self._r_sub  = tk.Label(rh, text="", bg=BG, fg=MUTED, font=F(10))
        self._r_sub.pack(side="left", padx=(12,0))
        self._dl_btn = tk.Button(rh, text="⬇  Download as Zip",
            bg=BG, fg=ACCENT, font=F(10,b=True), relief="flat", bd=0,
            padx=14, pady=5, cursor="hand2",
            highlightbackground=ACCENT, highlightthickness=1,
            activebackground=ACCENT, activeforeground=WHITE,
            command=self._dl_selected)

        self._dlf   = tk.Frame(right, bg=BG)
        self._dlbar = ttk.Progressbar(self._dlf, mode="determinate",
            style="G.Horizontal.TProgressbar", maximum=100)
        self._dlbar.pack(fill="x", padx=22, pady=(4,0))
        self._dllbl = tk.Label(self._dlf, text="", bg=BG, fg=GREEN, font=F(9))
        self._dllbl.pack(anchor="w", padx=22)

        self._welcome = tk.Label(right, text="← Select a person",
            bg=BG, fg=MUTED, font=F(14))
        self._welcome.pack(expand=True)

        self._grid_sf    = ScrollFrame(right, bg=BG)
        self._grid_inner = self._grid_sf.inner

    def _st(self, text, color=MUTED):
        self._st_var.set(text)
        self._st_dot.configure(fg=color)

    def _toggle_panel(self):
        if self._rpanel_open:
            self._rpanel.pack_forget()
            self._rpanel_open = False
            self._run_btn.configure(text="▶  Run Pipeline")
        else:
            self._rpanel.pack(fill="x")
            self._rpanel_open = True
            self._run_btn.configure(text="✕  Close")

    def _run(self):
        link = self._link_var.get().strip()
        out  = self._out_var.get().strip() or "output"
        if not link:
            messagebox.showwarning("Missing", "Paste your Google Drive link!")
            return
        self._cfg["last_link"]  = link
        self._cfg["output_dir"] = out
        self._save_cfg()
        self._go_btn.configure(text="⏳ Running...", state="disabled")
        self._ppf.pack(fill="x")
        self._ppbar.start(12)
        self._st("Processing...", YELLOW)

        def worker():
            import builtins; orig = builtins.print
            def patch(*a, **kw):
                msg = " ".join(str(x) for x in a)
                if msg.strip():
                    self.after(0, self._pplbl.configure, {"text": msg[:88]})
                orig(*a, **kw)
            builtins.print = patch
            try:
                from cors.pipeline import run_pipeline  # ✅ FIXED: was cors
                ok = run_pipeline(
                    drive_link  = link,
                    output_dir  = out,
                    batch_size  = self._cfg["batch_size"],
                    eps         = self._cfg["eps"],
                    min_samples = self._cfg["min_samples"])
            except Exception as e:
                self.after(0, self._pplbl.configure, {"text": f"❌ {e}"})
                ok = False
            finally:
                builtins.print = orig
            self.after(0, self._run_done, ok)

        threading.Thread(target=worker, daemon=True).start()

    def _run_done(self, ok):
        self._ppbar.stop(); self._ppf.pack_forget()
        self._go_btn.configure(text="▶  Start", state="normal")
        if ok: self._st("Done!", GREEN); self._load_groups()
        else:  self._st("Error!", RED)

    # ── Load groups ───────────────────────────────────────

    def _load_groups(self):
        for w in self._person_list.winfo_children(): w.destroy()
        self._rows={};self._selected=None;self._groups={}
        _THUMB_CACHE.clear();_TK_REFS.clear()
        self._clear_photos()
        self._welcome.pack(expand=True)

        gf = "data/groups.json"
        if not os.path.exists(gf):
            self._ph_lbl.configure(text="No groups yet")
            self._badge.pack_forget()
            self._st("Run pipeline first", YELLOW)
            return
        try:
            with open(gf) as f: self._groups = json.load(f)
        except Exception as e:
            self._st(f"Error: {e}", RED); return
        if not self._groups:
            self._ph_lbl.configure(text="Empty"); return

        names  = sorted(self._groups.keys(), key=lambda x:(x=="Unknown",x))
        people = [n for n in names if n != "Unknown"]

        self._ph_lbl.configure(text="People  ")
        self._badge.configure(text=str(len(people)))
        self._badge.pack(side="left")

        for name in names:
            faces    = self._groups[name]
            n_photos = len(set(f["filename"] for f in faces))
            n_faces  = len(faces)
            row = PersonRow(self._person_list, name, n_photos, n_faces,
                            on_select=self._select, on_download=self._dl_person)
            row.pack(fill="x")
            self._rows[name] = row

        self._st(f"{len(people)} people", GREEN)
        if HAS_PIL: self._load_avatars(names)

    # ── Avatar loading — 8 parallel workers ──────────────

    def _load_avatars(self, names):
        total = len(names)
        done  = [0]
        self._av_bar.configure(maximum=total, value=0)
        self._av_frame.pack(fill="x", pady=(0,4))

        def load_one(name):
            return name, fetch_face_pil(self._groups.get(name, []))

        def run():
            with ThreadPoolExecutor(max_workers=2) as ex:  # ✅ 8 parallel
                futs = {ex.submit(load_one, n): n for n in names}
                for fut in as_completed(futs):
                    try:   name, pil = fut.result()
                    except: name=futs[fut]; pil=None
                    done[0] += 1
                    self.after(0, self._av_bar.configure, {"value": done[0]})
                    self.after(0, self._av_lbl.configure,
                        {"text": f"Loading thumbnails  {done[0]} / {total}"})
                    if pil and name in self._rows:
                        tk_img = circle(pil, AVATAR_SZ)
                        _TK_REFS[name] = tk_img
                        self.after(0, self._rows[name].set_avatar, tk_img)
            self.after(0, self._av_frame.pack_forget)
            self.after(0, self._st,
                f"{len([n for n in names if n!='Unknown'])} people  •  ready", GREEN)

        threading.Thread(target=run, daemon=True).start()

    # ── Select person ─────────────────────────────────────

    def _select(self, name):
        if self._selected and self._selected in self._rows:
            self._rows[self._selected].select(False)
        self._selected = name
        self._rows[name].select(True)
        faces    = self._groups.get(name, [])
        n_photos = len(set(f["filename"] for f in faces))
        self._r_name.configure(text=name.replace("_"," "))
        self._r_sub.configure(
            text=f"{n_photos} photos  ·  {len(faces)} faces")
        self._dl_btn.pack(side="right")
        self._stream_photos(name, faces)

    # ── Stream photos — 8 parallel workers ───────────────

    def _stream_photos(self, name, faces):
        self._clear_photos()
        self._welcome.pack_forget()
        self._grid_sf.pack(fill="both", expand=True)

        unique = {}
        for face in faces:
            fn = face.get("filename",""); fid = face.get("file_id","")
            if fn and fid and fn not in unique: unique[fn] = fid
        items = list(unique.items())
        total = len(items)

        self._dlbar.configure(maximum=total, value=0)
        self._dlf.pack(after=self._rh)
        self._dllbl.configure(text=f"Loading  0 / {total} photos...")
        self._st(f"Loading {name}...", YELLOW)

        # pre-create placeholder tiles
        tiles = {}
        for i, (fn, _) in enumerate(items):
            ph = tk.Frame(self._grid_inner, bg=CARD,
                highlightbackground=BORDER, highlightthickness=1,
                width=TILE_SZ, height=TILE_SZ+28)
            ph.grid(row=i//COLS, column=i%COLS, padx=8, pady=8)
            ph.pack_propagate(False)
            lbl = tk.Label(ph, text="⏳", font=F(22), bg=CARD, fg=MUTED)
            lbl.pack(expand=True)
            name_lbl = tk.Label(ph,
                text=fn[:14]+"…" if len(fn)>16 else fn,
                bg=CARD, fg=MUTED, font=F(8))
            name_lbl.pack(pady=(0,4))
            tiles[fn] = (ph, lbl, name_lbl)

        def update_tile(fn, pil_img):
            if fn not in tiles: return
            ph, lbl, _ = tiles[fn]
            if pil_img and HAS_PIL:
                tk_img = to_tk(pil_img, TILE_SZ)
                self._tile_refs.append(tk_img)
                lbl.configure(image=tk_img, text="",
                               width=TILE_SZ, height=TILE_SZ)
                lbl.bind("<Button-1>",
                    lambda e, p=pil_img, f=fn: self._open_pil(p, f))
            else:
                lbl.configure(text="✗", fg=RED)

        def worker():
            from cors.downloader import download_one_image  # ✅ FIXED: was cors
            done = [0]
            lock = threading.Lock()

            def dl_one(fn_fid):
                fn, fid = fn_fid
                pil_img = None
                try:
                    tmp = download_one_image(fid, fn)
                    if tmp and os.path.exists(tmp):
                        pil_img = load_pil(tmp)
                        try: os.remove(tmp)
                        except: pass
                except Exception as e:
                    print(f"  stream fail {fn}: {e}")
                with lock:
                    done[0] += 1
                    current = done[0]
                pct = int(current / total * 100)
                self.after(0, update_tile, fn, pil_img)
                self.after(0, self._dlbar.configure, {"value": current})
                self.after(0, self._dllbl.configure,
                    {"text": f"Loading  {current} / {total}  ({pct}%)"})

            # ✅ 8 photos at the same time
            with ThreadPoolExecutor(max_workers=8) as ex:
                list(ex.map(dl_one, items))

            self.after(0, self._stream_done, name, done[0], total, items)

        threading.Thread(target=worker, daemon=True).start()

    def _stream_done(self, name, done, total, items):
        self._dllbl.configure(
            text=f"✅  {done} / {total} loaded  —  click ⬇ to save as zip")
        self._st(f"{name}  —  {done} photos", GREEN)
        self._loaded_items = {"name": name, "items": items}

    def _open_pil(self, pil_img, filename):
        win = tk.Toplevel(self)
        win.title(filename); win.configure(bg=BG)
        try:
            img = pil_img.copy()
            img.thumbnail((1200, 900), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            lbl = tk.Label(win, image=tk_img, bg=BG)
            lbl.image = tk_img; lbl.pack(padx=10, pady=10)
        except Exception:
            tk.Label(win, text=filename, bg=BG, fg=TEXT).pack(padx=20, pady=20)

    def _clear_photos(self):
        for w in self._grid_inner.winfo_children(): w.destroy()
        self._grid_sf.pack_forget()
        self._dlf.pack_forget()
        self._tile_refs   = []
        self._loaded_items= {}

    # ── Download as ZIP directly (no output folder) ───────

    def _dl_selected(self):
        if not self._selected: return
        items = getattr(self, "_loaded_items", {})
        if not items or items.get("name") != self._selected:
            messagebox.showinfo("Select first",
                "Click a person first to preview photos,\n"
                "then click Download as Zip.")
            return
        self._zip_person(items["name"], items["items"])

    def _dl_person(self, name, callback=None):
        """Called from sidebar ⬇ icon."""
        faces  = self._groups.get(name, [])
        unique = {}
        for face in faces:
            fn=face.get("filename",""); fid=face.get("file_id","")
            if fn and fid and fn not in unique: unique[fn]=fid
        self._zip_person(name, list(unique.items()), callback=callback)

    def _zip_person(self, name, items, callback=None):
        """
        Downloads all photos into a temp folder,
        zips them, asks where to save.
        output/ folder is NEVER touched.
        """
        # ask save path first
        save = filedialog.asksaveasfilename(
            title=f"Save {name} photos as zip",
            initialfile=f"{name}_photos.zip",
            defaultextension=".zip",
            filetypes=[("Zip files", "*.zip")])
        if not save:
            if callback: callback(False)
            return

        total = len(items)
        self._dlbar.configure(maximum=total, value=0)
        self._dlf.pack(after=self._rh)
        self._dllbl.configure(text=f"Downloading  0 / {total}...")
        self._dl_btn.configure(text="⏳  Zipping...", state="disabled")
        self._st(f"Saving {name}...", YELLOW)

        def worker():
            from cors.downloader import download_one_image  # ✅ FIXED: was cors
            done = [0]
            lock = threading.Lock()

            # use a temp folder — deleted after zipping
            tmp_dir = tempfile.mkdtemp(prefix="face_zip_")

            def dl_one(fn_fid):
                fn, fid = fn_fid
                try:
                    path = download_one_image(fid, fn)
                    if path and os.path.exists(path):
                        dest = os.path.join(tmp_dir, fn)
                        shutil.copy2(path, dest)
                        # remove from temp_batch after copying
                        try: os.remove(path)
                        except: pass
                        with lock:
                            done[0] += 1
                            current = done[0]
                        pct = int(current / total * 100)
                        self.after(0, self._dlbar.configure, {"value": current})
                        self.after(0, self._dllbl.configure,
                            {"text": f"Downloading  {current} / {total}  ({pct}%)"})
                except Exception as e:
                    print(f"  zip dl fail {fn}: {e}")

            # ✅ 8 parallel downloads
            with ThreadPoolExecutor(max_workers=8) as ex:
                list(ex.map(dl_one, items))

            # zip everything from temp folder
            self.after(0, self._dllbl.configure,
                {"text": f"Zipping {done[0]} photos..."})
            n_zipped = 0
            try:
                with zipfile.ZipFile(save, "w",
                        zipfile.ZIP_DEFLATED) as zf:
                    for fn in os.listdir(tmp_dir):
                        fp = os.path.join(tmp_dir, fn)
                        if os.path.exists(fp):
                            zf.write(fp, fn)
                            n_zipped += 1
                mb = os.path.getsize(save) / (1024*1024)
                self.after(0, self._zip_done,
                    name, save, n_zipped, mb, callback)
            except Exception as e:
                self.after(0, self._st, f"Zip error: {e}", RED)
                if callback: self.after(0, callback, False)
            finally:
                # clean up temp folder
                shutil.rmtree(tmp_dir, ignore_errors=True)

        threading.Thread(target=worker, daemon=True).start()

    def _zip_done(self, name, save, n, mb, callback):
        self._dl_btn.configure(text="⬇  Download as Zip", state="normal")
        self._dllbl.configure(
            text=f"✅  {n} photos saved  ({mb:.1f} MB)  →  {os.path.basename(save)}")
        self._st(f"Saved {n} photos ({mb:.1f} MB)", GREEN)
        if callback: callback(n > 0)
        # open folder
        subprocess.Popen(["xdg-open", os.path.dirname(save)])


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    App().mainloop()