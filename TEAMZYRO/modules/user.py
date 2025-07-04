from TEAMZYRO import users  # MongoDB collection

def get_or_create_user(user_id: int):
    user = users.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "coins": 0, "tokens": 0}
        users.insert_one(user)
    return user
