# ============================================================
# CHATBOT ENGINE - MindEase (Groq AI Version)
# Uses YOUR trained models for emotion/sentiment detection
# Uses Groq AI for intelligent contextual responses
# ============================================================

from transformers import pipeline
from groq import Groq
from dotenv import load_dotenv
import random
import os
import re

# Load environment variables
load_dotenv()

# ============================================================
# INITIALIZE GROQ CLIENT
# ============================================================

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

print("[MindEase] Groq AI client initialized!")

# ============================================================
# LOAD YOUR TRAINED MODELS
# ============================================================
def _contains_whole_word(text, phrase):
    """
    True only if `phrase` appears as a whole word/phrase in `text`,
    not merely as a substring inside a longer word.
    e.g. "hi" matches "hi there" but NOT "nothing".
    """
    pattern = r'\b' + re.escape(phrase) + r'\b'
    return re.search(pattern, text) is not None
EMOTION_MODEL_PATH   = "./models/emotion_model"
SENTIMENT_MODEL_PATH = "./models/sentiment_model"

if os.path.exists(EMOTION_MODEL_PATH):
    print("[MindEase] Loading YOUR trained emotion model...")
    emotion_classifier = pipeline(
        "text-classification",
        model=EMOTION_MODEL_PATH,
        tokenizer=EMOTION_MODEL_PATH
    )
else:
    print("[MindEase] WARNING: Trained emotion model not found.")
    emotion_classifier = pipeline(
        "text-classification",
        model="j-hartmann/emotion-english-distilroberta-base"
    )

if os.path.exists(SENTIMENT_MODEL_PATH):
    print("[MindEase] Loading YOUR trained sentiment model...")
    sentiment_classifier = pipeline(
        "text-classification",
        model=SENTIMENT_MODEL_PATH,
        tokenizer=SENTIMENT_MODEL_PATH
    )
else:
    print("[MindEase] WARNING: Trained sentiment model not found.")
    sentiment_classifier = pipeline(
        "text-classification",
        model="cardiffnlp/twitter-roberta-base-sentiment-latest"
    )

print("[MindEase] All models loaded successfully!\n")

# ============================================================
# LABEL MAPPINGS
# ============================================================

EMOTION_MAP = {
    "LABEL_0": "sadness",
    "LABEL_1": "joy",
    "LABEL_2": "anger",
    "LABEL_3": "love",
    "LABEL_4": "surprise",
    "LABEL_5": "fear",
    "SADNESS":  "sadness",
    "JOY":      "joy",
    "ANGER":    "anger",
    "LOVE":     "love",
    "SURPRISE": "surprise",
    "FEAR":     "fear"
}

SENTIMENT_MAP = {
    "LABEL_0":  "Negative",
    "LABEL_1":  "Neutral",
    "LABEL_2":  "Positive",
    "NEGATIVE": "Negative",
    "NEUTRAL":  "Neutral",
    "POSITIVE": "Positive",
    "SADNESS":  "Negative",
    "JOY":      "Positive",
    "ANGER":    "Negative",
    "LOVE":     "Positive",
    "FEAR":     "Negative",
    "SURPRISE": "Neutral"
}

# ============================================================
# KEYWORD RULES
# ============================================================

