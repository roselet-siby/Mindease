# ============================================================
# SENTIMENT MODEL TRAINING SCRIPT
# MindEase - AI Mental Health Chatbot
# ============================================================
# NOTE: We derive sentiment labels from emotion labels
#   Positive  -> joy, love
#   Negative  -> sadness, anger, fear
#   Neutral   -> surprise
# ============================================================

import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)
from sklearn.metrics import accuracy_score, f1_score
import os

# ============================================================
# STEP 1 - CONFIGURATION
# ============================================================

BASE_MODEL  = "distilbert-base-uncased"
DATA_DIR    = "./"
OUTPUT_DIR  = "./models/sentiment_model"

# Sentiment labels
SENTIMENT_LABELS = ["Negative", "Neutral", "Positive"]
LABEL2ID = {label: idx for idx, label in enumerate(SENTIMENT_LABELS)}
ID2LABEL = {idx: label for idx, label in enumerate(SENTIMENT_LABELS)}

# Emotion → Sentiment mapping
EMOTION_TO_SENTIMENT = {
    "joy":      "Positive",
    "love":     "Positive",
    "surprise": "Neutral",
    "sadness":  "Negative",
    "anger":    "Negative",
    "fear":     "Negative"
}

NUM_EPOCHS    = 3
BATCH_SIZE    = 16
MAX_LENGTH    = 128
LEARNING_RATE = 2e-5

print("=" * 60)
print("SENTIMENT MODEL TRAINING - MindEase Chatbot")
print("=" * 60)
print(f"Base Model  : {BASE_MODEL}")
print(f"Epochs      : {NUM_EPOCHS}")
print(f"Labels      : {SENTIMENT_LABELS}")
print("=" * 60)


# ============================================================
# STEP 2 - LOAD AND PARSE TXT FILES
# ============================================================

def load_txt_dataset(filepath):
    """Load txt file and convert emotion labels to sentiment labels"""
    texts, labels = [], []
    skipped = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(";")
            if len(parts) != 2:
                skipped += 1
                continue
            text, emotion = parts[0].strip(), parts[1].strip()
            if emotion not in EMOTION_TO_SENTIMENT:
                skipped += 1
                continue
            sentiment = EMOTION_TO_SENTIMENT[emotion]
            texts.append(text)
            labels.append(LABEL2ID[sentiment])

    print(f"Loaded {len(texts)} samples from {filepath} (skipped {skipped})")
    return texts, labels


print("\n[1/5] Loading and converting datasets...")
train_texts, train_labels = load_txt_dataset(os.path.join(DATA_DIR, "train.txt"))
val_texts,   val_labels   = load_txt_dataset(os.path.join(DATA_DIR, "val.txt"))
test_texts,  test_labels  = load_txt_dataset(os.path.join(DATA_DIR, "test.txt"))

# Show sentiment distribution
print("\nTraining sentiment distribution:")
df_check = pd.Series(train_labels)
for idx, sentiment in ID2LABEL.items():
    count = (df_check == idx).sum()
    print(f"  {sentiment:10s} : {count}")


# ============================================================
# STEP 3 - TOKENIZER
# ============================================================

print("\n[2/5] Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)


# ============================================================
# STEP 4 - DATASET CLASS
# ============================================================

class SentimentDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt"
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids":      self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels":         self.labels[idx]
        }


print("[3/5] Tokenizing datasets...")
train_dataset = SentimentDataset(train_texts, train_labels, tokenizer, MAX_LENGTH)
val_dataset   = SentimentDataset(val_texts,   val_labels,   tokenizer, MAX_LENGTH)
test_dataset  = SentimentDataset(test_texts,  test_labels,  tokenizer, MAX_LENGTH)
print(f"  Train size : {len(train_dataset)}")
print(f"  Val size   : {len(val_dataset)}")
print(f"  Test size  : {len(test_dataset)}")


# ============================================================
# STEP 5 - LOAD MODEL
# ============================================================

print("\n[4/5] Loading base model...")
model = AutoModelForSequenceClassification.from_pretrained(
    BASE_MODEL,
    num_labels=len(SENTIMENT_LABELS),
    id2label=ID2LABEL,
    label2id=LABEL2ID
)


# ============================================================
# STEP 6 - METRICS
# ============================================================

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, predictions)
    f1  = f1_score(labels, predictions, average="weighted")
    return {"accuracy": acc, "f1": f1}


# ============================================================
# STEP 7 - TRAINING ARGUMENTS
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    learning_rate=LEARNING_RATE,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
    logging_dir="./logs/emotion",
    logging_steps=50,
    warmup_steps=100,
    weight_decay=0.01,
    report_to="none"
)


# ============================================================
# STEP 8 - TRAIN
# ============================================================

print("\n[5/5] Starting training...")
print("This will take 10-20 minutes depending on your CPU/GPU\n")

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics
)

trainer.train()


# ============================================================
# STEP 9 - EVALUATE
# ============================================================

print("\nEvaluating on test set...")
results = trainer.evaluate(test_dataset)
print(f"\n{'='*60}")
print(f"TEST RESULTS")
print(f"{'='*60}")
print(f"Accuracy : {results['eval_accuracy']:.4f} ({results['eval_accuracy']*100:.2f}%)")
print(f"F1 Score : {results['eval_f1']:.4f}")


# ============================================================
# STEP 10 - SAVE
# ============================================================

print(f"\nSaving model to {OUTPUT_DIR} ...")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"\n{'='*60}")
print("SENTIMENT MODEL TRAINING COMPLETE!")
print(f"Model saved to: {OUTPUT_DIR}")
print("You can now use this model in chatbot_engine.py")
print(f"{'='*60}")