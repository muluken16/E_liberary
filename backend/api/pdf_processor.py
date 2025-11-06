import os
import re
import json
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict
import pdfplumber
import pytesseract
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# -----------------------
# Configuration / Globals
# -----------------------
STOP = set(stopwords.words("english"))
DEFAULT_OUTPUT_DIR = "student_ai_output"

# -----------------------
# Text extraction & helpers
# -----------------------
def extract_text(pdf_path: str) -> str:
    """Extract text from PDF, with OCR fallback for scanned pages."""
    text = ""
    with pdfplumber.open(pdf_path) as doc:
        for p in doc.pages:
            t = p.extract_text()
            if not t or not t.strip():
                # OCR fallback
                pil_img = p.to_image(resolution=200).original
                t = pytesseract.image_to_string(pil_img)
            text += " " + (t or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def make_summary(text: str, lines: int = 3) -> str:
    sents = sent_tokenize(text)
    return " ".join(sents[:lines]) if sents else ""

def make_concepts(text: str, max_terms: int = 10) -> List[str]:
    words = [w.lower() for w in word_tokenize(text) if w.isalpha() and w.lower() not in STOP]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    sorted_terms = sorted(freq, key=freq.get, reverse=True)
    return sorted_terms[:max_terms]

def make_quiz(text: str, n: int = 8, difficulty: str = "medium") -> List[Dict[str,str]]:
    sents = [s for s in sent_tokenize(text) if 6 < len(s.split()) < 35]
    random.shuffle(sents)
    quiz = []
    length_cut = {"easy": 4, "medium": 6, "hard": 8}.get(difficulty, 6)
    for s in sents:
        words = [w for w in word_tokenize(s) if w.isalpha() and w.lower() not in STOP]
        candidates = [w for w in words if len(w) >= length_cut]
        if not candidates:
            continue
        answer = random.choice(candidates)
        q_text = re.sub(rf"\b{re.escape(answer)}\b", "_____", s, flags=re.I)
        quiz.append({"Q": q_text, "A": answer})
        if len(quiz) >= n:
            break
    return quiz

def make_flashcards(concepts: List[str]) -> List[Dict[str,str]]:
    cards = []
    for term in concepts:
        definition = f"Define '{term}' in simple words."  # Placeholder — could be replaced by real definitions if integrated with a QA model
        cards.append({"front": term, "back": definition})
    return cards

# -----------------------
# PDF builder
# -----------------------
def build_pdf(summary: str, quiz: List[Dict[str,str]], concepts: List[str],
              out_pdf: str, logo_path: str = None, color_mode: str = "plain", teacher_mode: bool = False):
    doc = SimpleDocTemplate(out_pdf, pagesize=letter,
                            rightMargin=50, leftMargin=50, topMargin=60, bottomMargin=50)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCenter", parent=styles["Title"], alignment=TA_CENTER)
    elements = []

    # Optional logo
    if logo_path and os.path.exists(logo_path):
        try:
            elements.append(RLImage(logo_path, width=2*inch, height=2*inch))
            elements.append(Spacer(1, 0.15*inch))
        except Exception:
            pass

    elements.append(Paragraph("📘 AI Student Study Worksheet", title_style))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph("<b>Name:</b> ________________________________   <b>Date:</b> ____________", styles["BodyText"]))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("<b>Lesson Summary</b>", styles["Heading2"]))
    elements.append(Paragraph(summary or "Summary could not be generated.", styles["BodyText"]))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("<b>Key Concepts</b>", styles["Heading2"]))
    elements.append(Paragraph(", ".join(concepts) if concepts else "—", styles["BodyText"]))
    elements.append(PageBreak())

    # Quiz page
    elements.append(Paragraph("🎯 Practice Quiz", title_style))
    elements.append(Spacer(1, 0.1*inch))
    for i, q in enumerate(quiz, 1):
        elements.append(Paragraph(f"{i}. {q['Q']}", styles["BodyText"]))
        elements.append(Spacer(1, 0.05*inch))
        elements.append(Paragraph("Answer: _________________________________", styles["BodyText"]))
        elements.append(Spacer(1, 0.12*inch))
    elements.append(PageBreak())

    # Answer key (teacher mode)
    if teacher_mode:
        elements.append(Paragraph("👩‍🏫 Teacher Answer Key", title_style))
        elements.append(Spacer(1, 0.1*inch))
        for i, q in enumerate(quiz, 1):
            elements.append(Paragraph(f"{i}. {q['A']}", styles["BodyText"]))

    doc.build(elements)

