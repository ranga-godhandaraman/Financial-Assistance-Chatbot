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

def classify_question(text):
    """Determine if the question is about finance using semantic analysis."""
    try:
        # Use Cohere's embed to get semantic understanding
        response = co.chat(
            message=f"Is this a question about personal finance, investing, banking, taxes, budgeting, or economics? Question: {text}",
            preamble="""You are a classifier that ONLY answers 'Yes' or 'No'.
            Answer 'Yes' ONLY if the question is directly related to:
            - Personal finance
            - Money management
            - Investing
            - Banking
            - Economics
            - Budgeting
            - Taxes
            - Insurance
            - Financial planning
            - Business finance
            
            Answer 'No' for everything else, even if it might indirectly relate to finance.
            
            DO NOT provide any explanation. ONLY answer with a single word: 'Yes' or 'No'.""",
            temperature=0,
            max_tokens=1
        )
        
        answer = response.text.strip().lower()
        return answer == 'yes'
        
    except Exception as e:
        print(f"Classification error: {e}")
        return False

def get_chat_history(chat_id, limit=20):
    """Get the recent chat history for context."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['financial_assistant']
        messages = list(db.messages.find(
            {'chat_id': chat_id},
            {'_id': 0, 'role': 1, 'content': 1}
        ).sort('timestamp', -1).limit(limit))
        
        # Reverse to get chronological order
        messages.reverse()
        return messages
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return []

def format_chat_history(messages):
    """Format chat history for the prompt."""
    if not messages:
        return ""
    
    history = "\nPrevious conversation context:\n"
    for msg in messages:
        role = "User" if msg['role'] == 'user' else "Assistant"
        history += f"{role}: {msg['content']}\n"
    return history

def get_financial_response(user_input, chat_id):
    try:
        # First check if it's a financial question
        if not classify_question(user_input):
            return """I am a specialized Financial Assistant and can only help with questions about:

• Personal Finance and Budgeting
• Investing and Stock Markets
• Saving Strategies
• Debt Management
• Financial Planning
• Banking and Interest Rates
• Insurance Basics
• Tax Concepts
• Retirement Planning

Please ask me a question related to these financial topics, and I'll be happy to help!"""

        # Get recent chat history for context
        chat_history = get_chat_history(chat_id)
        history_context = format_chat_history(chat_history)

        # For financial questions, use a strictly controlled prompt with context
        financial_prompt = f"""You are a Personal Financial Assistant. Follow these rules STRICTLY:

1. ONLY provide factual financial information and advice
2. NEVER make up or reference specific people, experts, or authors
3. NEVER create fictional examples or case studies
4. If asked about specific people, companies, or historical events, say "I can help with general financial concepts, but I don't provide information about specific people or companies"
5. Focus ONLY on verified financial concepts and principles
6. Use clear numbered points in responses
7. Include basic calculations when relevant
8. Always add a disclaimer for investment-related advice
9. MAINTAIN CONTEXT from the previous conversation
10. Use the same units and currency as mentioned in the conversation

{history_context}

Current question: {user_input}

Please provide a clear, factual response that maintains context from the previous messages:"""

        # Get response from Cohere
        response = co.generate(
            model='command',
            prompt=financial_prompt,
            max_tokens=2000,
            temperature=0.7,
            k=0,
            return_likelihoods='NONE'
        )

        return response.generations[0].text.strip()

    except Exception as e:
        print(f"Error in get_financial_response: {e}")
        return "I apologize, but I encountered an error. Please try asking your question again."

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

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_input = data.get('message', '').strip()
        chat_id = data.get('chatId')
        
        if not user_input:
            return jsonify({'error': 'Empty message'}), 400
        
        if not chat_id:
            chat_id = str(uuid.uuid4())
        
        # Save user message
        if not save_chat_message(chat_id, 'user', user_input):
            return jsonify({'error': 'Failed to save message'}), 500
        
        # Get AI response with chat context
        ai_response = get_financial_response(user_input, chat_id)
        
        # Save AI response
        if not save_chat_message(chat_id, 'assistant', ai_response):
            return jsonify({'error': 'Failed to save response'}), 500
        
        return jsonify({
            'response': ai_response,
            'chatId': chat_id
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route("/chat-sessions", methods=["GET"])
def get_chat_sessions():
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['financial_assistant']
        sessions = list(db.chat_sessions.find().sort('timestamp', -1))
        
        formatted_sessions = []
        for session in sessions:
            formatted_sessions.append({
                '_id': str(session['_id']),
                'timestamp': session['timestamp'].isoformat() if 'timestamp' in session else None,
                'message_count': session.get('message_count', 0),
                'first_message': session.get('first_message', 'New Chat')
            })
        
        return jsonify({'sessions': formatted_sessions})
    except Exception as e:
        print(f"Error getting chat sessions: {str(e)}")
        return jsonify({"error": "Failed to get chat sessions"}), 500

@app.route("/chat-history/<chat_id>", methods=["GET"])
def get_chat_history_route(chat_id):
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['financial_assistant']
        
        # Get messages for the chat
        messages = list(db.messages.find(
            {'chat_id': chat_id},
            {'_id': 0, 'role': 1, 'content': 1, 'timestamp': 1}
        ).sort('timestamp', 1))
        
        return jsonify({"history": messages})
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        return jsonify({"error": "Failed to get chat history"}), 500

@app.route("/chat-session/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['financial_assistant']
        
        # Delete messages and session
        db.messages.delete_many({'chat_id': chat_id})
        db.chat_sessions.delete_one({'_id': chat_id})
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting chat: {str(e)}")
        return jsonify({"error": "Failed to delete chat"}), 500

if __name__ == '__main__':
    app.run(debug=True)
