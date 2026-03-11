#!/usr/bin/env python3
# cli.py — Interactive terminal for Face Organizer
# Run: python cli.py

import os
import sys
import json
import time
import shutil

# ── Must be set BEFORE any other imports ──────────────────
os.environ["CUDA_VISIBLE_DEVICES"]  = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# ── Colors ─────────────────────────────────────────────────
R  = "\033[0m"       # reset
B  = "\033[1m"       # bold
DIM= "\033[2m"       # dim

BLU= "\033[94m"      # blue
CYN= "\033[96m"      # cyan
GRN= "\033[92m"      # green
YLW= "\033[93m"      # yellow
RED= "\033[91m"      # red
MGN= "\033[95m"      # magenta
WHT= "\033[97m"      # white
GRY= "\033[90m"      # gray


def clr():
    os.system("clear")


def hr(char="─", color=GRY):
    w = shutil.get_terminal_size().columns
    print(f"{color}{char * w}{R}")


def banner():
    clr()
    print(f"""
{BLU}{B}
  ███████╗ █████╗  ██████╗███████╗
  ██╔════╝██╔══██╗██╔════╝██╔════╝
  █████╗  ███████║██║     █████╗
  ██╔══╝  ██╔══██║██║     ██╔══╝
  ██║     ██║  ██║╚██████╗███████╗
  ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝
{R}{CYN}  ██████╗ ██████╗  ██████╗  █████╗ ███╗   ██╗██╗███████╗███████╗██████╗
  ██╔═══██╗██╔══██╗██╔════╝ ██╔══██╗████╗  ██║██║╚══███╔╝██╔════╝██╔══██╗
  ██║   ██║██████╔╝██║  ███╗███████║██╔██╗ ██║██║  ███╔╝ █████╗  ██████╔╝
  ██║   ██║██╔══██╗██║   ██║██╔══██║██║╚██╗██║██║ ███╔╝  ██╔══╝  ██╔══██╗
  ╚██████╔╝██║  ██║╚██████╔╝██║  ██║██║ ╚████║██║███████╗███████╗██║  ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚══════╝╚══════╝╚═╝  ╚═╝
{R}""")
    hr()
    # print(f"  {GRY}Sort photos by face using AI  •  v1.0{R}\n")


def title(text):
    print(f"\n{BLU}{B}{'─'*3} {text} {'─'*3}{R}\n")


def success(text):
    print(f"  {GRN}✅  {text}{R}")


def error(text):
    print(f"  {RED}❌  {text}{R}")


def warn(text):
    print(f"  {YLW}⚠️   {text}{R}")


def info(text):
    print(f"  {CYN}ℹ️   {text}{R}")


def log(text):
    print(f"  {GRY}    {text}{R}")


def step(n, text):
    print(f"\n  {BLU}{B}[{n}]{R} {WHT}{B}{text}{R}")


def ask(prompt, default=None):
    if default:
        q = f"  {CYN}❯{R} {WHT}{prompt}{R} {GRY}[{default}]{R}: "
    else:
        q = f"  {CYN}❯{R} {WHT}{prompt}{R}: "
    try:
        val = input(q).strip()
        return val if val else default
    except KeyboardInterrupt:
        print(f"\n\n  {YLW}Cancelled.{R}\n")
        sys.exit(0)


def ask_choice(prompt, choices, default=None):
    print(f"\n  {WHT}{B}{prompt}{R}")
    for i, (key, label) in enumerate(choices, 1):
        marker = f"{GRN}●{R}" if key == default else f"{GRY}○{R}"
        print(f"    {marker} {CYN}{key}{R}  {label}")
    print()
    val = ask("Choose", default)
    return val


def spinner(msg):
    """Simple inline spinner context."""
    import threading

    class Spin:
        def __init__(self):
            self.running = False
            self.thread  = None

        def start(self, text):
            self.running = True
            self.text    = text
            self.thread  = threading.Thread(
                target=self._spin, daemon=True)
            self.thread.start()

        def _spin(self):
            frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
            i = 0
            while self.running:
                print(
                    f"\r  {BLU}{frames[i % len(frames)]}{R}"
                    f"  {self.text}   ",
                    end="", flush=True)
                time.sleep(0.1)
                i += 1

        def stop(self, ok=True):
            self.running = False
            if self.thread:
                self.thread.join()
            icon = f"{GRN}✅{R}" if ok else f"{RED}❌{R}"
            print(f"\r  {icon}  {self.text}   ")

    return Spin()