# -----------------------
# GUI application
# -----------------------
class AIStudentAssistantGUI:
    def __init__(self, root):
        self.root = root
        root.title("AI Student Assistant")
        root.geometry("720x520")
        self.pdf_path = ""
        self.logo_path = ""
        self.output_dir = DEFAULT_OUTPUT_DIR

        # Top frame: file selection
        frm_top = ttk.Frame(root, padding=10)
        frm_top.pack(fill="x")

        ttk.Label(frm_top, text="Lesson PDF:").pack(side="left")
        self.entry_pdf = ttk.Entry(frm_top, width=55)
        self.entry_pdf.pack(side="left", padx=8)
        ttk.Button(frm_top, text="Browse", command=self.browse_pdf).pack(side="left")

        ttk.Button(frm_top, text="Choose Logo (optional)", command=self.browse_logo).pack(side="left", padx=6)

        # Options frame
        frm_opts = ttk.Frame(root, padding=(10,5))
        frm_opts.pack(fill="x")

        ttk.Label(frm_opts, text="Difficulty:").grid(row=0, column=0, sticky="w")
        self.diff_var = tk.StringVar(value="medium")
        diff_combo = ttk.Combobox(frm_opts, values=["easy", "medium", "hard"], textvariable=self.diff_var, width=8, state="readonly")
        diff_combo.grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(frm_opts, text="Color Mode:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.color_var = tk.StringVar(value="plain")
        color_combo = ttk.Combobox(frm_opts, values=["plain", "fun"], textvariable=self.color_var, width=8, state="readonly")
        color_combo.grid(row=0, column=3, sticky="w", padx=6)

        self.teacher_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm_opts, text="Teacher Mode (Show answers)", variable=self.teacher_var).grid(row=0, column=4, padx=10)

        # Buttons frame
        frm_buttons = ttk.Frame(root, padding=10)
        frm_buttons.pack(fill="x")
        ttk.Button(frm_buttons, text="Show Summary", command=self.show_summary).pack(side="left", padx=6)
        ttk.Button(frm_buttons, text="Generate Quiz (popup)", command=self.show_quiz).pack(side="left", padx=6)
        ttk.Button(frm_buttons, text="Generate Flashcards (JSON)", command=self.generate_flashcards).pack(side="left", padx=6)
        ttk.Button(frm_buttons, text="Generate Worksheet (PDF+JSON+TXT)", command=self.generate_worksheet).pack(side="left", padx=6)

        ttk.Button(frm_buttons, text="Choose Output Folder", command=self.choose_output_folder).pack(side="right")
        self.lbl_out = ttk.Label(root, text=f"Output folder: {self.output_dir}")
        self.lbl_out.pack(fill="x", padx=10)

        # Text area for results
        frm_text = ttk.Frame(root)
        frm_text.pack(fill="both", expand=True, padx=10, pady=6)
        self.txt = tk.Text(frm_text, wrap="word")
        self.txt.pack(fill="both", expand=True)
        self.set_help_text()

    # ---------- GUI utilities ----------
    def set_help_text(self):
        help_text = (
            "Welcome to AI Student Assistant!\n\n"
            "1. Click Browse to select a lesson PDF.\n"
            "2. Choose difficulty (easy/medium/hard) and options.\n"
            "3. Use 'Show Summary' to see a short 2-3 sentence summary.\n"
            "4. Generate Quiz to view fill-in-the-blank questions.\n"
            "5. Generate Worksheet will create a printable PDF, JSON and TXT in the output folder.\n\n"
            "Works with scanned PDFs (if Tesseract is installed).\n"
        )
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", help_text)

    def browse_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files","*.pdf")])
        if path:
            self.pdf_path = path
            self.entry_pdf.delete(0, "end")
            self.entry_pdf.insert(0, path)
            self.txt.insert("end", f"\nSelected PDF: {path}\n")
            self.txt.see("end")

    def browse_logo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif")])
        if path:
            self.logo_path = path
            self.txt.insert("end", f"\nSelected Logo: {path}\n")
            self.txt.see("end")

    def choose_output_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir = path
            self.lbl_out.config(text=f"Output folder: {self.output_dir}")
            self.txt.insert("end", f"\nOutput folder set: {path}\n")
            self.txt.see("end")

    # ---------- Functional buttons ----------
    def require_pdf(self) -> bool:
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            messagebox.showwarning("No PDF", "Please choose a valid PDF file first.")
            return False
        return True

    def show_summary(self):
        if not self.require_pdf():
            return
        self.txt.insert("end", "\n⏳ Extracting text and generating summary...\n"); self.txt.see("end")
        try:
            text = extract_text(self.pdf_path)
            summary = make_summary(text, lines=3)
            self.txt.insert("end", f"\n--- Summary ---\n{summary}\n")
            self.txt.see("end")
            messagebox.showinfo("Summary", summary or "No summary could be created.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract summary: {e}")

    def show_quiz(self):
        if not self.require_pdf():
            return
        self.txt.insert("end", "\n⏳ Generating quiz...\n"); self.txt.see("end")
        try:
            text = extract_text(self.pdf_path)
            quiz = make_quiz(text, n=8, difficulty=self.diff_var.get())
            if not quiz:
                messagebox.showinfo("Quiz", "No quiz questions could be generated.")
                return
            # Show in a small popup
            popup = tk.Toplevel(self.root)
            popup.title("Generated Quiz")
            popup.geometry("600x400")
            txt = tk.Text(popup, wrap="word")
            txt.pack(fill="both", expand=True)
            for i, q in enumerate(quiz, 1):
                txt.insert("end", f"{i}. {q['Q']}\n\n")
            txt.insert("end", "\n(Answers hidden - enable Teacher Mode to include answers in worksheet.)")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate quiz: {e}")

    def generate_flashcards(self):
        if not self.require_pdf():
            return
        self.txt.insert("end", "\n⏳ Generating flashcards...\n"); self.txt.see("end")
        try:
            text = extract_text(self.pdf_path)
            concepts = make_concepts(text, max_terms=12)
            cards = make_flashcards(concepts)
            out_dir = self.output_dir
            os.makedirs(out_dir, exist_ok=True)
            file_path = os.path.join(out_dir, "flashcards.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(cards, f, indent=2, ensure_ascii=False)
            self.txt.insert("end", f"Flashcards saved: {file_path}\n")
            messagebox.showinfo("Flashcards", f"Saved {len(cards)} flashcards to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create flashcards: {e}")

    def generate_worksheet(self):
        if not self.require_pdf():
            return
        try:
            self.txt.insert("end", "\n⏳ Processing PDF and generating worksheet files...\n"); self.txt.see("end")
            text = extract_text(self.pdf_path)
            summary = make_summary(text, lines=3)
            concepts = make_concepts(text, max_terms=12)
            quiz = make_quiz(text, n=10, difficulty=self.diff_var.get())
            cards = make_flashcards(concepts)

            # prepare output folder
            out_dir = self.output_dir
            os.makedirs(out_dir, exist_ok=True)

            # PDF
            pdf_out = os.path.join(out_dir, "AI_Student_Worksheet.pdf")
            build_pdf(summary, quiz, concepts, pdf_out, logo_path=self.logo_path,
                      color_mode=self.color_var.get(), teacher_mode=self.teacher_var.get())

            # JSON
            json_out = os.path.join(out_dir, "AI_Student_Worksheet.json")
            with open(json_out, "w", encoding="utf-8") as jf:
                json.dump({"summary": summary, "concepts": concepts, "quiz": quiz, "flashcards": cards},
                          jf, indent=2, ensure_ascii=False)

            # TXT (printable quick)
            txt_out = os.path.join(out_dir, "AI_Student_Worksheet.txt")
            with open(txt_out, "w", encoding="utf-8") as tf:
                tf.write("AI Student Worksheet\n\n")
                tf.write("Summary:\n" + (summary or "—") + "\n\n")
                tf.write("Key Concepts:\n" + (", ".join(concepts) or "—") + "\n\n")
                tf.write("Quiz:\n")
                for i, q in enumerate(quiz, 1):
                    tf.write(f"{i}. {q['Q']}\n")
                if self.teacher_var.get():
                    tf.write("\nAnswer Key:\n")
                    for i, q in enumerate(quiz, 1):
                        tf.write(f"{i}. {q['A']}\n")

            self.txt.insert("end", f"Worksheet PDF: {pdf_out}\nJSON: {json_out}\nTXT: {txt_out}\n")
            self.txt.see("end")
            messagebox.showinfo("Done", f"Worksheet files saved in:\n{out_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate worksheet: {e}")

# -----------------------
# Run app
# -----------------------
def main():
    root = tk.Tk()
    app = AIStudentAssistantGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
