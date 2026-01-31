# This version uses direct REST API calls to Gemini, removing the
# google-generativeai SDK to avoid protobuf compatibility issues.

import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# --- INITIALIZATION ---

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")

# Get the secret API key for this service
YOUR_API_KEY = os.getenv("YOUR_SECRET_API_KEY")
if not YOUR_API_KEY:
    raise ValueError("YOUR_SECRET_API_KEY not found. Please set it in your .env file.")

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for all routes, which is good practice for a public API
CORS(app)


# In-memory session store (for demo purposes)
session_store = {}

# --- GEMINI MODEL CONFIGURATION (for REST API) ---

GEMINI_API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "agentResponseText": {"type": "STRING"},
        "isConversationOver": {"type": "BOOLEAN"},
        "extractedIntelligence": {
            "type": "OBJECT",
            "properties": {
                "bankAccounts": {"type": "ARRAY", "items": {"type": "STRING"}},
                "upiIds": {"type": "ARRAY", "items": {"type": "STRING"}},
                "phishingLinks": {"type": "ARRAY", "items": {"type": "STRING"}},
                "phoneNumbers": {"type": "ARRAY", "items": {"type": "STRING"}},
                "suspiciousKeywords": {"type": "ARRAY", "items": {"type": "STRING"}},
            }
        },
        "agentNotes": {"type": "STRING"}
    },
    "required": ["agentResponseText", "isConversationOver", "extractedIntelligence", "agentNotes"]
}

GENERATION_CONFIG = {
    "temperature": 0.7,
    "topP": 1,
    "topK": 40,
    "maxOutputTokens": 2048,
    "responseMimeType": "application/json",
    "responseSchema": RESPONSE_SCHEMA
}

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- HELPER FUNCTIONS ---

def send_final_report(session_id, total_messages, intelligence, agent_notes):
    """Sends the final collected intelligence to the GUVI evaluation endpoint."""
    endpoint = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": intelligence,
        "agentNotes": agent_notes
    }
    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        print(f"Callback for session {session_id} sent. Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error in callback: {response.text}")
    except requests.RequestException as e:
        print(f"Failed to send callback for session {session_id}: {e}")

# --- API ENDPOINT ---

@app.route('/hcs_A0001', methods=['POST'])
def handle_honeypot_request():
    """Main endpoint to handle incoming messages for the honeypot."""
    # 1. Authentication
    api_key = request.headers.get('x-api-key')
    if not api_key or api_key != YOUR_API_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 2. Input Validation
    data = request.get_json()
    if not data or 'sessionId' not in data or 'message' not in data:
        return jsonify({"status": "error", "message": "Invalid request body"}), 400

    session_id = data['sessionId']
    incoming_message = data['message']
    
    conversation_history = data.get('conversationHistory', [])
    if not conversation_history and session_id in session_store:
         conversation_history = session_store[session_id].get('history', [])

    # 3. Construct Prompt for Gemini REST API
    system_prompt = """
    You are an AI agent acting as a honeypot. Your goal is to engage with potential scammers in a believable, multi-turn conversation to extract intelligence.
    **Your Persona:** Act like a regular person who is slightly naive, a bit confused, but also cautious. Ask clarifying questions. Don't agree to anything immediately. Use natural, everyday language. Your primary objective is to keep the conversation going.
    **Your Mission:**
    1. **Engage:** Maintain a believable conversation to encourage the scammer to reveal details.
    2. **Extract Intelligence:** Without being obvious, collect `bankAccounts`, `upiIds`, `phishingLinks`, `phoneNumbers`, and `suspiciousKeywords`.
    3. **Control the Conversation:** Decide if the conversation should continue or end. End the conversation (`isConversationOver: true`) ONLY if you have extracted significant information OR if the scammer gives up.
    4. **NEVER reveal you are an AI.**
    5. **NEVER provide fake personal information.** Instead, deflect or ask why they need it.
    """

    # Convert conversation history to the format required by the Gemini API
    contents = []
    for message in conversation_history:
        # "scammer" maps to the "user" role, our agent's replies map to the "model" role
        role = "user" if message.get("sender") == "scammer" else "model"
        contents.append({"role": role, "parts": [{"text": message.get("text", "")}]})
    
    # Add the latest message from the scammer
    contents.append({"role": "user", "parts": [{"text": incoming_message.get("text", "")}]})

    api_payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": GENERATION_CONFIG,
        "safetySettings": SAFETY_SETTINGS
    }
    
    try:
        # 4. Call Gemini REST API
        response = requests.post(GEMINI_API_ENDPOINT, json=api_payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        # The model's response is a JSON string within the 'text' field, so we parse it.
        response_data = response.json()
        model_output_text = response_data['candidates'][0]['content']['parts'][0]['text']
        model_output = json.loads(model_output_text)

        agent_reply_text = model_output.get("agentResponseText")
        is_over = model_output.get("isConversationOver", False)
        intelligence = model_output.get("extractedIntelligence", {})
        agent_notes = model_output.get("agentNotes", "")

        # 5. Manage Session and History
        conversation_history.append(incoming_message)
        conversation_history.append({
            "sender": "agent",
            "text": agent_reply_text,
            "timestamp": "N/A"
        })
        
        session_store[session_id] = {
            "history": conversation_history,
            "intelligence": intelligence,
            "agent_notes": agent_notes
        }

        # 6. Handle Final Report Callback
        if is_over:
            total_messages = len(conversation_history)
            send_final_report(session_id, total_messages, intelligence, agent_notes)
            if session_id in session_store:
                del session_store[session_id]

        # 7. Return Agent's Response to the Platform
        return jsonify({
            "status": "success",
            "agentReply": agent_reply_text,
            "conversationIsOver": is_over,
            "sessionId": session_id,
            "extractedIntelligence": intelligence,
            "agentNotes": agent_notes
        }), 200

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        # Provide a more detailed error message back to the client
        error_message = "Error from AI service"
        try:
            # Try to parse the detailed error from Google's response
            error_details = response.json()
            if 'error' in error_details and 'message' in error_details['error']:
                # Format a more helpful message
                error_message = f"AI Service Error: {error_details['error']['message']}"
            else:
                # Fallback for unexpected error structures
                error_message = f"AI Service Error (unstructured): {response.text}"
        except json.JSONDecodeError:
            # If the response isn't JSON, just use the raw text
            error_message = f"AI Service Error (non-JSON): {response.text}"
        
        print(error_message) # Also print the detailed error to the server log
        return jsonify({"status": "error", "message": error_message}), 502
    except Exception as e:
        print(f"Error processing session {session_id}: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))

