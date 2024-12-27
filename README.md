# Personal Financial Assistant Chatbot 💰

A modern web-based chatbot that provides personalized financial advice using AI. Built with Flask, Cohere AI, and MongoDB.

## 🌟 Features

- 💬 Interactive chat interface
- 💰 Personalized financial advice
- 📊 Budget planning assistance
- 💎 Investment guidance
- 📈 Compound interest explanations
- 💾 Persistent chat history
- 🎯 Quick suggestion chips

## 🛠️ Prerequisites

Before running this project, make sure you have:

1. Python 3.8 or higher installed
2. MongoDB installed and running locally
3. A Cohere API key (get one at [cohere.ai](https://cohere.ai))

## ⚙️ Installation

1. Clone the repository:
```bash
git clone https://github.com/ranga-godhandaraman/Financial-Assistance-Chatbot.git
cd personal-financial-assistant
```

2. Create and activate a virtual environment (recommended):
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your Cohere API key:
```env
COHERE_API_KEY=your_api_key_here
```

## 🚀 Running the Application

1. Make sure MongoDB is running on your system:
```bash
# Windows (if MongoDB is installed as a service)
net start MongoDB

# Linux/MacOS
sudo systemctl start mongod
```

2. Start the Flask application:
```bash
python fa-backend.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## 💡 Usage

1. Start a new chat session by clicking the "New Chat" button
2. Type your financial question in the input box or use one of the suggestion chips
3. Get AI-powered responses about:
   - Creating monthly budgets
   - Saving strategies
   - Investment basics
   - Compound interest calculations
   - And more!

## 🔧 Project Structure

```
personal-financial-assistant/
├── fa-backend.py          # Main Flask application
├── templates/
│   └── index.html        # Frontend template
├── static/
│   └── styles/           # CSS files (if any)
├── requirements.txt      # Python dependencies
├── .env                 # Environment variables
└── README.md           # This file
```

## 📦 Dependencies

- Flask: Web framework
- Cohere: AI model for generating responses
- PyMongo: MongoDB driver for Python
- python-dotenv: Environment variable management
- Other dependencies listed in requirements.txt

## 🤝 Contributing

Feel free to:
1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Important Notes

- Keep your Cohere API key secure and never commit it to version control
- The chatbot's responses are AI-generated and should not be considered as professional financial advice
- Always verify financial information from reliable sources