def progress_bar(current, total, label="", width=40):
    pct  = current / total if total > 0 else 0
    done = int(width * pct)
    bar  = f"{GRN}{'█' * done}{GRY}{'░' * (width-done)}{R}"
    pct_str = f"{int(pct*100):3d}%"
    print(
        f"\r  {bar} {CYN}{pct_str}{R}  {GRY}{label}{R}",
        end="", flush=True)
    if current >= total:
        print()


# ══════════════════════════════════════════════════════════
#  MENU SCREENS
# ══════════════════════════════════════════════════════════

def main_menu():
    banner()
    print(f"  {WHT}{B}What would you like to do?{R}\n")
    options = [
        ("1", "Run full pipeline  (Drive → Sort photos)"),
        ("2", "View results       (See sorted people)"),
        ("3", "Re-cluster faces   (Tune grouping)"),
        ("4", "Download results   (Save as zip)"),
        ("5", "Check status       (Files & stats)"),
        ("6", "Settings           (eps, batch size)"),
        ("0", "Exit"),
    ]
    for key, label in options:
        if key == "0":
            print(f"    {GRY}○{R}  {GRY}{key}  {label}{R}")
        else:
            print(f"    {CYN}○{R}  {CYN}{B}{key}{R}  {WHT}{label}{R}")
    print()
    choice = ask("Enter choice", "1")
    return choice.strip()


# ══════════════════════════════════════════════════════════
#  SCREEN 1 — RUN PIPELINE
# ══════════════════════════════════════════════════════════

def screen_run():
    clr()
    hr()
    print(f"\n  {BLU}{B}▶  RUN FACE ORGANIZER{R}\n")
    hr()

    # get settings
    cfg = load_settings()

    print(f"\n  {GRY}Current settings:{R}")
    print(f"    Output folder : {CYN}{cfg['output_dir']}{R}")
    print(f"    Batch size    : {CYN}{cfg['batch_size']}{R}")
    print(f"    Clustering eps: {CYN}{cfg['eps']}{R}")

    print()
    drive_link = ask(
        "Paste Google Drive folder link",
        cfg.get("last_link", ""))

    if not drive_link:
        error("No link provided!")
        input(f"\n  {GRY}Press Enter to go back...{R}")
        return

    # confirm
    print(f"\n  {GRY}Ready to process:{R}")
    print(f"    Link  : {CYN}{drive_link[:60]}...{R}")
    print(f"    Output: {CYN}{cfg['output_dir']}{R}")
    print()

    confirm = ask("Start? (y/n)", "y")
    if confirm.lower() != "y":
        warn("Cancelled.")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    # save last link
    cfg["last_link"] = drive_link
    save_settings(cfg)

    print()
    hr()

    # patch print to show nicely
    import builtins
    original_print = builtins.print

    def nice_print(*args, **kwargs):
        msg = " ".join(str(a) for a in args)
        if not msg.strip():
            return
        if "✅" in msg:
            original_print(f"  {GRN}{msg}{R}")
        elif "❌" in msg:
            original_print(f"  {RED}{msg}{R}")
        elif "⚠" in msg:
            original_print(f"  {YLW}{msg}{R}")
        elif "STEP" in msg or "===" in msg:
            original_print(f"\n  {BLU}{B}{msg}{R}")
        elif "Progress:" in msg:
            original_print(f"  {MGN}{msg}{R}")
        elif "Saved" in msg or "Loaded" in msg:
            original_print(f"  {CYN}{msg}{R}")
        else:
            original_print(f"  {GRY}{msg}{R}")

    builtins.print = nice_print

    try:
        from cors.pipeline import run_pipeline
        result = run_pipeline(
            drive_link  = drive_link,
            output_dir  = cfg["output_dir"],
            batch_size  = cfg["batch_size"],
            eps         = cfg["eps"],
            min_samples = cfg["min_samples"],
        )
    except Exception as e:
        builtins.print = original_print
        error(f"Pipeline failed: {e}")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    builtins.print = original_print

    hr()
    if result:
        print(f"\n  {GRN}{B}🎉  DONE! Photos sorted successfully!{R}\n")
        success(f"Check your '{cfg['output_dir']}/' folder")
    else:
        error("Pipeline finished with errors")

    input(f"\n  {GRY}Press Enter to continue...{R}")


