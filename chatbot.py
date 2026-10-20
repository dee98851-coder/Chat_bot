
import json
import re
import random
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from difflib import SequenceMatcher


# =====================================================
# 1. CONFIGURATION
# =====================================================

BASE_DIR = Path("sample_faq.json").resolve().parent
JSON_FILE = BASE_DIR / "sample_faq.json"

BG = "#0B1220"
PANEL = "#131F33"
CARD = "#1B2B43"
INPUT_BG = "#22344E"
ACCENT = "#4D8DFF"
TEXT = "#F0F4FC"
MUTED = "#9DAEC8"
GREEN = "#42DDA1"
USER_BUBBLE = "#254D87"
BOT_BUBBLE = "#1B3048"


# =====================================================
# 2. LOAD JSON DATA
# =====================================================

def load_data():
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            loaded_data = json.load(file)

        if not isinstance(loaded_data, dict):
            raise ValueError("The JSON root must be an object.")

        print("Knowledge base loaded successfully.")
        return loaded_data

    except FileNotFoundError:
        messagebox.showerror(
            "Missing JSON File",
            f"File not found:\n{JSON_FILE}\n\n"
            "Keep your_file.json beside chatbot.py."
        )
        return {}

    except (json.JSONDecodeError, ValueError) as error:
        messagebox.showerror(
            "Invalid JSON Data",
            str(error)
        )
        return {}


# =====================================================
# 3. TEXT NORMALIZATION
# =====================================================

def normalize(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text)


# =====================================================
# 4. LOAD GREETINGS AND FAQS
# =====================================================

data = load_data()

GREETINGS = data.get("greetings", [])

if not isinstance(GREETINGS, list):
    GREETINGS = []

GREETINGS = [
    normalize(item)
    for item in GREETINGS
    if isinstance(item, str)
]

# Add common greeting variations.
GREETINGS.extend([
    "hello there",
    "hi there",
    "hey there",
    "good evening"
])

GREETINGS = set(GREETINGS)


def extract_faqs(obj):
    """Extract question-answer pairs from the supplied JSON structure."""
    results = []

    if isinstance(obj, dict):
        faqs = obj.get("faqs", [])

        if isinstance(faqs, list):
            for item in faqs:
                if not isinstance(item, dict):
                    continue

                question = item.get("question")
                answer = item.get("answer")

                if (
                    isinstance(question, str)
                    and isinstance(answer, str)
                    and question.strip()
                    and answer.strip()
                ):
                    results.append(
                        (question.strip(), answer.strip())
                    )

        elif isinstance(faqs, dict):
            for question, answer in faqs.items():
                if (
                    isinstance(question, str)
                    and isinstance(answer, str)
                ):
                    results.append(
                        (question.strip(), answer.strip())
                    )

    elif isinstance(obj, list):
        for item in obj:
            results.extend(extract_faqs(item))

    return results


FAQS = extract_faqs(data)

print(f"FAQs loaded: {len(FAQS)}")


# =====================================================
# 5. FAQ KEYWORDS AND ALTERNATIVE WORDING
# =====================================================

STOP_WORDS = {
    "a", "an", "the", "is", "are", "am", "do", "does",
    "did", "i", "we", "you", "your", "our", "my", "me",
    "to", "of", "for", "in", "on", "at", "and", "or",
    "can", "could", "would", "will", "please", "what",
    "when", "where", "how", "tell", "about", "much",
    "many", "get", "know", "like", "want", "need"
}

# These phrases help match common alternative questions.
ALIASES = {
    "hours": [
        "opening time",
        "closing time",
        "working hours",
        "business hours",
        "office timings",
        "when are you open",
        "what time do you operate"
    ],
    "internship project": [
        "upload project",
        "submit project",
        "project submission",
        "github submission",
        "submit github link",
        "where to submit my project"
    ],
    "certificate": [
        "certificate date",
        "certificate delivery",
        "certificate status",
        "when do i get my certificate",
        "how long for certificate",
        "certificate issue time"
    ]
}


def keyword_set(text):
    return {
        word
        for word in normalize(text).split()
        if word not in STOP_WORDS and len(word) > 1
    }


