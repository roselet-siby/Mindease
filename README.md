# MindEase

An AI-powered mental health support chatbot, built as my final year MCA project.

## Features

- Chatbot that detects the user's emotion and sentiment and replies with supportive responses
- Crisis keyword detection
- Mood check-in
- Appointment booking with psychiatrists
- Doctor login and dashboard
- Admin panel
- PDF report generation for users

## Built With

- **Backend:** Python, Flask
- **Database:** MySQL
- **NLP:** HuggingFace Transformers, two fine-tuned DistilBERT models (emotion detection and sentiment analysis)
- **LLM responses:** Groq API
- **Frontend:** HTML templates

## How the Chatbot Works

1. The user's message is checked for greetings and crisis keywords.
2. The DistilBERT models detect the emotion and sentiment of the message.
3. Keyword rules and a confidence threshold decide how the reply is chosen.
4. The Groq API generates the final response.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/roselet-siby/Mindease.git
cd Mindease
```

### 2. Install the requirements

Python 3.10 is recommended.

```bash
pip install flask flask-mysqldb bcrypt python-dotenv transformers torch groq reportlab
```

### 3. Create the database

Create a MySQL database named `mental_health_chatbot` and create the tables the app uses.

### 4. Add your environment variables

Create a file named `.env` in the project folder:

```
GROQ_API_KEY=your-groq-api-key
FLASK_SECRET_KEY=any-long-random-text
MYSQL_PASSWORD=your-mysql-password
```

### 5. Train the models

The trained models are too large for GitHub, so they are not included. Train them yourself with the data files in this repository:

```bash
python train_emotion_model.py
python train_sentiment_model.py
```

The training data comes from the [Emotions Dataset for NLP](https://www.kaggle.com/datasets/praveengovi/emotions-dataset-for-nlp) on Kaggle.

### 6. Run the app

```bash
python app.py
```

Then open the address shown in the terminal (usually http://127.0.0.1:5000).

## Disclaimer

MindEase is a student project. It is not a replacement for professional mental health care. If you or someone you know is in crisis, please contact a local emergency number or a qualified professional.

## Author

Roselet Siby
GitHub: [roselet-siby](https://github.com/roselet-siby)