# ══════════════════════════════════════════════════════════
#  SCREEN 2 — VIEW RESULTS
# ══════════════════════════════════════════════════════════

def screen_view():
    clr()
    hr()
    print(f"\n  {BLU}{B}👁  VIEW RESULTS{R}\n")
    hr()

    cfg = load_settings()
    out = cfg["output_dir"]

    if not os.path.exists(out):
        warn(f"Output folder '{out}' not found!")
        warn("Run the pipeline first.")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    folders = sorted([
        f for f in os.listdir(out)
        if os.path.isdir(os.path.join(out, f))
    ])

    if not folders:
        warn("No person folders found yet!")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    # count photos
    people  = [f for f in folders if f != "Unknown"]
    unknown = "Unknown" if "Unknown" in folders else None

    print(f"\n  {WHT}{B}Found {len(people)} people "
          f"+ {'Unknown' if unknown else 'no unknown'}{R}\n")

    total_photos = 0
    print(f"  {'Person':<15} {'Photos':>8}  {'Preview'}")
    print(f"  {GRY}{'─'*50}{R}")

    for folder in folders:
        path   = os.path.join(out, folder)
        photos = [
            f for f in os.listdir(path)
            if f.lower().endswith((
                '.jpg','.jpeg','.png','.bmp','.webp'))
        ]
        total_photos += len(photos)

        # show first 3 filenames as preview
        preview = ", ".join(
            p[:15] for p in photos[:3])
        if len(photos) > 3:
            preview += f" ... +{len(photos)-3} more"

        color = YLW if folder == "Unknown" else GRN
        print(
            f"  {color}{B}{folder:<15}{R}"
            f" {CYN}{len(photos):>8}{R}  "
            f"{GRY}{preview}{R}")

    print(f"\n  {GRY}{'─'*50}{R}")
    print(
        f"  {'TOTAL':<15} {CYN}{total_photos:>8}{R}  "
        f"{GRY}photos{R}")

    # fingerprints stats
    fp_file = "data/fingerprints.json"
    if os.path.exists(fp_file):
        with open(fp_file) as f:
            fps = json.load(f)
        print(f"\n  {GRY}Fingerprints saved: "
              f"{CYN}{len(fps)}{GRY} faces{R}")

    print()
    print(f"  {GRY}Options:{R}")
    print(f"    {CYN}o{R}  Open output folder")
    print(f"    {CYN}p{R}  Open specific person folder")
    print(f"    {CYN}b{R}  Back to menu")
    print()

    choice = ask("Choice", "b")

    if choice == "o":
        os.system(f"xdg-open {out}")
    elif choice == "p":
        person = ask(
            "Enter person name (e.g. Person_01)")
        path = os.path.join(out, person)
        if os.path.exists(path):
            os.system(f"xdg-open {path}")
        else:
            error(f"Folder not found: {path}")
            time.sleep(1)


# ══════════════════════════════════════════════════════════
#  SCREEN 3 — RE-CLUSTER
# ══════════════════════════════════════════════════════════