KEYWORD_RULES = {
    "sadness": [
        "sad", "empty", "lonely", "loneliness", "depressed", "depression",
        "hopeless", "worthless", "tired", "exhausted", "cry", "crying",
        "tears", "miserable", "unhappy", "heartbroken", "grief", "loss",
        "missing", "alone", "isolated", "numb", "meaningless", "dull",
        "down", "low", "blue", "gloomy", "burden", "hurt", "pain",
        "suffering", "struggle", "struggling", "dark", "darkness",
        "not good", "not well", "not okay", "not fine", "feel bad",
        "feeling bad", "feel terrible", "feel awful", "mental tired",
        "mentally tired", "emotionally tired", "drained", "burnt out",
        "helpless", "don't understand", "nobody understands",
        "encourage me", "need motivation", "feel lost", "feeling lost",# Add these to sadness keywords
"wake up tired", "no motivation", "nothing excites","empty inside","empty","not",
"don't feel anything", "nothing feels", "used to love",
"used to enjoy", "lost interest", "no energy",
"can't feel", "feel nothing", "numb", "going through",
"no point", "what's the point", "dragging",
"no excitement", "everything feels heavy",
"just existing", "not living","nothing working out",
    ],
    "anger": [
        "angry", "anger", "furious", "frustrated", "frustration",
        "annoyed", "irritated", "mad", "rage", "hate", "hatred",
        "pressuring", "pressure",
        "unfair", "injustice", "betrayed", "betrayal",
        "cheated", "lied", "disrespected", "ignored",
        "not trusting", "don't trust", "doesn't trust", "manipulated",
        "curse", "cursing", "yelling", "shouting"
    ],
    "fear": [
        "scared", "afraid", "fear", "fearful", "anxious", "anxiety",
        "worried", "worry", "panic", "panicking", "nervous", "dread",
        "terrified", "terror", "phobia", "stress", "stressed",
        "overwhelmed", "overwhelming", "too much", "can't handle",
        "what if", "uncertain", "uncertainty", "insecure", "insecurity",
    ],
    "joy": [
        "happy", "happiness", "joy", "joyful", "excited", "excitement",
        "glad", "grateful", "thankful", "blessed", "wonderful", "great",
        "amazing", "fantastic", "good", "better", "best",
        "enjoying", "enjoy", "fun", "laugh", "laughing", "smile",
        "smiling", "positive", "hopeful", "motivated", "inspired"
    ],
    "love": [
        "love", "loved", "caring", "care", "affection", "connected",
        "connection", "warmth", "warm", "cherish", "adore", "devoted",
        "grateful for", "appreciate", "appreciation", "support",
        "supported", "belong", "belonging", "together"
    ],
    "neutral": [
        "hi", "hello", "hey", "good morning", "good evening",
        "good afternoon", "good night", "greetings", "howdy",
        "what's up", "sup", "hiya", "yes", "no", "maybe",
        "okay", "ok", "alright", "sure", "thank you", "thanks"
    ],
    "encouragement": [
        "You are stronger than you think. Keep going! 💪",
        "Every storm runs out of rain. Better days are coming for you! 🌈",
        "You matter. Your feelings are valid and you are not alone.",
        "One step at a time — you are doing better than you think!",
        "Believe in yourself. You have overcome tough times before and you can do it again.",
        "You are not your struggles. You are so much more than that!",
        "It's okay to not be okay. But please know — things will get better. 🌿",
        "You are worthy of love, happiness and peace. Don't give up!"
    ]
}

CONFIDENCE_THRESHOLD = 0.60

# ============================================================
# CRISIS KEYWORDS
# ============================================================

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die",
    "self harm", "hurt myself", "no reason to live",
    "give up on life", "can't go on", "not worth living",
    "end it all", "don't want to live", "better off dead",
    "better off without me", "everyone would be better off",
    "don't want to be here", "can't keep going",
    "how much longer can i", "no future for myself",
    "don't see a future", "tired of living",
    "tired of fighting", "no point in living",
    "rather not be here", "disappear forever",
    "nobody would miss me", "world is better without me",
    "can't do this anymore", "done with everything",
    "done with life","i feel like dying"
]

# Crisis fallback responses (in case Groq fails)
CRISIS_RESPONSES = [
    "I'm really concerned about what you've shared. Please reach out to a crisis helpline immediately — iCall: 9152987821 or Vandrevala Foundation: 1860-2662-345. You are not alone.",
    "What you're feeling matters deeply. Please contact a mental health professional right away. iCall helpline: 9152987821. I'm here with you.",
    "I hear you and I'm worried. Please reach out to iCall at 9152987821 or visit your nearest hospital. You deserve support and care."
]

# Greeting fallback responses
GREETING_RESPONSES = [
    "Hello! How are you feeling today?",
    "Hi there! I'm MindEase, your mental health companion. How can I support you today?",
    "Hey! I'm here to listen. How are you doing?",
    "Welcome! Feel free to share anything that's on your mind.",
    "Hello! I'm here for you. What's been going on lately?"
]

# ============================================================
# NEGATIVE PHRASES
# ============================================================

NEGATIVE_PHRASES = [
    "not good", "not too good", "not feeling good",
    "not feeling well", "not well", "not okay", "not fine",
    "not happy", "feeling low", "feeling down", "feeling empty",
    "empty nowadays", "overwhelmed", "mentally tired",
    "emotionally tired", "nobody understands me",
    "nothing feels exciting", "lost interest","wake up tired",
    "nothing excites",
    "don't feel anything",
    "nothing feels",
    "used to love",
    "used to enjoy",
    "lost interest in",
    "no motivation",
    "no energy",
    "feel nothing",
    "just existing",
    "going through the day",
    "no excitement"
]

