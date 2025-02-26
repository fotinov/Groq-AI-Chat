# 🌟 GROQ AI Chatbot 🌟

Welcome to the **GROQ AI Chatbot**! This application allows you to interact with various AI models in a user-friendly interface. You can chat, analyze sentiments, export chat history, and even customize the chatbot's personality! 

## 📦 Features

- **Chat with AI** 🤖: Engage in conversations with different AI models.
- **Custom Prompts** ✏️: Set your own prompts to change the chatbot's personality.
- **Sentiment Analysis** 🔍: Analyze the sentiment of the last AI message.
- **Export Options** 💾: Export chat history to PDF or Markdown files.
- **Code Snippets** 📋: Highlight and manage code snippets with options to copy, edit, and set language overrides.
- **Text-to-Speech** 🔊: Listen to the last AI message using text-to-speech functionality.
- **Color Customization** 🎨: Change the background and text colors for a personalized experience.
- **Toggle Chat Save** 💾: Easily turn chat log saving on or off.
- **Save Code Snippets with Extensions** 📝: Save code snippets with the appropriate file extension based on the selected programming language.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/fotinov/Groq-AI-Chat.git
   ```

2. **Navigate to the project directory**:
   ```bash
   cd groq-ai-chatbot
   ```

3. **Obtain your API Key**:
   - Sign up or log in to your account on the [Groq website](https://groq.com).
   - Navigate to the API section of your account dashboard.
   - Generate a new API key and copy it.

4. **Set your API Key**:
   - Open the `chat/groq_ai.py` file in a text editor.
   - Locate the line where the Groq API client is initialized:
     ```python
     client = groq.Groq(api_key="YOUR_KEY_HERE")  # Replace with your actual API key
     ```
   - Replace `"YOUR_KEY_HERE"` with your actual API key.

5. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

1. **Run the application**:
   ```bash
   python chat/groq_ai.py
   ```

2. **Interact with the chatbot** through the GUI.

3. **Use the buttons** to send messages, set custom prompts, and export chat history.

## 🎨 Customization

- Change the AI model from the dropdown menu.
- Adjust the colors of the chat interface and message labels.
- Modify the font settings for AI replies.

## 📄 Exporting Chat History

You can export your chat history in different formats:
- **PDF**: Save your chat as a PDF file.
- **Markdown**: Export your chat in Markdown format for easy sharing.

## 💾 Saving Options

- **Toggle Chat Save**: You can turn chat log saving on or off using the settings menu.
- **Save Code Snippets**: When saving code snippets, you can select the programming language, and the snippet will be saved with the appropriate file extension (e.g., `.py` for Python, `.js` for JavaScript).

## 📖 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## 📞 Contact

For any inquiries, please reach out to [stanislavfotinov@gmail.com](mailto:stanislavfotinov@gmail.com).

---

Thank you for checking out the GROQ AI Chatbot! Enjoy chatting with AI! 🎉
