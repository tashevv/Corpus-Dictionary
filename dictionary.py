import sys
import os
import subprocess
import csv
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox

# Add the local 'lib' folder to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import requests


# =========================================================
# CONFIG
# =========================================================

DICTIONARY_PATH = os.path.join("data", "dictionary.txt")
FLAGS_PATH = os.path.join("data", "flagged_ranks.txt")

POS_MAP = {
    "n": "Noun",
    "v": "Verb",
    "j": "Adjective",
    "r": "Adverb",
    "p": "Pronoun",
    "d": "Determiner",
    "i": "Preposition",
    "c": "Conjunction",
    "a": "Article",
    "m": "Numeral",
    "u": "Interjection",
    "x": "Unknown"
}

# =========================================================
# DICTIONARY LOADING
# =========================================================

def load_dictionary(path):

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dictionary file not found:\n{path}"
        )

    entries = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:

        reader = csv.reader(f, delimiter="\t")

        for row in reader:

            # Skip malformed/header rows
            if len(row) < 5:
                continue

            rank, lemma, pos, freq, dispersion = row[:5]

            # Skip separator rows
            if rank == "----":
                continue

            # Skip header row
            if rank.lower() == "rank":
                continue

            try:
                entry = {
                    "rank": int(rank),
                    "lemma": lemma.strip(),
                    "pos": pos.strip(),
                    "freq": int(freq),
                    "dispersion": float(dispersion)
                }

                entries.append(entry)

            except:
                continue

    return entries


# =========================================================
# API LOOKUP
# =========================================================

def fetch_definition(word):

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

    try:

        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return "No definition found."

        data = response.json()

        definitions = []

        for meaning in data[0].get("meanings", []):

            part = meaning.get("partOfSpeech", "")

            for definition_data in meaning.get("definitions", []):

                definition = definition_data.get("definition", "")

                if definition:
                    definitions.append(
                        f"[{part}] {definition}"
                    )

        if not definitions:
            return "No definition found."

        return "\n\n".join(definitions[:10])

    except Exception as e:
        return f"Definition lookup failed:\n{e}"


# =========================================================
# GUI
# =========================================================

