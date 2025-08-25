import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import docx
import pdfplumber
import zipfile
import os
import sys
import re

# --- Drag & Drop (tkdnd) ---
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    messagebox.showerror("Errore", "Installa tkinterdnd2:\n\npip install tkinterdnd2")
    sys.exit(1)

# --- Funzione per trovare risorse (compatibile con PyInstaller) ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Carica modello già allenato
model_path = resource_path("modello_finale")
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)

# --- Funzione per pulire testo Pages ---
def clean_pages_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# --- Funzione per leggere file ---
def leggi_file(path):
    if path.endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    elif path.endswith(".docx"):
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    elif path.endswith(".pdf"):
        testo = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                testo += page.extract_text() or ""
        return testo
    elif path.endswith(".pages"):
        try:
            testo = ""
            with zipfile.ZipFile(path, "r") as z:
                for name in z.namelist():
                    if name.endswith("Index.xml"):
                        with z.open(name) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            testo += clean_pages_text(content)
            return testo if testo else "⚠️ Impossibile estrarre testo da .pages"
        except Exception as e:
            raise ValueError(f"Errore lettura .pages: {str(e)}")
    else:
        raise ValueError("Formato non supportato (usa .txt, .docx, .pdf, .pages)")

# --- Funzione per classificare testo ---
def classifica_testo(testo):
    inputs = tokenizer(testo, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1).squeeze()
    return {"umano": probs[0].item(), "ai": probs[1].item()}

# --- GUI ---
def mostra_risultato(risultato):
    for widget in result_frame.winfo_children():
        widget.destroy()
    classe = "Umano" if risultato["umano"] > risultato["ai"] else "AI"
    colore = "green" if classe == "Umano" else "red"

    lbl1 = tk.Label(result_frame, text=f"Probabilità Umano: {risultato['umano']*100:.2f}%",
                    font=("Arial", 16), bg=result_frame.cget("bg"))
    lbl1.pack(pady=5)

    lbl2 = tk.Label(result_frame, text=f"Probabilità AI: {risultato['ai']*100:.2f}%",
                    font=("Arial", 16), bg=result_frame.cget("bg"))
    lbl2.pack(pady=5)

    canvas = tk.Canvas(result_frame, width=40, height=40, bg=result_frame.cget("bg"), highlightthickness=0)
    canvas.pack(pady=10)
    canvas.create_oval(5, 5, 35, 35, fill=colore)

    lbl3 = tk.Label(result_frame, text=f"Conclusione: {classe}",
                    font=("Arial", 20, "bold"), fg=colore, bg=result_frame.cget("bg"))
    lbl3.pack(pady=5)

def analizza_file(file_path):
    try:
        testo = leggi_file(file_path)
        risultato = classifica_testo(testo)
        file_status_label.config(
            text=f"✔️ Caricato: {os.path.basename(file_path)}", fg="green"
        )
        mostra_risultato(risultato)
    except Exception as e:
        file_status_label.config(
            text=f"❌ Errore caricamento: {os.path.basename(file_path)}\n{str(e)}", fg="red"
        )

def apri_file():
    file_path = filedialog.askopenfilename(filetypes=[("File di testo", "*.txt *.docx *.pdf *.pages")])
    if file_path:
        analizza_file(file_path)

def drop_file(event):
    file_path = event.data.strip("{}")
    if os.path.isfile(file_path):
        analizza_file(file_path)

# --- Costruzione GUI ---
root = TkinterDnD.Tk()
root.title("AuthentiAI - Classificatore Testo")
root.geometry("650x600")
root.tk_setPalette(background="#f0f0f0", foreground="#333333")

# Titolo
title_lbl = tk.Label(root, text="AuthentiAI", font=("Arial", 32, "bold"),
                     fg="#333333", bg="#f0f0f0", highlightbackground="#f0f0f0")
title_lbl.pack(pady=20)

lbl = tk.Label(root, text="Trascina qui un file (.txt, .docx, .pdf, .pages)\noppure seleziona manualmente",
               font=("Arial", 14), bg="#f0f0f0")
lbl.pack(pady=10)

# Bottone con ttk e stile
style = ttk.Style()
style.configure("Custom.TButton", font=("Arial", 14), foreground="white", background="#4CAF50")
btn = ttk.Button(root, text="📂 Apri file", command=apri_file, style="Custom.TButton")
btn.pack(pady=10)

file_status_label = tk.Label(root, text="Nessun file caricato", font=("Arial", 12), bg="#f0f0f0", fg="gray")
file_status_label.pack(pady=10)

result_frame = tk.Frame(root, bg="#f0f0f0")
result_frame.pack(pady=30, fill="both", expand=True)

root.drop_target_register(DND_FILES)
root.dnd_bind("<<Drop>>", drop_file)

root.mainloop()