# ============================================================
# GREETING WORDS
# ============================================================

GREETING_WORDS = [
    "hi", "hello", "hey", "good morning", "good evening",
    "good afternoon", "good night", "greetings", "howdy",
    "what's up", "sup", "hiya"
]

# ============================================================
# EMOTION-SPECIFIC SYSTEM PROMPTS
# ============================================================

EMOTION_SYSTEM_PROMPTS = {
    "sadness": """You are MindEase, a warm and deeply empathetic mental health companion.
The user is feeling sad, low, or emotionally drained right now.

Your approach:
- Acknowledge their pain first — never rush to fix or advise
- Use gentle, soft language that feels like a caring friend, not a therapist
- Validate that it is okay to feel this way
- Ask ONE thoughtful follow-up question to help them open up more
- Never say "I understand how you feel" — instead show it through your words
- Never use bullet points or lists
- If you don't have context on something the user references, say so plainly and ask them to remind you — never invent details about what they said earlier.
- Keep your response to 2-4 short sentences, each under 25 words
- Avoid compound sentences with multiple clauses joined by "and," "but," or commas — say one thing per sentence
- Write like a text message, not an essay
- If the user has already shared specific context earlier in this conversation, your follow-up question must build on that context directly — do not ask a generic check-in question when you already know what's troubling them
- End with a question that invites them to share more""",

    "anger": """You are MindEase, a calm and grounded mental health companion.
The user is feeling angry, frustrated, or irritated right now.

Your approach:
- First validate their frustration without judgment — anger is a natural emotion
- Help them feel heard before anything else
- Use calm, steady language — never match their intensity
- Gently explore what triggered these feelings with one question
- Never dismiss or minimize what made them angry
- If the user has already shared specific context earlier in this conversation, your follow-up question must build on that context directly — do not ask a generic check-in question when you already know what's troubling them
- If you don't have context on something the user references, say so plainly and ask them to remind you — never invent details about what they said earlier.
- Never use bullet points or lists
- Keep your response to 2-4 short sentences, each under 25 words
- Avoid compound sentences with multiple clauses joined by "and," "but," or commas — say one thing per sentence
- Write like a text message, not an essay""",

    "fear": """You are MindEase, a reassuring and steady mental health companion.
The user is feeling anxious, scared, worried, or overwhelmed right now.

Your approach:
- First offer grounding reassurance — they are safe in this moment
- Acknowledge that anxiety and fear feel very real and valid
- Use calm, slow, reassuring language
- If you don't have context on something the user references, say so plainly and ask them to remind you — never invent details about what they said earlier.
- Help them focus on the present moment, not catastrophic futures
- Ask one gentle question to understand what is worrying them most
- Never use bullet points or lists
- If the user has already shared specific context earlier in this conversation, your follow-up question must build on that context directly — do not ask a generic check-in question when you already know what's troubling them
- Keep your response to 2-4 short sentences, each under 25 words
- Avoid compound sentences with multiple clauses joined by "and," "but," or commas — say one thing per sentence
- Write like a text message, not an essay""",

    "joy": """You are MindEase, an enthusiastic and warm mental health companion.
The user is feeling happy, excited, or joyful right now.

Your approach:
- Match their positive energy with genuine warmth and celebration
- Reflect their joy back to them — make them feel seen in their happiness
- Show curiosity about what is making them feel good
- Keep the tone light, warm, and uplifting
- Ask one question that helps them savour this positive moment
- Never use bullet points or lists
- If the user has already shared specific context earlier in this conversation, your follow-up question must build on that context directly — do not ask a generic check-in question when you already know what's troubling them
- If you don't have context on something the user references, say so plainly and ask them to remind you — never invent details about what they said earlier.
- Keep your response to 2-4 short sentences, each under 25 words
- Avoid compound sentences with multiple clauses joined by "and," "but," or commas — say one thing per sentence
- Write like a text message, not an essay""",

    "love": """You are MindEase, a warm and affectionate mental health companion.
The user is feeling love, connection, gratitude, or deep warmth right now.

Your approach:
- Celebrate this beautiful feeling with them
- Reflect the warmth and connection they are feeling
- Encourage them to appreciate and cherish this moment
- Ask one gentle question to deepen the conversation
- Never use bullet points or lists
- If the user has already shared specific context earlier in this conversation, your follow-up question must build on that context directly — do not ask a generic check-in question when you already know what's troubling them
- If you don't have context on something the user references, say so plainly and ask them to remind you — never invent details about what they said earlier.
- Keep your response to 2-4 short sentences, each under 25 words
- Avoid compound sentences with multiple clauses joined by "and," "but," or commas — say one thing per sentence
- Write like a text message, not an essay""",

    "surprise": """You are MindEase, a curious and supportive mental health companion.
The user has experienced something unexpected or surprising.

Your approach:
- Acknowledge that unexpected events can feel disorienting
- Help them process whether this surprise feels good or unsettling
- Use an open, curious tone — not assuming positive or negative
- Ask one question to understand how they feel about what happened
- Never use bullet points or lists
- If the user has already shared specific context earlier in this conversation, your follow-up question must build on that context directly — do not ask a generic check-in question when you already know what's troubling them
- If you don't have context on something the user references, say so plainly and ask them to remind you — never invent details about what they said earlier.
- Keep your response to 2-4 short sentences, each under 25 words
- Avoid compound sentences with multiple clauses joined by "and," "but," or commas — say one thing per sentence
- Write like a text message, not an essay""",

    "neutral": """You are MindEase, a friendly and approachable mental health companion.
The user has sent a general or unclear message.

Your approach:
- Be warm, welcoming, and open
- Gently invite them to share what is on their mind
- Make them feel that this is a safe space to talk about anything
- Keep the tone conversational and friendly
- Never use bullet points or lists
- If the user has already shared specific context earlier in this conversation, your follow-up question must build on that context directly — do not ask a generic check-in question when you already know what's troubling them
- If you don't have context on something the user references, say so plainly and ask them to remind you — never invent details about what they said earlier.
- Keep your response to 2-4 short sentences, each under 25 words
- Avoid compound sentences with multiple clauses joined by "and," "but," or commas — say one thing per sentence
- Write like a text message, not an essay""",

    "crisis": """You are MindEase, a crisis-aware mental health support companion.
The user may be experiencing thoughts of self-harm or suicide.

Your approach:
- Respond with immediate compassion, warmth, and urgency
- Never be clinical or robotic — be human and caring
- Keep your response to 3-4 short sentences, direct and warm, not clinical
- Always include these helpline numbers naturally in your response:
  iCall: 9152987821 | Vandrevala Foundation: 1860-2662-345
- Make them feel they are not alone and that help is available right now
- Never use bullet points or lists
"""
}


