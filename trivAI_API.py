import json
import os
from flask import Flask, request, jsonify, session
from openai import OpenAI
import openai
import logging
from dotenv import load_dotenv

load_dotenv('/Users/nickryan/Documents/TrivAI_Flask_API/API_KEY.env')

# Basic configuration for the logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

app = Flask(__name__)
app.secret_key = 'your-very-secure-and-unique-secret-key'

# Replace with your actual ChatGPT API endpoint and key
CHATGPT_API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY')

client = openai.OpenAI(api_key=CHATGPT_API_KEY)

session = dict()

@app.route('/start_trivia', methods=['GET'])
def start_trivia():
    session['total_questions'] = request.args.get('numQuestions', default=1, type=int)
    session['asked_questions'] = 0
    session['asked_questions_list'] = [] 

    difficulty = request.args.get('difficulty')
    topic = request.args.get('topic')

    # Initialize conversation context
    session['conversation'] = [{
        "role": "system",
        "content": f"You are a game show host. When asked, provide a given number of "
                   f"{difficulty} trivia questions about {topic} in multiple choice "
                   "form (A, B, C, D) along with the correct answers. The results must "
                   "be returned in JSON format with a key 'questions' that maps to an array "
                   "of objects, each containing 'question' for the trivia query, 'options' as "
                   "a dictionary with choices labeled A to D, and 'correct_answer' "
                   "indicating the label of the correct option."
    }]

    return jsonify({"message": "Trivia session initialized. Use /get_questions to retrieve trivia."})

@app.route('/get_questions', methods=['GET'])
def get_questions():
    number_of_questions = request.args.get('number', default=1, type=int)
    remaining_questions = session['total_questions'] - session['asked_questions']

    print(f"number of question: {number_of_questions}")

    if number_of_questions > remaining_questions:
        number_of_questions = remaining_questions

    if number_of_questions <= 0:
        return jsonify({"message": "No more questions available."})

    previous_questions_formatted = "; ".join([f'"{q}"' for q in session['asked_questions_list']])
    prompt = f"Please give me the next {number_of_questions} questions, avoiding repetition. The previous questions are as follows: {previous_questions_formatted}"
    
    session['conversation'].append({"role": "user", "content": prompt})



    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=session["conversation"]
    )

    contentJSON = json.loads(response.choices[0].message.content)

    formatted_content = format_questions_for_conversation(contentJSON)
    session['conversation'].append({"role": "assistant", "content": formatted_content})
    session['asked_questions'] += number_of_questions

    conversation_data = session.get('conversation', [])
    pretty_conversation = json.dumps(conversation_data, indent=4)
    app.logger.debug(pretty_conversation)

    app.logger.info(f"questions content: {contentJSON.get('questions', [])}")

    for question in contentJSON.get('questions', []):
        app.logger.info(f"question: {question['question']}")
        session['asked_questions_list'].append(question['question'])

    app.logger.info(f"asked questions: {session['asked_questions_list']}")

    # conversation_data = session.get('conversation', [])
    # pretty_conversation = json.dumps(conversation_data, indent=4)

    # app.logger.debug(pretty_conversation)

    return jsonify(contentJSON)

@app.route('/get_remaining_questions', methods=['GET'])
def get_remaining_questions():
    remaining_questions = session['total_questions'] - session['asked_questions']

    if remaining_questions <= 0:
        return jsonify({"message": "No more questions available."})

    return get_questions(number=remaining_questions)

def format_questions_for_conversation(questions_json):
    questions_text = "Here are your trivia questions:\n"
    for idx, question in enumerate(questions_json['questions'], 1):
        options_text = "; ".join([f"{k}: {v}" for k, v in question['options'].items()])
        questions_text += f"{idx}) {question['question']} Options - {options_text}. Correct answer: {question['correct_answer']}.\n"
    return questions_text


if __name__ == '__main__':
    app.run(debug=True)