def find_faq(user_text):
    """Find the closest relevant FAQ without accepting weak matches."""
    query = normalize(user_text)

    if not query:
        return None

    # Exact matching has the highest priority.
    for question, answer in FAQS:
        if query == normalize(question):
            return answer

    # Match questions contained in the query.
    for question, answer in FAQS:
        normalized_question = normalize(question)

        if (
            len(query) >= 5
            and (
                query in normalized_question
                or normalized_question in query
            )
        ):
            return answer

    # Match known alternative wording.
    for category, phrases in ALIASES.items():
        if any(normalize(phrase) in query for phrase in phrases):
            for question, answer in FAQS:
                question_normalized = normalize(question)

                if category == "hours" and any(
                    word in question_normalized
                    for word in ["hours", "operation", "operate"]
                ):
                    return answer

                if category == "internship project" and any(
                    word in question_normalized
                    for word in ["project", "submit", "internship"]
                ):
                    return answer

                if category == "certificate" and "certificate" in question_normalized:
                    return answer

    # Compare remaining questions.
    query_words = keyword_set(query)
    best_answer = None
    best_score = 0.0

    for question, answer in FAQS:
        normalized_question = normalize(question)
        question_words = keyword_set(normalized_question)

        if not query_words or not question_words:
            continue

        intersection = len(query_words & question_words)
        union = len(query_words | question_words)

        overlap_score = intersection / union if union else 0

        similarity_score = SequenceMatcher(
            None,
            query,
            normalized_question
        ).ratio()

        # Give more weight to matching important words.
        combined_score = (
            0.65 * overlap_score
            + 0.35 * similarity_score
        )

        # Reward questions containing the query's key words.
        if query_words.issubset(question_words):
            combined_score = max(combined_score, 0.85)

        if combined_score > best_score:
            best_score = combined_score
            best_answer = answer

    # Reject unrelated questions rather than guessing.
    if best_score >= 0.45:
        return best_answer

    return None


# =====================================================
# 6. INTENT DETECTION
# =====================================================

INTENTS = {
    "greeting": [
        r"\bhello\b",
        r"\bhi\b",
        r"\bhey\b",
        r"\bgood morning\b",
        r"\bgood afternoon\b",
        r"\bgood evening\b"
    ],

    "thanks": [
        r"\bthank you\b",
        r"\bthanks\b",
        r"\bthx\b"
    ],

    "business_hours": [
        r"\bhours of operation\b",
        r"\bbusiness hours\b",
        r"\bopening hours\b",
        r"\bworking hours\b",
        r"\bwhen do you open\b",
        r"\bwhen do you close\b",
        r"\bare you open\b",
        r"\bwhat time.*open\b",
        r"\bwhat time.*close\b"
    ],

    "contact": [
        r"\bcontact details\b",
        r"\bcontact information\b",
        r"\bphone number\b",
        r"\bemail address\b",
        r"\bcustomer support\b",
        r"\bspeak to.*human\b",
        r"\btalk to.*agent\b"
    ],

    "goodbye": [
        r"\bbye\b",
        r"\bgoodbye\b",
        r"\bsee you\b",
        r"\bquit\b",
        r"\bexit\b"
    ]
}


def identify_intent(user_text):
    query = normalize(user_text)

    if query in GREETINGS:
        return "greeting"

    # Avoid matching "hi" inside words such as "this".
    for pattern in INTENTS["greeting"]:
        if re.search(pattern, query):
            return "greeting"

    for intent in ["thanks", "goodbye", "contact"]:
        for pattern in INTENTS[intent]:
            if re.search(pattern, query):
                return intent

    # Match the FAQ before assigning a business-hours intent.
    if find_faq(user_text):
        return "faq"

    for pattern in INTENTS["business_hours"]:
        if re.search(pattern, query):
            return "business_hours"

    if re.search(
        r"\b(hours|opening|closing|operate|operating)\b",
        query
    ):
        return "business_hours"

    return None


# =====================================================
# 7. RESPONSE GENERATION
# =====================================================

