import os
from datetime import datetime

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

client = MongoClient(MONGODB_URI)

db = client["ai_career_assistant"]

users_collection = db["users"]
conversations_collection = db["conversations"]
messages_collection = db["messages"]


# ---------------- USER FUNCTIONS ----------------

def create_user(username, email, password):
    # Check if email already exists
    existing_user = users_collection.find_one({"email": email})

    if existing_user:
        return False

    # Hash password
    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )

    user = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "created_at": datetime.utcnow()
    }

    users_collection.insert_one(user)

    return True


def authenticate_user(email, password):
    user = users_collection.find_one({"email": email})

    if not user:
        return None

    if bcrypt.checkpw(
        password.encode("utf-8"),
        user["password"]
    ):
        return user

    return None


print("MongoDB connected successfully!")