import re
import os
import sys
import html

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextBrowser, QLineEdit, QPushButton, QMenu,
    QLabel, QComboBox, QHBoxLayout, QColorDialog, QMessageBox, QFontDialog, QInputDialog, QTextEdit
)
from PyQt6.QtGui import QAction, QTextCursor, QColor, QFont
from PyQt6.QtCore import Qt, QUrl, QRunnable, QThreadPool, pyqtSignal, QObject

import groq
import pyttsx3
from fpdf import FPDF

from textblob import TextBlob

from pygments import highlight
from pygments.lexers import guess_lexer, PythonLexer
from pygments.formatters import HtmlFormatter

client = groq.Groq(
    api_key="YOUR_KEY_HERE")  # Replace with your actual API key


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    result = pyqtSignal(str)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self.signals.error.emit(e)
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class AIChatApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GROQ AI Chatbot")
        self.setGeometry(200, 200, 800, 600)

        self.bg_color = "#1e2419"
        self.separator_color = "#888888"

        self.user_label_color = "#007BFF"
        self.user_chat_color = "#FFFFFF"
        self.ai_label_color = "#FF0000"
        self.ai_chat_color = "#FFFFFF"

        self.ai_model = "llama3-8b-8192"
        self.model_mapping = {
            "🤖 Llama3 8B": "llama3-8b-8192",
            "🧠 Mixtral 8x7B": "mixtral-8x7b-32768",
            "🚀 Llama3 70B": "llama3-70b-8192",
            "🛡️ Llama Guard 3 8B": "llama-guard-3-8b",
            "🔐 Gemma 2 9B": "gemma2-9b-it",
            "💀 Llama 3.3 70B SpecDec": "llama-3.3-70b-specdec",
            "🕵️ Llama 3.2 11B Vision Preview": "llama-3.2-11b-vision-preview",
            "⚡ DeepSeek-R1": "deepseek-r1-distill-llama-70b"
        }

        self.save_log = False
        self.chat_history = []
        self.custom_prompt = ""
        self.prompt_set = False

        self.code_snippets = {}
        self.next_code_id = 1

        self.last_saved_index = 0
        self.tts_engine = pyttsx3.init()

        self.ai_reply_font = QFont("Arial", 12)
        self.threadpool = QThreadPool()

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        top_controls_layout = QHBoxLayout()
        self.search_button = QPushButton("🔍 Search Chat")
        self.search_button.clicked.connect(self.search_chat_history)
        top_controls_layout.addWidget(self.search_button)
        prompt_label = QLabel("Custom Prompt:")
        top_controls_layout.addWidget(prompt_label)
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter custom prompt to change chatbot personality...")
        top_controls_layout.addWidget(self.prompt_input)
        self.set_prompt_button = QPushButton("Set Prompt ✏️")
        self.set_prompt_button.clicked.connect(self.set_custom_prompt)
        top_controls_layout.addWidget(self.set_prompt_button)
        layout.addLayout(top_controls_layout)

        self.chat_display = QTextBrowser()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"background-color: {self.bg_color}; color: white; font-size: 14px;")
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here (emoji supported too) ...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        self.emoji_button = QPushButton("Emoji 😊")
        self.emoji_menu = QMenu()
        emoji_list = ["😊", "😂", "😍", "👍", "🔥", "🥳", "🤖", "😎", "🙌", "💯"]
        for emoji in emoji_list:
            action = QAction(emoji, self)
            action.triggered.connect(lambda checked, em=emoji: self.insert_emoji(em))
            self.emoji_menu.addAction(action)
        self.emoji_button.setMenu(self.emoji_menu)
        input_layout.addWidget(self.emoji_button)
        layout.addLayout(input_layout)

        buttons_layout = QHBoxLayout()
        self.send_button = QPushButton("Send 🚀")
        self.send_button.clicked.connect(self.send_message)
        buttons_layout.addWidget(self.send_button)
        self.speak_button = QPushButton("Speak AI 🔊")
        self.speak_button.clicked.connect(self.speak_last_ai_message)
        buttons_layout.addWidget(self.speak_button)
        layout.addLayout(buttons_layout)

        secondary_layout = QHBoxLayout()
        self.settings_button = QPushButton("Settings ⚙️")
        self.settings_menu = QMenu()
        self.settings_menu.setStyleSheet(
            "QMenu { background-color: #333333; color: white; border: 1px solid #222; }"
            "QMenu::item { padding: 5px 25px; }"
            "QMenu::item:selected { background-color: #555555; }"
        )
        self.settings_menu.addAction(self.create_action("💾 Toggle Save Log (ON/OFF)", self.toggle_save_log))
        self.settings_menu.addAction(self.create_action("📝 Export Chat to PDF", self.export_chat_to_pdf))
        self.settings_menu.addAction(self.create_action("📝 Export Chat to Markdown", self.export_chat_to_markdown))
        self.settings_menu.addAction(self.create_action("🔍 Analyze Last AI Sentiment", self.show_last_ai_sentiment))
        self.settings_menu.addAction(
            self.create_action("🗣️ Speech-to-Text (coming soon)", self.speech_to_text_placeholder))
        self.settings_menu.addAction(self.create_action("🧹 Clear Chat", self.clear_chat))
        self.settings_menu.addAction(self.create_action("🖋 Change AI Reply Formatting", self.change_ai_reply_font))
        self.settings_menu.addAction(self.create_action("💾 Save Snippet", self.save_snippet))
        self.settings_menu.addAction(self.create_action("📋 Export Code Snippets", self.export_code_snippets))
        self.settings_button.setMenu(self.settings_menu)
        secondary_layout.addWidget(self.settings_button)
        self.colors_button = QPushButton("Colors 🎨")
        self.colors_menu = QMenu()
        self.colors_menu.setStyleSheet(
            "QMenu { background-color: #333333; color: white; border: 1px solid #222; }"
            "QMenu::item { padding: 5px 25px; }"
            "QMenu::item:selected { background-color: #555555; }"
        )
        self.colors_menu.addAction(self.create_action("🌈 Change Background Color", lambda: self.change_color("bg")))
        self.colors_menu.addAction(self.create_action("🎨 Change User Label Color", lambda: self.change_message_color("user_label")))
        self.colors_menu.addAction(self.create_action("🎨 Change User Chat Text Color", lambda: self.change_message_color("user_chat")))
        self.colors_menu.addAction(self.create_action("🎨 Change AI Label Color", lambda: self.change_message_color("ai_label")))
        self.colors_menu.addAction(self.create_action("🎨 Change AI Chat Text Color", lambda: self.change_message_color("ai_chat")))
        self.colors_button.setMenu(self.colors_menu)
        secondary_layout.addWidget(self.colors_button)
        layout.addLayout(secondary_layout)

        self.model_selector = QComboBox()
        for display in self.model_mapping.keys():
            self.model_selector.addItem(display)
        self.model_selector.currentIndexChanged.connect(self.change_model)
        layout.addWidget(QLabel("Change AI Model:"))
        layout.addWidget(self.model_selector)

        self.setLayout(layout)
        self.update_style()

    def insert_emoji(self, emoji: str):
        current_text = self.input_field.text()
        self.input_field.setText(current_text + emoji)
        self.input_field.setFocus()

    def create_action(self, text, callback):
        action = QAction(text, self)
        action.triggered.connect(callback)
        return action

    def set_custom_prompt(self):
        prompt = self.prompt_input.text().strip()
        if prompt:
            self.custom_prompt = prompt
            self.prompt_set = False
            self.display_message("System", f"Custom prompt set: {prompt}", "#FFA500", "#FFFFFF")
            self.prompt_input.clear()

    def send_message(self):
        user_input = self.input_field.text().strip()
        if not user_input:
            return
        if user_input.lower() in ["exit", "quit"]:
            self.close()
            return

        self.display_message("You", user_input, self.user_label_color, self.user_chat_color)
        self.chat_history.append({"role": "user", "content": user_input})
        self.input_field.clear()
        self.send_button.setEnabled(False)
        worker = Worker(self.get_ai_response)
        worker.signals.result.connect(self.handle_ai_response)
        worker.signals.error.connect(self.handle_worker_error)
        worker.signals.finished.connect(lambda: self.send_button.setEnabled(True))
        self.threadpool.start(worker)

    def get_ai_response(self) -> str:
        if self.custom_prompt and not self.prompt_set:
            self.chat_history.insert(0, {"role": "system", "content": self.custom_prompt})
            self.prompt_set = True
        try:
            response = client.chat.completions.create(
                model=self.ai_model,
                messages=self.chat_history
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    def handle_ai_response(self, ai_response: str):
        self.display_message("AI Assistant", ai_response, self.ai_label_color, self.ai_chat_color)
        self.chat_history.append({"role": "assistant", "content": ai_response})
        if self.save_log:
            self.save_chat_log()

    def handle_worker_error(self, error: Exception):
        QMessageBox.critical(self, "Error", f"An error occurred: {error}")

    def format_ai_text(self, text: str) -> str:
        text = text.replace("\n", "<br>")
        formatted = re.sub(r'(?<!^)(?<!<br>)(\d{2,}\.\s)', r'<br>\1', text)
        return formatted

    def format_code_snippet(self, code_text: str, code_id: int) -> str:
        header = f"<div style='font-weight: bold; color: #FFD700;'>Snippet {code_id}</div>"
        try:
            lexer = guess_lexer(code_text)
        except Exception:
            lexer = PythonLexer()
        formatter = HtmlFormatter(nowrap=True, noclasses=True, style='monokai')
        highlighted = highlight(code_text, lexer, formatter)
        snippet_div = (
            f"<div style='background-color: black; padding: 10px; border-radius: 5px; "
            f"white-space: pre-wrap; overflow:auto;'>```{highlighted}```</div>"
        )
        return header + snippet_div

    def auto_format_code_snippets(self, text: str) -> str:
        def repl_manual(match):
            code_content = match.group(1)
            code_id = self.next_code_id
            self.next_code_id += 1
            self.code_snippets[code_id] = code_content
            return self.format_code_snippet(code_content, code_id)

        pattern = re.compile(r"```(?:[a-zA-Z]+)?\n(.*?)```", re.DOTALL)
        new_text = pattern.sub(repl_manual, text)
        if new_text == text:
            lines = text.splitlines()
            if len(lines) >= 3:
                code_indicators = ["def ", "elif ", "{", "}", ";"]
                score = sum(1 for indicator in code_indicators if indicator in text)
                if score >= 2:
                    code_id = self.next_code_id
                    self.next_code_id += 1
                    self.code_snippets[code_id] = text
                    new_text = self.format_code_snippet(text, code_id)
        return new_text

    def display_message(self, sender, message, label_color, text_color):
        separator = "<br>━━━━━━━━━━━━✦━━━━━━━━━━━━<br>"
        message = self.auto_format_code_snippets(message)
        if sender == "AI Assistant":
            message = self.format_ai_text(message)
            font_style = f"font-family: {self.ai_reply_font.family()}; font-size: {self.ai_reply_font.pointSize()}pt; "
            if self.ai_reply_font.bold():
                font_style += "font-weight: bold; "
            if self.ai_reply_font.italic():
                font_style += "font-style: italic; "
            formatted_message = f"<span style='{font_style}color:{text_color};'>{message}</span>"
        else:
            formatted_message = f"<span style='color:{text_color};'>{message}</span>"
        self.chat_display.append(f"<span style='color:{label_color};'><b>{sender}:</b></span> {formatted_message}{separator}")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def change_color(self, target):
        selected_color = QColorDialog.getColor()
        if selected_color.isValid():
            if target == "bg":
                self.bg_color = selected_color.name()
            self.update_style()

    def change_message_color(self, part):
        selected_color = QColorDialog.getColor()
        if selected_color.isValid():
            if part == "user_label":
                self.user_label_color = selected_color.name()
            elif part == "user_chat":
                self.user_chat_color = selected_color.name()
            elif part == "ai_label":
                self.ai_label_color = selected_color.name()
            elif part == "ai_chat":
                self.ai_chat_color = selected_color.name()
            self.update_style()

    def change_model(self):
        selected_display = self.model_selector.currentText()
        self.ai_model = self.model_mapping[selected_display]

    def toggle_save_log(self):
        self.save_log = not self.save_log
        state = "ON" if self.save_log else "OFF"
        QMessageBox.information(self, "Save Log", f"Chat log saving is now {state}.")

    def save_chat_log(self):
        try:
            with open("chat_log.txt", "a", encoding="utf-8") as file:
                for message in self.chat_history[self.last_saved_index:]:
                    file.write(f"{message['role'].capitalize()}: {message['content']}\n")
                file.write("-" * 50 + "\n")
            self.last_saved_index = len(self.chat_history)
        except Exception as e:
            QMessageBox.critical(self, "Save Log Error", f"Error saving log: {e}")

    def export_chat_to_pdf(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for msg in self.chat_history:
            role = msg['role'].capitalize()
            content = msg['content']
            pdf.multi_cell(0, 10, f"{role}: {content}")
            pdf.ln()
        try:
            pdf.output("chat_history.pdf")
            QMessageBox.information(self, "Export to PDF", "Chat history exported to chat_history.pdf")
        except Exception as e:
            QMessageBox.critical(self, "Export to PDF", f"Failed to export PDF: {e}")

    def export_chat_to_markdown(self):
        try:
            with open("chat_history.md", "w", encoding="utf-8") as file:
                for msg in self.chat_history:
                    role = msg['role'].capitalize()
                    content = msg['content']
                    file.write(f"**{role}:**\n\n{content}\n\n---\n\n")
            QMessageBox.information(self, "Export to Markdown", "Chat history exported to chat_history.md")
        except Exception as e:
            QMessageBox.critical(self, "Export to Markdown", f"Failed to export Markdown: {e}")

    def export_code_snippets(self):
        try:
            with open("code_snippets.txt", "w", encoding="utf-8") as file:
                for code_id, code in self.code_snippets.items():
                    file.write(f"--- Snippet {code_id} ---\n")
                    file.write(code + "\n\n")
            QMessageBox.information(self, "Export Code Snippets", "Code snippets exported to code_snippets.txt")
        except Exception as e:
            QMessageBox.critical(self, "Export Code Snippets", f"Failed to export code snippets: {e}")

    def save_snippet(self):
        """
        Allow the user to select a snippet from those saved in chat,
        then select a language from a drop-down list (which determines the file extension),
        and finally save the chosen snippet to a file.
        """
        if not self.code_snippets:
            QMessageBox.information(self, "Save Snippet", "No code snippet available to save.")
            return

        snippet_ids = sorted(self.code_snippets.keys())
        snippet_labels = [f"Snippet {i}" for i in snippet_ids]

        snippet_choice, ok = QInputDialog.getItem(self, "Save Snippet", "Select snippet to save:", snippet_labels, 0, False)
        if not ok or not snippet_choice:
            return

        chosen_id = snippet_ids[snippet_labels.index(snippet_choice)]
        code_text = self.code_snippets.get(chosen_id, "")
        if not code_text:
            QMessageBox.warning(self, "Save Snippet", "Selected snippet not found.")
            return

        languages = {
            "Python (.py)": "py",
            "JavaScript (.js)": "js",
            "C++ (.cpp)": "cpp",
            "Java (.java)": "java",
            "Text (.txt)": "txt"
        }
        lang_items = list(languages.keys())
        lang_choice, ok = QInputDialog.getItem(self, "Save Snippet", "Select language:", lang_items, 0, False)
        if not ok or not lang_choice:
            return

        ext = languages.get(lang_choice, "txt")
        file_name = f"snippet_{chosen_id}.{ext}"
        try:
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(code_text)
            QMessageBox.information(self, "Save Snippet", f"Snippet saved as {file_name}")
        except Exception as e:
            QMessageBox.critical(self, "Save Snippet", f"Failed to save snippet: {e}")

    def speech_to_text_placeholder(self):
        QMessageBox.information(self, "Speech-to-Text", "Speech-to-Text feature coming soon!")

    def speak_last_ai_message(self):
        for msg in reversed(self.chat_history):
            if msg["role"] == "assistant":
                self.tts_engine.say(msg["content"])
                self.tts_engine.runAndWait()
                return
        QMessageBox.information(self, "Text-to-Speech", "No AI message to speak.")

    def search_chat_history(self):
        keyword, ok = QInputDialog.getText(self, "Search Chat History", "Enter keyword:")
        if ok and keyword:
            results = []
            for msg in self.chat_history:
                if keyword.lower() in msg["content"].lower():
                    results.append(f"{msg['role'].capitalize()}: {msg['content']}")
            result_text = "\n\n".join(results) if results else "No matches found."
            results_window = QWidget()
            results_window.setWindowTitle("Search Results")
            layout = QVBoxLayout(results_window)
            results_text_edit = QTextEdit()
            results_text_edit.setReadOnly(True)
            results_text_edit.setText(result_text)
            layout.addWidget(results_text_edit)
            results_window.resize(400, 300)
            results_window.show()
            self.results_window = results_window

    def show_last_ai_sentiment(self):
        for msg in reversed(self.chat_history):
            if msg["role"] == "assistant":
                blob = TextBlob(msg["content"])
                polarity = blob.sentiment.polarity
                sentiment = "Positive" if polarity > 0 else "Negative" if polarity < 0 else "Neutral"
                summary = f"Sentiment: {sentiment} (Polarity: {polarity:.2f})"
                QMessageBox.information(self, "AI Message Sentiment", summary)
                return
        QMessageBox.information(self, "AI Message Sentiment", "No AI message to analyze.")

    def clear_chat(self):
        self.chat_history.clear()
        self.chat_display.clear()
        self.last_saved_index = 0

    def update_style(self):
        self.setStyleSheet(f"background-color: {self.bg_color};")
        self.chat_display.setStyleSheet(f"background-color: {self.bg_color}; color: white; font-size: 14px;")

    def change_ai_reply_font(self):
        font, ok = QFontDialog.getFont(self.ai_reply_font, self, "Choose AI Reply Font")
        if ok:
            self.ai_reply_font = font
            QMessageBox.information(self, "AI Reply Formatting", "AI reply font updated.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AIChatApp()
    window.show()
    sys.exit(app.exec())