def screen_recluster():
    clr()
    hr()
    print(f"\n  {BLU}{B}🔄  RE-CLUSTER FACES{R}\n")
    hr()

    fp_file = "data/fingerprints.json"
    if not os.path.exists(fp_file):
        warn("No fingerprints found!")
        warn("Run the pipeline first.")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    with open(fp_file) as f:
        fps = json.load(f)

    info(f"Loaded {len(fps)} fingerprints")

    # test eps values
    print(f"\n  {WHT}{B}Testing different eps values...{R}\n")
    print(f"  {GRY}(eps controls how strict grouping is){R}")
    print(f"  {GRY}(lower = more groups, higher = fewer groups){R}\n")

    try:
        from core.clusterer import (
            load_fingerprints, group_faces)

        fingerprints = load_fingerprints()

        print(f"  {GRY}{'eps':>6}  {'People':>8}  "
              f"{'Unknown':>8}  {'Result'}{R}")
        print(f"  {GRY}{'─'*50}{R}")

        for eps in [0.3, 0.35, 0.4, 0.45,
                    0.5, 0.55, 0.6, 0.65, 0.7]:
            groups  = group_faces(
                fingerprints, eps=eps,
                min_samples=2)
            people  = len([
                p for p in groups
                if p != "Unknown"])
            unknown = len(
                groups.get("Unknown", []))

            # color code
            if people <= 1:
                pc = RED
                note = "← too loose"
            elif people >= 10:
                pc = YLW
                note = "← maybe too strict"
            else:
                pc = GRN
                note = "← looks good ✓"

            print(
                f"  {CYN}{eps:>6}{R}  "
                f"{pc}{people:>8}{R}  "
                f"{YLW}{unknown:>8}{R}  "
                f"{GRY}{note}{R}")

    except Exception as e:
        error(f"Failed to test: {e}")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    cfg = load_settings()
    print(f"\n  {GRY}Current eps: {CYN}{cfg['eps']}{R}")
    new_eps = ask(
        "Enter new eps value", str(cfg["eps"]))

    try:
        new_eps = float(new_eps)
    except ValueError:
        error("Invalid value!")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    cfg["eps"] = new_eps
    save_settings(cfg)

    print()
    confirm = ask(
        "Re-run clustering and organize now? (y/n)",
        "y")
    if confirm.lower() != "y":
        success(f"eps saved as {new_eps}")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    print()
    hr()

    try:
        import builtins
        orig = builtins.print

        def np(*args, **kwargs):
            msg = " ".join(str(a) for a in args)
            if msg.strip():
                orig(f"  {GRY}{msg}{R}")

        builtins.print = np

        from core.clusterer import (
            load_fingerprints, group_faces, save_groups)
        from core.organizer import (
            load_groups, organize_results)

        builtins.print = orig

        # delete old output
        out = cfg["output_dir"]
        if os.path.exists(out):
            shutil.rmtree(out)
            info(f"Cleared old output/")

        fingerprints = load_fingerprints()
        groups = group_faces(
            fingerprints,
            eps         = new_eps,
            min_samples = cfg["min_samples"])
        save_groups(groups)
        groups = load_groups()
        organize_results(groups, output_dir=out)

        builtins.print = orig
        hr()
        people = len([
            p for p in groups if p != "Unknown"])
        success(
            f"Done! Found {people} people "
            f"with eps={new_eps}")

    except Exception as e:
        builtins.print = builtins.print
        error(f"Failed: {e}")

    input(f"\n  {GRY}Press Enter...{R}")


# ══════════════════════════════════════════════════════════
#  SCREEN 4 — DOWNLOAD
# ══════════════════════════════════════════════════════════