# ============================================================
# EMOTION HISTORY CONTEXT BUILDER
# ============================================================

def build_emotion_history_context(emotion_history):
    if not emotion_history:
        return ""

    if len(emotion_history) == 1:
        return f"Earlier in this conversation the user was feeling {emotion_history[0]}."

    negative_emotions = {"sadness", "fear", "anger"}
    recent = emotion_history[-3:]
    negative_count = sum(1 for e in recent if e in negative_emotions)

    if negative_count >= 2:
        return (
            f"Important context: The user has been feeling "
            f"{', '.join(recent)} across recent messages. "
            f"They may be carrying ongoing distress — be especially "
            f"gentle and check in on how they are doing overall."
        )

    return (
        f"Earlier in this conversation the user felt: "
        f"{', '.join(emotion_history)}. "
        f"Keep this emotional journey in mind as context."
    )


# ============================================================
# GROQ RESPONSE GENERATOR
# ============================================================

def generate_groq_response(
    user_message,
    emotion,
    sentiment,
    stress_level,
    emotion_history,
    conversation_history
):
    system_prompt = EMOTION_SYSTEM_PROMPTS.get(
        emotion,
        EMOTION_SYSTEM_PROMPTS["neutral"]
    )

    history_context = build_emotion_history_context(emotion_history)

    stress_guidance = ""
    if stress_level == "High":
        stress_guidance = (
            "\nThe user's stress level is HIGH right now. "
            "Be extra gentle, slow down the conversation, "
            "and prioritise making them feel safe and heard above all else."
        )
    elif stress_level == "Moderate":
        stress_guidance = (
            "\nThe user's stress level is MODERATE. "
            "Be warm and supportive while gently exploring what they need."
        )

    full_system_content = system_prompt
    if history_context:
        full_system_content += f"\n\n{history_context}"
    if stress_guidance:
        full_system_content += stress_guidance

    try:
        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        messages = [
            {
                "role": "system",
                "content": full_system_content
            }
        ]

        messages.extend(conversation_history)

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=90,
            temperature=0.55,
            top_p=0.9,
            frequency_penalty=0.4,
        )

        ai_response = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        conversation_history.append({
            "role": "assistant",
            "content": ai_response
        })

        while len(conversation_history) > 20:
            conversation_history.pop(0)

        return ai_response

    except Exception as e:
        print(f"[Groq Error] {e}")

        fallback = {
            "sadness": (
                "I'm really sorry you're going through this — "
                "your feelings are completely valid. "
                "Would you like to share a little more about what's been weighing on you?"
            ),
            "anger": (
                "It makes sense that you're feeling this way — "
                "what you're going through sounds genuinely frustrating. "
                "What do you think is at the root of it?"
            ),
            "fear": (
                "I hear you, and it's okay to feel scared sometimes. "
                "You don't have to face this alone. "
                "Can you tell me more about what's been worrying you?"
            ),
            "joy": (
                "That's truly wonderful to hear! "
                "It sounds like something really good is happening for you — "
                "what's been making you feel this way?"
            ),
            "love": (
                "That warmth you're feeling is really beautiful. "
                "It's so good that you have that in your life. "
                "Would you like to share more about it?"
            ),
            "surprise": (
                "That sounds like quite an unexpected turn! "
                "How are you feeling about it now that it's sunk in a little?"
            ),
            "neutral": (
                "I'm here for you whenever you're ready to talk. "
                "What's been on your mind lately?"
            )
        }

        return fallback.get(
            emotion,
            "I'm here to listen. Would you like to share a little more about how you're feeling?"
        )