def get_response(user_text):
    query = normalize(user_text)

    if query in {"bye", "exit", "quit"}:
        return "Goodbye! Thank you for contacting us.", True

    intent = identify_intent(user_text)

    if intent == "greeting":
        return random.choice([
            "Hello! Welcome to Customer Support. How can I help?",
            "Hi there! What would you like to know?",
            "Welcome! Please ask your question."
        ]), False

    if intent == "thanks":
        return "You're welcome! How else can I help?", False

    if intent == "goodbye":
        return "Goodbye! Thank you for chatting with us.", True

    if intent == "contact":
        contact = data.get("contact_details")

        if contact:
            return str(contact), False

        return (
            "Contact details are not available in the current FAQ dataset.",
            False
        )

    # Always search the FAQs for an actual stored answer.
    answer = find_faq(user_text)

    if answer:
        return answer, False

    if intent == "business_hours":
        return (
            "I couldn't find the business hours in the FAQ dataset. "
            "Please check the knowledge base.",
            False
        )

    return (
        "I couldn't find a matching answer in the knowledge base.\n\n"
        "Try asking about:\n"
        "• Hours of operation\n"
        "• Internship project submission\n"
        "• Certificate delivery",
        False
    )


# =====================================================
# 8. TKINTER CHATBOT GUI
# =====================================================