class DictionaryApp:

    def __init__(self, root):

        self.root = root
        root.iconbitmap("icon.ico")
        self.root.title("Corpus Dictionary")
        self.root.geometry("1000x450")
        self.root.minsize(1000, 450)

        self.entries = []
        self.flagged_ranks = set()

        self.current_word = ""

        self.build_ui()
        self.load_flags()
        self.load_data()

    # =====================================================
    # FLAGS
    # =====================================================

    def load_flags(self):

        self.flagged_ranks = set()

        if not os.path.exists(FLAGS_PATH):
            return

        try:

            with open(
                    FLAGS_PATH,
                    "r",
                    encoding="utf-8"
            ) as f:

                for line in f:

                    line = line.strip()

                    if not line:
                        continue

                    try:
                        self.flagged_ranks.add(int(line))
                    except:
                        pass

        except:
            pass

    # -----------------------------------------------------

    def save_flags(self):

        try:

            os.makedirs(
                os.path.dirname(FLAGS_PATH),
                exist_ok=True
            )

            with open(
                    FLAGS_PATH,
                    "w",
                    encoding="utf-8"
            ) as f:

                for rank in sorted(self.flagged_ranks):
                    f.write(str(rank) + "\n")

        except Exception as e:

            messagebox.showerror(
                "Save Error",
                f"Failed to save flags:\n{e}"
            )

    # -----------------------------------------------------

    def toggle_flag(self):

        selected = self.tree.selection()

        if not selected:
            return

        item = self.tree.item(selected[0])

        rank = int(item["values"][0])

        if rank in self.flagged_ranks:
            self.flagged_ranks.remove(rank)
        else:
            self.flagged_ranks.add(rank)

        self.save_flags()

        self.filter_entries()

        self.update_flag_button()

    # -----------------------------------------------------

    def update_flag_button(self):

        selected = self.tree.selection()

        if not selected:
            self.flag_button.config(
                text="Toggle Flag"
            )

            return

        item = self.tree.item(selected[0])

        rank = int(item["values"][0])

        if rank in self.flagged_ranks:

            self.flag_button.config(
                text="Unflag Word"
            )

        else:

            self.flag_button.config(
                text="Flag Word"
            )

    # =====================================================
    # BUILD UI
    # =====================================================

    def build_ui(self):

        PADX = 6
        PADY = 6

        root_frame = tk.Frame(
            self.root,
            padx=PADX,
            pady=PADY
        )

        root_frame.pack(
            fill="both",
            expand=True
        )

        # =================================================
        # LEFT PANEL
        # =================================================

        left_panel = tk.Frame(
            root_frame,
            width=560
        )

        left_panel.pack(
            side="left",
            fill="y"
        )

        left_panel.pack_propagate(False)

        # =================================================
        # SEARCH BAR
        # =================================================

        search_frame = tk.Frame(left_panel)

        search_frame.pack(
            fill="x",
            pady=(0, PADY)
        )

        tk.Label(
            search_frame,
            text="Search:"
        ).pack(side="left")

        self.search_entry = tk.Entry(
            search_frame,
            width=80
        )

        self.search_entry.pack(
            side="left",
            padx=(5, 0)
        )

        self.search_entry.bind(
            "<KeyRelease>",
            self.filter_entries
        )

        # =================================================
        # FILTER BAR
        # =================================================

        filter_frame = tk.Frame(left_panel)

        filter_frame.pack(
            fill="x",
            pady=(0, PADY)
        )

        tk.Label(
            filter_frame,
            text="Filter by:"
        ).pack(side="left")

        self.filter_type = ttk.Combobox(
            filter_frame,
            values=[
                "Rank",
                "Frequency",
                "Dispersion"
            ],
            state="readonly",
            width=12
        )

        self.filter_type.pack(
            side="left",
            padx=(5, 5)
        )

        self.filter_type.set("Rank")

        tk.Label(
            filter_frame,
            text="Min"
        ).pack(side="left")

        self.filter_min = tk.Entry(
            filter_frame,
            width=10
        )

        self.filter_min.pack(
            side="left",
            padx=(5, 10)
        )

        tk.Label(
            filter_frame,
            text="Max"
        ).pack(side="left")

        self.filter_max = tk.Entry(
            filter_frame,
            width=10
        )

        self.filter_max.pack(
            side="left",
            padx=(5, 0)
        )

        self.filter_type.bind(
            "<<ComboboxSelected>>",
            self.filter_entries
        )

        self.filter_min.bind(
            "<KeyRelease>",
            self.filter_entries
        )

        self.filter_max.bind(
            "<KeyRelease>",
            self.filter_entries
        )

        # =================================================
        # FLAG FILTER
        # =================================================

        self.show_flagged_only = tk.BooleanVar()

        flagged_checkbox = tk.Checkbutton(
            left_panel,
            text="Show flagged only",
            variable=self.show_flagged_only,
            command=self.filter_entries
        )

        flagged_checkbox.pack(
            anchor="w",
            pady=(0, PADY)
        )

        # =================================================
        # STATUS LABEL
        # =================================================

        self.status_label = tk.Label(
            left_panel,
            text="Loading...",
            font=("Arial", 9)
        )

        self.status_label.pack(
            anchor="w",
            pady=(0, PADY)
        )

        # =================================================
        # TREEVIEW FRAME
        # =================================================

        tree_frame = tk.Frame(left_panel)

        tree_frame.pack(
            fill="both",
            expand=True
        )

        columns = (
            "Rank",
            "Lemma",
            "PoS",
            "Freq",
            "Disp"
        )

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings"
        )

        self.tree.heading("Rank", text="Rank")
        self.tree.heading("Lemma", text="Word")
        self.tree.heading("PoS", text="PoS")
        self.tree.heading("Freq", text="Frequency")
        self.tree.heading("Disp", text="Dispersion")

        self.tree.column(
            "Rank",
            width=60,
            anchor="center"
        )

        self.tree.column(
            "Lemma",
            width=120
        )

        self.tree.column(
            "PoS",
            width=80,
            anchor="center"
        )

        self.tree.column(
            "Freq",
            width=80,
            anchor="e"
        )

        self.tree.column(
            "Disp",
            width=80,
            anchor="center"
        )

        y_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree.yview
        )

        x_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )

        self.tree.tag_configure(
            "flagged",
            background="#fff2a8"
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        y_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        x_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        tree_frame.grid_rowconfigure(
            0,
            weight=1
        )

        tree_frame.grid_columnconfigure(
            0,
            weight=1
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select_word
        )

        # =================================================
        # RIGHT PANEL
        # =================================================

        right_panel = tk.Frame(
            root_frame,
            padx=PADX,
            pady=PADY
        )

        right_panel.pack(
            side="right",
            fill="both",
            expand=True
        )

        title_frame = tk.Frame(right_panel)

        title_frame.pack(
            anchor="nw",
            fill="x",
            pady=(0, 10)
        )

        self.word_title = tk.Label(
            title_frame,
            text="Select a word",
            font=("Arial", 22, "bold")
        )

        self.word_title.pack(
            side="left"
        )

        self.speak_button = tk.Button(
            title_frame,
            text="🔊",
            command=self.speak_word
        )

        self.speak_button.pack(
            side="left",
            padx=(10, 0)
        )

        self.meta_label = tk.Label(
            right_panel,
            text="",
            font=("Arial", 10),
            justify="left"
        )

        self.meta_label.pack(
            anchor="nw",
            pady=(0, 10)
        )

        self.flag_button = tk.Button(
            right_panel,
            text="Toggle Flag",
            command=self.toggle_flag,
            width=18
        )

        self.flag_button.pack(
            anchor="nw",
            pady=(0, 10)
        )

        definition_frame = tk.Frame(right_panel)

        definition_frame.pack(
            fill="both",
            expand=True
        )

        self.definition_box = tk.Text(
            definition_frame,
            wrap="word",
            font=("Arial", 12)
        )

        self.definition_box.pack(
            side="left",
            fill="both",
            expand=True
        )

        definition_scrollbar = ttk.Scrollbar(
            definition_frame,
            orient="vertical",
            command=self.definition_box.yview
        )

        self.definition_box.configure(
            yscrollcommand=definition_scrollbar.set
        )

        definition_scrollbar.pack(
            side="right",
            fill="y"
        )

    # =====================================================
    # LOAD DATA
    # =====================================================

    def load_data(self):

        try:

            self.entries = load_dictionary(
                DICTIONARY_PATH
            )

            self.populate_tree()

            self.status_label.config(
                text=f"{len(self.entries):,} entries loaded"
            )

        except Exception as e:

            messagebox.showerror(
                "Load Error",
                str(e)
            )

    # =====================================================
    # POPULATE TREE
    # =====================================================

    def populate_tree(self, filter_text=""):

        # CLEAR TREE

        for item in self.tree.get_children():
            self.tree.delete(item)

        filtered = self.entries

        # =================================================
        # SEARCH FILTER
        # =================================================

        if filter_text:

            filter_text = filter_text.lower()

            filtered = [
                entry for entry in filtered
                if filter_text in entry["lemma"].lower()
            ]

        # =================================================
        # FILTER TYPE
        # =================================================

        filter_type = self.filter_type.get()

        field_map = {
            "Rank": "rank",
            "Frequency": "freq",
            "Dispersion": "dispersion"
        }

        field = field_map.get(filter_type)

        # =================================================
        # PARSE MIN/MAX
        # =================================================

        min_value = self.filter_min.get().strip()
        max_value = self.filter_max.get().strip()

        try:
            min_value = float(min_value) if min_value else None
        except:
            min_value = None

        try:
            max_value = float(max_value) if max_value else None
        except:
            max_value = None

        # =================================================
        # APPLY FILTERS
        # =================================================

        final_filtered = []

        flagged_only = self.show_flagged_only.get()

        for entry in filtered:

            value = entry[field]

            # MIN CHECK

            if min_value is not None:

                if value < min_value:
                    continue

            # MAX CHECK

            if max_value is not None:

                if value > max_value:
                    continue

            # FLAG FILTER

            if flagged_only:

                if entry["rank"] not in self.flagged_ranks:
                    continue

            final_filtered.append(entry)

        # =================================================
        # INSERT ROWS
        # =================================================

        for entry in final_filtered:

            pos_name = POS_MAP.get(
                entry["pos"].lower(),
                entry["pos"]
            )

            tags = ()

            if entry["rank"] in self.flagged_ranks:
                tags = ("flagged",)

            self.tree.insert(
                "",
                "end",
                values=(
                    entry["rank"],
                    entry["lemma"],
                    pos_name,
                    f"{entry['freq']:,}",
                    f"{entry['dispersion']:.2f}"
                ),
                tags=tags
            )

        # =================================================
        # STATUS
        # =================================================

        shown_count = len(final_filtered)

        shown_flagged_count = sum(
            1
            for entry in final_filtered
            if entry["rank"] in self.flagged_ranks
        )

        flagged_percent = 0

        if shown_count > 0:
            flagged_percent = (
                                      shown_flagged_count / shown_count
                              ) * 100

        self.status_label.config(
            text=(
                f"{shown_count:,} results   |   "
                f"{shown_flagged_count:,} flagged "
                f"({flagged_percent:.2f}%)"
            )
        )

    # =====================================================
    # FILTER
    # =====================================================

    def filter_entries(self, event=None):

        text = self.search_entry.get()

        self.populate_tree(text)

    # =====================================================
    # SELECT WORD
    # =====================================================

    def on_select_word(self, event):

        selected = self.tree.selection()

        if not selected:
            return

        item = self.tree.item(selected[0])

        values = item["values"]

        word = values[1]
        self.current_word = word
        pos = values[2]
        freq = values[3]
        dispersion = values[4]
        rank = values[0]

        self.word_title.config(
            text=word
        )

        self.meta_label.config(
            text=(
                f"Rank: {rank}\n"
                f"Part of Speech: {pos}\n"
                f"Frequency: {freq}\n"
                f"Dispersion: {dispersion}"
            )
        )

        self.definition_box.delete(
            "1.0",
            tk.END
        )

        self.definition_box.insert(
            tk.END,
            "Loading definition..."
        )

        self.root.update()

        definition = fetch_definition(word)

        self.definition_box.delete(
            "1.0",
            tk.END
        )

        self.definition_box.insert(
            tk.END,
            definition
        )

        self.update_flag_button()

    # =====================================================
    # SPEAK WORD
    # =====================================================

    def speak_word(self):

        if not self.current_word:
            return

        try:

            text = self.current_word.replace('"', '')

            command = f'''
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Speak("{text}")
'''

            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    command
                ],
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        except Exception as e:

            messagebox.showerror(
                "Speech Error",
                f"Failed to vocalize word:\n{e}"
            )

# IMPORTANT: set BEFORE Tk()
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
    "corpus.dictionary.app"
)

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = DictionaryApp(root)

    root.mainloop()