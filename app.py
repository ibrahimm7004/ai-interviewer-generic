from flask import Flask, render_template, request, jsonify, redirect, url_for
from openai import OpenAI
import os
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)

# Load OpenAI API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global variables
assistant = None
thread = None
interview_type = None
candidate_years_of_experience = None
job_important_skills = None
job_level = None

global ids_list, questions_asked
ids_list = []
questions_asked = []


def take_interview(question_count, response):
    """
    Generates the next interview question dynamically based on the candidate's previous response.
    """
    global job_level, candidate_years_of_experience, job_important_skills

    flag = False
    skills_text = ""

    if isinstance(job_important_skills, list):
        skills_text = ', '.join(job_important_skills)
    else:
        skills_text = "Not provided"

    while not flag:
        # Initial easy question for the first round
        first_question = (
            f"Start the interview by asking an easy question suitable for a {job_level} {interview_type} "
            f"with {candidate_years_of_experience} years of experience. Focus on foundational {interview_type} concepts"
        )
        # Tailored question based on candidate response
        question = (
            f"""Based on the candidate's last response: "{response}", adjust the difficulty as needed, making them 
            easier if the candidate answers badly, and increasing difficulty if they answer well. 
            - Aim to gauge knowledge in key skills: {skills_text}.
            - Tailor the question to their experience level ({candidate_years_of_experience} years) and job level ({job_level}).
            Only return the question."""
        )

        # Select the first or follow-up question
        if question_count == 0:
            content = first_question
        else:
            content = question

        # Send the message to OpenAI assistant
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=content
        )

        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        # Retrieve the run status
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

        # Fetch messages and identify the next question
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        for i in messages.data:
            if (i.assistant_id is not None) and (i.id not in ids_list) and (len(i.content) != 0):
                ids_list.append(i.id)
                questions_asked.append(i.content[0].text.value)
                question_count += 1
                flag = True
                break

    return questions_asked[-1]


@app.route('/')
def index():
    """Renders the initial screen for interview setup."""
    return render_template('index.html')


@app.route('/submit_role', methods=['POST'])
def submit_role():
    """
    Handles form submission, initializes OpenAI assistant with role and parameters,
    and redirects to the interview page.
    """
    global assistant, thread, interview_type
    global candidate_years_of_experience, job_important_skills, job_level

    # Retrieve the form data
    interview_type = request.form['interview_role']
    candidate_years_of_experience = request.form['candidate_years_of_experience']
    job_important_skills = [skill.strip(
    ) for skill in request.form['job_important_skills'].split(",") if skill.strip()]
    job_level = request.form['job_level']

    # Initialize assistant and thread with new parameters
    assistant = client.beta.assistants.create(
        name=f"{interview_type} Interviewer",
        instructions=f"""You are a {interview_type} Interviewer. Take technical interviews by asking one question 
        at a time, adjusting question difficulty based on the candidate's responses, years of experience, job level, 
        and job description (JD) skills required. 
        Consider these parameters:
        - Years of experience: {candidate_years_of_experience}
        - Required skills from the JD: {', '.join(job_important_skills)}
        - Job level: {job_level}

        Start with foundational {interview_type} questions and adapt based on responses, moving to more advanced 
        topics related to JD skills and level if the candidate shows proficiency. Only return the question, nothing else.""",
        model="gpt-4o-mini"
    )
    thread = client.beta.threads.create()

    # Redirect to the interview page
    return redirect(url_for('interview'))


@app.route('/interview')
def interview():
    """Renders the interview page."""
    return render_template('interview.html')


@app.route('/get_next_question', methods=['POST'])
def get_next_question():
    """
    Handles the retrieval of the next interview question based on the candidate's response.
    """
    data = request.json
    question_count = data.get("question_count", 0)
    response = data.get("response", "")

    # Call the take_interview function
    next_question = take_interview(question_count, response)

    return jsonify({"question": next_question})


if __name__ == '__main__':
    app.run(debug=True)
