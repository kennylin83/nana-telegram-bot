import os, json

MEMORY_PATH = "memory"
AUTHORIZED_IDS = ["555412099"]

def is_authorized(update):
    uid = str(update.effective_user.id)
    if uid not in AUTHORIZED_IDS:
        update.message.reply_text("你不是我主人啦 💢")
        return False
    return True

def memory_file(user_id):
    return os.path.join(MEMORY_PATH, f"{user_id}.json")

def load_memory(user_id):
    path = memory_file(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(user_id, history):
    with open(memory_file(user_id), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def reset_memory(user_id):
    path = memory_file(user_id)
    if os.path.exists(path):
        os.remove(path)