def screen_download():
    import zipfile

    clr()
    hr()
    print(f"\n  {BLU}{B}⬇  DOWNLOAD RESULTS{R}\n")
    hr()

    cfg = load_settings()
    out = cfg["output_dir"]

    if not os.path.exists(out):
        warn("No output folder found!")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    folders = sorted([
        f for f in os.listdir(out)
        if os.path.isdir(os.path.join(out, f))
    ])

    if not folders:
        warn("No folders to download!")
        input(f"\n  {GRY}Press Enter...{R}")
        return

    print(f"\n  {WHT}{B}Download options:{R}\n")
    print(f"    {CYN}1{R}  Download ALL people (one zip)")
    print(f"    {CYN}2{R}  Download ONE person (choose)")
    print(f"    {CYN}b{R}  Back")
    print()

    choice = ask("Choice", "1")

    if choice == "b":
        return

    home = os.path.expanduser("~")

    if choice == "1":
        zip_path = os.path.join(home, "all_people.zip")
        zip_path = ask("Save zip as", zip_path)

        print(f"\n  {GRY}Zipping all folders...{R}\n")
        total = 0

        with zipfile.ZipFile(
                zip_path, 'w',
                zipfile.ZIP_DEFLATED) as zf:

            all_files = []
            for folder in folders:
                path = os.path.join(out, folder)
                for f in os.listdir(path):
                    if f.lower().endswith((
                            '.jpg','.jpeg','.png',
                            '.bmp','.webp')):
                        all_files.append(
                            (folder, f))

            for i, (folder, filename) in enumerate(
                    all_files, 1):
                fp  = os.path.join(out, folder, filename)
                arc = os.path.join(folder, filename)
                zf.write(fp, arc)
                total += 1
                progress_bar(
                    i, len(all_files),
                    f"{folder}/{filename}")

        mb = os.path.getsize(zip_path) / (1024*1024)
        print()
        success(
            f"Saved {total} photos "
            f"({mb:.1f} MB) → {zip_path}")

    elif choice == "2":
        print(f"\n  {WHT}Available folders:{R}\n")
        for i, folder in enumerate(folders, 1):
            path   = os.path.join(out, folder)
            count  = len([
                f for f in os.listdir(path)
                if f.lower().endswith((
                    '.jpg','.jpeg','.png',
                    '.bmp','.webp'))
            ])
            color = YLW if folder == "Unknown" else GRN
            print(
                f"    {CYN}{i:2d}{R}  "
                f"{color}{folder:<15}{R}  "
                f"{GRY}{count} photos{R}")

        print()
        idx = ask("Enter number")
        try:
            folder = folders[int(idx) - 1]
        except (ValueError, IndexError):
            error("Invalid choice!")
            time.sleep(1)
            return

        zip_path = os.path.join(
            home, f"{folder}_photos.zip")
        zip_path = ask("Save zip as", zip_path)

        folder_path = os.path.join(out, folder)
        photos = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith((
                '.jpg','.jpeg','.png',
                '.bmp','.webp'))
        ]

        print(f"\n  {GRY}Zipping {folder}...{R}\n")

        with zipfile.ZipFile(
                zip_path, 'w',
                zipfile.ZIP_DEFLATED) as zf:
            for i, filename in enumerate(photos, 1):
                fp = os.path.join(folder_path, filename)
                zf.write(fp, filename)
                progress_bar(
                    i, len(photos), filename)

        mb = os.path.getsize(zip_path) / (1024*1024)
        print()
        success(
            f"Saved {len(photos)} photos "
            f"({mb:.1f} MB) → {zip_path}")

    input(f"\n  {GRY}Press Enter...{R}")


# ══════════════════════════════════════════════════════════
#  SCREEN 5 — STATUS
# ══════════════════════════════════════════════════════════

def screen_status():
    clr()
    hr()
    print(f"\n  {BLU}{B}📊  STATUS & STATS{R}\n")
    hr()

    cfg = load_settings()

    def file_stat(label, path):
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 1024*1024:
                sz = f"{size/(1024*1024):.1f} MB"
            elif size > 1024:
                sz = f"{size/1024:.1f} KB"
            else:
                sz = f"{size} bytes"
            print(
                f"  {GRN}✅{R}  {WHT}{label:<25}{R}"
                f"  {CYN}{sz}{R}  "
                f"{GRY}{path}{R}")
        else:
            print(
                f"  {RED}✗{R}   {WHT}{label:<25}{R}"
                f"  {GRY}not found{R}")

    print(f"\n  {WHT}{B}Data Files:{R}\n")
    file_stat("fingerprints.json",
              "data/fingerprints.json")
    file_stat("groups.json",
              "data/groups.json")

    # fingerprint details
    fp_file = "data/fingerprints.json"
    if os.path.exists(fp_file):
        with open(fp_file) as f:
            fps = json.load(f)
        photos = set(x["filename"] for x in fps)
        print(f"\n  {WHT}{B}Fingerprint Stats:{R}\n")
        print(f"    Total faces    : {CYN}{len(fps)}{R}")
        print(f"    Unique photos  : "
              f"{CYN}{len(photos)}{R}")
        avg = len(fps)/len(photos) if photos else 0
        print(f"    Avg faces/photo: "
              f"{CYN}{avg:.1f}{R}")

    # output folder
    out = cfg["output_dir"]
    print(f"\n  {WHT}{B}Output Folder:{R}\n")
    if os.path.exists(out):
        folders = [
            f for f in os.listdir(out)
            if os.path.isdir(os.path.join(out, f))]
        people  = [
            f for f in folders if f != "Unknown"]
        total   = 0
        for folder in folders:
            path = os.path.join(out, folder)
            n = len([
                f for f in os.listdir(path)
                if f.lower().endswith((
                    '.jpg','.jpeg','.png',
                    '.bmp','.webp'))
            ])
            total += n
        print(f"    People found   : {GRN}{len(people)}{R}")
        print(f"    Total folders  : {CYN}{len(folders)}{R}")
        print(f"    Total photos   : {CYN}{total}{R}")
    else:
        print(f"    {GRY}Output folder not found yet{R}")

    print(f"\n  {WHT}{B}Current Settings:{R}\n")
    print(f"    Output dir  : {CYN}{cfg['output_dir']}{R}")
    print(f"    Batch size  : {CYN}{cfg['batch_size']}{R}")
    print(f"    Clustering  : {CYN}eps={cfg['eps']}, "
          f"min_samples={cfg['min_samples']}{R}")
    print(f"    Detector    : {CYN}retinaface{R}")
    print(f"    Model       : {CYN}ArcFace{R}")

    print()
    input(f"  {GRY}Press Enter to continue...{R}")