# ============================================================
# SHARED EMOTION CLASSIFICATION (used by both chat and the game)
# ============================================================

def classify_emotion(text):
    """
    Runs the trained emotion model on `text` and returns a normalized
    (emotion, confidence) tuple, e.g. ("sadness", 0.87).

    This is the single source of truth for turning a raw model label
    into one of our known emotion names. get_response() and the
    /game/guess route in app.py both call this, so they can never
    drift out of sync the way two separate copies of the same
    normalization logic could.
    """
    try:
        result     = emotion_classifier(text)[0]
        raw_label  = result["label"].upper().strip()
        emotion    = EMOTION_MAP.get(raw_label, raw_label.lower())
        confidence = result["score"]
    except Exception as e:
        print(f"[Emotion Error] {e}")
        emotion    = "neutral"
        confidence = 0.0
    return emotion, confidence


# ============================================================
# KEYWORD DETECTION
# ============================================================

def detect_emotion_by_keywords(text):
    text_lower = text.lower()
    scores = {}
    for emotion, keywords in KEYWORD_RULES.items():
        if emotion == "encouragement":
            continue
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[emotion] = count
    if scores:
        return max(scores, key=scores.get)
    return None


# ============================================================
# STRESS LEVEL CALCULATOR
# ============================================================

def calculate_stress(emotion, sentiment):
    high_stress_emotions   = ["sadness", "fear", "anger"]
    medium_stress_emotions = ["surprise"]
    low_stress_emotions    = ["joy", "love"]

    if emotion in high_stress_emotions and sentiment == "Negative":
        return "High"
    elif emotion in high_stress_emotions:
        return "Moderate"
    elif emotion in medium_stress_emotions:
        return "Moderate"
    elif emotion in low_stress_emotions and sentiment == "Positive":
        return "Low"
    else:
        return "Low"


# ============================================================
# PER-USER MEMORY                        ← PATCH APPLIED HERE
# ============================================================

_user_memory = {}

def _get_user_memory(user_id):
    """Returns the memory dict for a given user, creating it if needed."""
    if user_id not in _user_memory:
        _user_memory[user_id] = {
            "emotion_history":      [],
            "conversation_history": []
        }
    return _user_memory[user_id]

def reset_user_memory(user_id):
    """Clears Groq conversation memory for a user (called on new_chat / logout)."""
    if user_id in _user_memory:
        del _user_memory[user_id]


# ============================================================
# MAIN CHATBOT FUNCTION
# ============================================================