class CustomerSupportBot:

    def __init__(self, root):
        self.root = root
        self.root.title("Customer Support Assistant")
        self.root.geometry("900x720")
        self.root.minsize(620, 500)
        self.root.configure(bg=BG)

        self.chat_closed = False

        self.setup_styles()
        self.create_header()
        self.create_chat_area()
        self.create_quick_questions()
        self.create_input_area()

        self.add_message(
            "bot",
            "Hello! Welcome to Customer Support.\n"
            "Ask me about internship projects, certificates, "
            "or business hours."
        )

        self.entry.focus_set()

    # ---------------- STYLES ----------------

    def setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            "Vertical.TScrollbar",
            background=CARD,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=TEXT
        )

    # ---------------- HEADER ----------------

    def create_header(self):
        header = tk.Frame(
            self.root,
            bg=PANEL,
            padx=22,
            pady=16
        )
        header.pack(fill="x")

        tk.Label(
            header,
            text="✦",
            font=("Segoe UI", 27, "bold"),
            bg=PANEL,
            fg=ACCENT
        ).pack(side="left", padx=(0, 12))

        title_frame = tk.Frame(header, bg=PANEL)
        title_frame.pack(side="left", fill="x")

        tk.Label(
            title_frame,
            text="Customer Support",
            font=("Segoe UI", 18, "bold"),
            bg=PANEL,
            fg=TEXT
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="FAQ Assistant",
            font=("Segoe UI", 10),
            bg=PANEL,
            fg=MUTED
        ).pack(anchor="w", pady=(3, 0))

        tk.Label(
            header,
            text="● Online",
            font=("Segoe UI", 10, "bold"),
            bg=PANEL,
            fg=GREEN
        ).pack(side="right")

        tk.Frame(
            self.root,
            bg=ACCENT,
            height=2
        ).pack(fill="x")

    # ---------------- CHAT AREA ----------------

    def create_chat_area(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=12
        )

        self.canvas = tk.Canvas(
            outer,
            bg=BG,
            highlightthickness=0,
            borderwidth=0
        )

        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=self.canvas.yview,
            style="Vertical.TScrollbar"
        )

        self.chat_frame = tk.Frame(self.canvas, bg=BG)

        self.chat_window = self.canvas.create_window(
            (0, 0),
            window=self.chat_frame,
            anchor="nw"
        )

        self.chat_frame.bind(
            "<Configure>",
            self.update_scroll_region
        )

        self.canvas.bind(
            "<Configure>",
            self.resize_chat_frame
        )

        self.canvas.configure(
            yscrollcommand=scrollbar.set
        )

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

    def update_scroll_region(self, event=None):
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )
        self.canvas.after_idle(
            lambda: self.canvas.yview_moveto(1.0)
        )

    def resize_chat_frame(self, event):
        self.canvas.itemconfigure(
            self.chat_window,
            width=event.width
        )

    # ---------------- MESSAGE BUBBLES ----------------

    def add_message(self, sender, message):
        is_user = sender == "user"

        row = tk.Frame(self.chat_frame, bg=BG)
        row.pack(fill="x", padx=8, pady=7)

        bubble_color = USER_BUBBLE if is_user else BOT_BUBBLE
        sender_name = "You" if is_user else "Support Assistant"

        bubble = tk.Frame(
            row,
            bg=bubble_color,
            padx=14,
            pady=10
        )

        # Tkinter anchor values must be n, e, s, w, etc.
        bubble.pack(anchor="e" if is_user else "w")

        tk.Label(
            bubble,
            text=sender_name,
            font=("Segoe UI", 9, "bold"),
            bg=bubble_color,
            fg="#9BC0FF" if is_user else GREEN
        ).pack(anchor="w")

        tk.Label(
            bubble,
            text=message,
            font=("Segoe UI", 10),
            bg=bubble_color,
            fg=TEXT,
            justify="left",
            anchor="w",
            wraplength=max(
                250,
                min(560, self.root.winfo_width() - 160)
            )
        ).pack(anchor="w", pady=(5, 0))

        self.root.update_idletasks()
        self.canvas.yview_moveto(1.0)

    # ---------------- QUICK QUESTIONS ----------------

    def create_quick_questions(self):
        section = tk.Frame(
            self.root,
            bg=BG,
            padx=20,
            pady=5
        )
        section.pack(fill="x")

        tk.Label(
            section,
            text="QUICK QUESTIONS",
            font=("Segoe UI", 9, "bold"),
            bg=BG,
            fg=MUTED
        ).pack(anchor="w", pady=(0, 8))

        buttons_frame = tk.Frame(section, bg=BG)
        buttons_frame.pack(anchor="w")

        questions = [
            "What are your hours of operation?",
            "How do I submit my internship project?",
            "When will I receive my certificate?"
        ]

        for question in questions:
            tk.Button(
                buttons_frame,
                text=(
                    "Business Hours"
                    if "hours" in question
                    else "Project Submission"
                    if "project" in question
                    else "Certificate"
                ),
                command=lambda q=question: self.send_message(q),
                font=("Segoe UI", 9),
                bg=INPUT_BG,
                fg=TEXT,
                activebackground=ACCENT,
                activeforeground="white",
                relief="flat",
                bd=0,
                padx=12,
                pady=7,
                cursor="hand2"
            ).pack(side="left", padx=(0, 7), pady=(0, 8))

    # ---------------- INPUT AREA ----------------

    def create_input_area(self):
        footer = tk.Frame(
            self.root,
            bg=PANEL,
            padx=16,
            pady=14
        )
        footer.pack(side="bottom", fill="x")

        input_row = tk.Frame(footer, bg=PANEL)
        input_row.pack(fill="x")

        self.entry = tk.Entry(
            input_row,
            font=("Segoe UI", 11),
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0
        )
        self.entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=13,
            padx=(0, 10)
        )

        self.entry.bind("<Return>", self.handle_enter)

        self.send_button = tk.Button(
            input_row,
            text="Send  ➤",
            command=self.send_from_entry,
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT,
            fg="white",
            activebackground="#3675E8",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2"
        )
        self.send_button.pack(side="right")

        bottom_row = tk.Frame(footer, bg=PANEL)
        bottom_row.pack(fill="x", pady=(10, 0))

        tk.Label(
            bottom_row,
            text="Press Enter to send",
            font=("Segoe UI", 9),
            bg=PANEL,
            fg=MUTED
        ).pack(side="left")

        tk.Button(
            bottom_row,
            text="Clear Chat",
            command=self.clear_chat,
            font=("Segoe UI", 9),
            bg=PANEL,
            fg=MUTED,
            activebackground=PANEL,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            cursor="hand2"
        ).pack(side="right")

    # ---------------- SEND MESSAGE ----------------

    def handle_enter(self, event):
        self.send_from_entry()
        return "break"

    def send_from_entry(self):
        if self.chat_closed:
            return

        message = self.entry.get().strip()

        if message:
            self.send_message(message)

    def send_message(self, message):
        if self.chat_closed:
            return

        message = message.strip()

        if not message:
            return

        self.add_message("user", message)
        self.entry.delete(0, "end")

        response, should_exit = get_response(message)
        self.add_message("bot", response)

        if should_exit:
            self.chat_closed = True
            self.entry.config(state="disabled")
            self.send_button.config(state="disabled")

    # ---------------- CLEAR CHAT ----------------

    def clear_chat(self):
        self.chat_closed = False

        self.entry.config(state="normal")
        self.send_button.config(state="normal")

        for widget in self.chat_frame.winfo_children():
            widget.destroy()

        self.add_message(
            "bot",
            "Chat cleared. How can I help you today?"
        )

        self.entry.focus_set()


# =====================================================
# 9. START APPLICATION
# =====================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = CustomerSupportBot(root)
    root.mainloop()
