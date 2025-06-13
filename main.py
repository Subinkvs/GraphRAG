import os
import uuid
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase
from dotenv import load_dotenv

from ifc_to_neo4j import process_ifc_file
from chatbot import Chatbot

# Load .env values
load_dotenv()

# Flask app setup
app = Flask(__name__)
CORS(app)

# Neo4j connection setup
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "ifcrag123@")
DATABASE_NAME = os.getenv("NEO4J_DB_NAME", "test2.db")

# Connect to Neo4j
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Instantiate and initialize chatbot globally
chatbot = Chatbot()
chatbot.initialize(driver, DATABASE_NAME)

# ======== API 1: Upload IFC File and Process it ========
@app.route('/upload-ifc', methods=['POST'])
def upload_ifc():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.lower().endswith('.ifc'):
        return jsonify({'error': 'Only .ifc files are allowed'}), 400

    try:
        # Save to a temporary file
        os.makedirs('temp_uploads', exist_ok=True)
        filename = f"temp_{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join('temp_uploads', filename)
        file.save(filepath)

        # Process the IFC file and load into Neo4j
        process_ifc_file(filepath, driver, DATABASE_NAME)

        # Optional: Remove after processing
        os.remove(filepath)

        return jsonify({'message': 'IFC file uploaded and processed successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======== API 2: Chat with the Bot ========
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')

    if not message.strip():
        return jsonify({'error': 'Empty message'}), 400

    try:
        # Run the async chatbot method inside the Flask sync route
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(chatbot.message(message))
                # Split response into structured lines
        lines = [line.strip() for line in response.split('\n') if line.strip()]

        return jsonify({
            'response': lines  # List of each line for UI or structured use
        }), 200


    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======== Main Entrypoint ========
if __name__ == '__main__':
    app.run(debug=True)