# ══════════════════════════════════════════════════════════
#  SCREEN 6 — SETTINGS
# ══════════════════════════════════════════════════════════

def screen_settings():
    clr()
    hr()
    print(f"\n  {BLU}{B}⚙  SETTINGS{R}\n")
    hr()

    cfg = load_settings()

    print(f"\n  {GRY}Leave blank to keep current value{R}\n")

    # output dir
    print(f"  {GRY}Current output folder: "
          f"{CYN}{cfg['output_dir']}{R}")
    val = ask("Output folder", cfg["output_dir"])
    if val:
        cfg["output_dir"] = val

    # batch size
    print(f"\n  {GRY}Current batch size: "
          f"{CYN}{cfg['batch_size']}{R}")
    print(f"  {GRY}(how many photos to process at once){R}")
    val = ask("Batch size", str(cfg["batch_size"]))
    try:
        cfg["batch_size"] = int(val)
    except ValueError:
        pass

    # eps
    print(f"\n  {GRY}Current eps: {CYN}{cfg['eps']}{R}")
    print(f"  {GRY}(0.3=strict/more groups, "
          f"0.7=loose/fewer groups){R}")
    val = ask("Clustering eps", str(cfg["eps"]))
    try:
        cfg["eps"] = float(val)
    except ValueError:
        pass

    # min samples
    print(f"\n  {GRY}Current min_samples: "
          f"{CYN}{cfg['min_samples']}{R}")
    print(f"  {GRY}(min photos of same person "
          f"to form a group){R}")
    val = ask("Min samples",
              str(cfg["min_samples"]))
    try:
        cfg["min_samples"] = int(val)
    except ValueError:
        pass

    save_settings(cfg)
    print()
    success("Settings saved!")
    time.sleep(1)


# ══════════════════════════════════════════════════════════
#  SETTINGS FILE
# ══════════════════════════════════════════════════════════

SETTINGS_FILE = "data/cli_settings.json"

DEFAULT_SETTINGS = {
    "output_dir"  : "output",
    "batch_size"  : 100,
    "eps"         : 0.6,
    "min_samples" : 2,
    "last_link"   : "",
}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                s = json.load(f)
            # fill missing keys with defaults
            for k, v in DEFAULT_SETTINGS.items():
                if k not in s:
                    s[k] = v
            return s
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(cfg):
    os.makedirs("data", exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ══════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════

def main():
    # make sure we're in the right directory
    script_dir = os.path.dirname(
        os.path.abspath(__file__))
    os.chdir(script_dir)

    while True:
        choice = main_menu()

        if choice == "1":
            screen_run()
        elif choice == "2":
            screen_view()
        elif choice == "3":
            screen_recluster()
        elif choice == "4":
            screen_download()
        elif choice == "5":
            screen_status()
        elif choice == "6":
            screen_settings()
        elif choice == "0":
            clr()
            print(f"\n  {CYN}Bye! 👋{R}\n")
            sys.exit(0)
        else:
            warn("Invalid choice, try again.")
            time.sleep(0.5)


if __name__ == "__main__":
    main()