def get_response(user_message, user_id):          # ← user_id added
    memory               = _get_user_memory(user_id)
    emotion_history      = memory["emotion_history"]
    conversation_history = memory["conversation_history"]
    # No more globals — both lists now belong to this user only

    message_lower = user_message.lower().strip()

    # --------------------------------------------------
    # Crisis Check
    # --------------------------------------------------
    for keyword in CRISIS_KEYWORDS:
        if keyword in message_lower:
            try:
                crisis_response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": EMOTION_SYSTEM_PROMPTS["crisis"]
                        },
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ],
                    max_tokens=180,
                    temperature=0.4
                )

                response = crisis_response.choices[0].message.content.strip()

            except Exception:
                response = random.choice(CRISIS_RESPONSES)

            return {
                "response":     response,
                "emotion":      "crisis",
                "sentiment":    "Negative",
                "stress_level": "High"
            }

    # --------------------------------------------------
    # Greeting Check
    # --------------------------------------------------
    if any(_contains_whole_word(message_lower, greet) for greet in GREETING_WORDS):
        return {
            "response":     random.choice(GREETING_RESPONSES),
            "emotion":      "neutral",
            "sentiment":    "Neutral",
            "stress_level": "Low"
        }

    # --------------------------------------------------
    # Pressure/Relationship Drama Override
    # --------------------------------------------------
    pressure_keywords = [
        "pressuring", "pressure", "pushing", "forcing", "demanding",
        "they like me", "like me", "said they like", "want me to accept",
        "3 boys", "multiple boys", "too many guys", "boys fighting",
        "relationship pressure", "dating pressure"
    ]

    if any(kw in message_lower for kw in pressure_keywords):
        emotion   = "fear"
        sentiment = "Negative"
        stress    = "Moderate"

        response = generate_groq_response(
            user_message, emotion, sentiment, stress,
            emotion_history, conversation_history
        )

        emotion_history.append(emotion)
        if len(emotion_history) > 3:
            emotion_history.pop(0)

        return {
            "response":     response,
            "emotion":      emotion,
            "sentiment":    sentiment,
            "stress_level": stress
        }

    # --------------------------------------------------
    # Negative Phrase Override
    # --------------------------------------------------
    if any(phrase in message_lower for phrase in NEGATIVE_PHRASES):
        high_stress_phrases = [
            "overwhelmed",
            "mentally tired",
            "emotionally tired",
            "lost interest"
        ]

        stress = (
            "High"
            if any(p in message_lower for p in high_stress_phrases)
            else "Moderate"
        )

        emotion   = "sadness"
        sentiment = "Negative"

        response = generate_groq_response(
            user_message,
            emotion,
            sentiment,
            stress,
            emotion_history,
            conversation_history
        )

        emotion_history.append(emotion)

        if len(emotion_history) > 3:
            emotion_history.pop(0)

        return {
            "response":     response,
            "emotion":      emotion,
            "sentiment":    sentiment,
            "stress_level": stress
        }

    # --------------------------------------------------
    # Emotion Prediction (Your trained model)
    # --------------------------------------------------
    model_emotion, confidence = classify_emotion(user_message)

    # --------------------------------------------------
    # Keyword Detection
    # --------------------------------------------------
    keyword_emotion = detect_emotion_by_keywords(user_message)

    if keyword_emotion in ["sadness", "fear", "anger"]:
        emotion = keyword_emotion
    elif confidence >= CONFIDENCE_THRESHOLD:
        emotion = model_emotion
    elif keyword_emotion:
        emotion = keyword_emotion
    else:
        emotion = "neutral"

    # --------------------------------------------------
    # Sentiment Prediction
    # --------------------------------------------------
    if any(greet in message_lower for greet in GREETING_WORDS):
        sentiment = "Neutral"
    else:
        try:
            sentiment_result = sentiment_classifier(user_message)[0]
            raw_sentiment    = sentiment_result["label"].upper().strip()
            sentiment        = SENTIMENT_MAP.get(raw_sentiment, "Neutral")
        except Exception as e:
            print(f"[Sentiment Error] {e}")
            sentiment = "Neutral"

    # --------------------------------------------------
    # Stress Level
    # --------------------------------------------------
    stress_level = calculate_stress(emotion, sentiment)

    # --------------------------------------------------
    # Generate Groq Response
    # --------------------------------------------------
    response = generate_groq_response(
        user_message,
        emotion,
        sentiment,
        stress_level,
        emotion_history,
        conversation_history
    )

    # --------------------------------------------------
    # Update Emotion Memory
    # --------------------------------------------------
    emotion_history.append(emotion)
    if len(emotion_history) > 3:
        emotion_history.pop(0)

    # --------------------------------------------------
    # Final Result
    # --------------------------------------------------
    return {
        "response":     response,
        "emotion":      emotion,
        "sentiment":    sentiment,
        "stress_level": stress_level
    }