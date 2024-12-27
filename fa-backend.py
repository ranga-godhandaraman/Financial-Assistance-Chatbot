from flask import Flask, request, jsonify, render_template, url_for
from flask_cors import CORS
import cohere
from datetime import datetime
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Cohere client
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(COHERE_API_KEY, timeout=120)  # 2 minutes timeout

def get_financial_response(user_input):
    try:
        financial_prompt = """You are a specialized Personal Financial Assistant. Provide detailed, practical financial advice and guidance.

Example Question: What are the key aspects of personal budgeting?
Example Response:
Creating and maintaining a personal budget is essential for financial success. Here's a comprehensive guide:

1. Track Your Income: First, calculate your total monthly income from all sources including salary, investments, and any side hustles.

2. List Fixed Expenses: Document all your regular monthly expenses like rent/mortgage, utilities, insurance, and loan payments.

3. Track Variable Expenses: Monitor fluctuating costs such as groceries, entertainment, dining out, and shopping.

4. Set Savings Goals: Allocate a portion of your income for emergency funds, retirement, and other financial goals.

5. Use the 50/30/20 Rule: Consider allocating 50% for needs, 30% for wants, and 20% for savings and debt repayment.

Remember to review and adjust your budget regularly to ensure it remains effective and aligned with your financial goals.

Now, please provide a detailed response to this financial question, following the same format with numbered points and clear explanations:
{question}"""

        response = co.generate(
            model='command',
            prompt=financial_prompt.format(question=user_input),
            max_tokens=2000,
            temperature=0.7,
            k=0,
            return_likelihoods='NONE'
        )
        
        result = response.generations[0].text.strip()
        
        # Format the response to ensure proper spacing
        lines = result.split('\n')
        formatted_lines = []
        in_list = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # If it's a numbered point, add extra spacing
            if line[0].isdigit() and '. ' in line:
                if not in_list:
                    formatted_lines.append('')  # Add space before first point
                    in_list = True
                formatted_lines.append(line)
                formatted_lines.append('')  # Add space after each point
            else:
                if in_list:
                    in_list = False
                formatted_lines.append(line)
        
        # Join with newlines and clean up extra spacing
        formatted_result = '\n'.join(formatted_lines)
        formatted_result = '\n'.join(line for line in formatted_result.split('\n') if line.strip())
        
        return formatted_result
        
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return "I apologize, but I'm having trouble connecting to the AI service. Please try again in a moment."

def save_chat_message(chat_id, role, content):
    message = {
        'chat_id': chat_id,
        'role': role,
        'content': content,
        'timestamp': datetime.utcnow()
    }
    
    try:
        # MongoDB connection string
        mongo_uri = "mongodb://localhost:27017/"
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Select database and collection
        db = client['financial_assistant']
        messages_collection = db['messages']
        
        # Insert the message
        messages_collection.insert_one(message)
        
        # Update chat session
        sessions_collection = db['chat_sessions']
        session = sessions_collection.find_one({'_id': chat_id})
        
        if session:
            # Update existing session
            sessions_collection.update_one(
                {'_id': chat_id},
                {
                    '$inc': {'message_count': 1},
                    '$set': {'timestamp': datetime.utcnow()}
                }
            )
        else:
            # Create new session
            sessions_collection.insert_one({
                '_id': chat_id,
                'message_count': 1,
                'timestamp': datetime.utcnow(),
                'first_message': content if role == 'user' else None
            })
            
        client.close()
        return True
        
    except ServerSelectionTimeoutError:
        print("Could not connect to MongoDB")
        return False
    except Exception as e:
        print(f"Error saving message: {str(e)}")
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_input = data.get("message")
        chat_id = data.get("chatId")
        
        if not user_input:
            return jsonify({"error": "No message provided"}), 400

        if not chat_id:
            chat_id = str(uuid.uuid4())

        # Save user message
        save_chat_message(chat_id, 'user', user_input)
        
        # Get AI response
        ai_response = get_financial_response(user_input)
        
        # Save AI response
        save_chat_message(chat_id, 'assistant', ai_response)
        
        return jsonify({
            "response": ai_response,
            "chatId": chat_id
        })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"response": "I apologize, but I encountered an error. Please try again or rephrase your question."})

@app.route("/chat-history/<chat_id>", methods=["GET"])
def get_chat(chat_id):
    try:
        # MongoDB connection
        mongo_uri = "mongodb://localhost:27017/"
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client['financial_assistant']
        messages_collection = db['messages']
        
        # Get messages for the chat
        messages = list(messages_collection.find(
            {'chat_id': chat_id},
            {'_id': 0, 'role': 1, 'content': 1, 'timestamp': 1}
        ).sort('timestamp', 1))
        
        client.close()
        
        return jsonify({"history": messages})
        
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        return jsonify({"error": "Failed to get chat history"}), 500

@app.route("/chat-sessions", methods=["GET"])
def get_chat_sessions():
    try:
        # MongoDB connection
        mongo_uri = "mongodb://localhost:27017/"
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client['financial_assistant']
        sessions_collection = db['chat_sessions']
        
        # Get all chat sessions
        sessions = list(sessions_collection.find(
            {},
            {'_id': 1, 'message_count': 1, 'timestamp': 1, 'first_message': 1}
        ).sort('timestamp', -1))
        
        client.close()
        
        return jsonify({"sessions": sessions})
        
    except Exception as e:
        print(f"Error getting chat sessions: {str(e)}")
        return jsonify({"error": "Failed to get chat sessions"}), 500

@app.route("/chat-session/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    try:
        # MongoDB connection
        mongo_uri = "mongodb://localhost:27017/"
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client['financial_assistant']
        
        # Delete messages and session
        messages_collection = db['messages']
        sessions_collection = db['chat_sessions']
        
        messages_collection.delete_many({'chat_id': chat_id})
        sessions_collection.delete_one({'_id': chat_id})
        
        client.close()
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error deleting chat: {str(e)}")
        return jsonify({"error": "Failed to delete chat"}), 500

if __name__ == '__main__':
    app.run(debug=True)
