import os
from sqlite3 import *
from utils import generate_hash_and_salt
from datetime import datetime

# Setting base directory so file path is independent of where python is run from (useful in a production setting)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
DB_PATH = os.path.join(BASE_DIR, "users.db")

# TODO: Do not open and close the database for every query as this is very inefficient

def execute_action(sql, *args):
    con = connect(DB_PATH)
    cur = con.cursor()
    cur.execute(sql, args)
    con.commit()
    con.close()

def execute_query(sql, *args):
    con = connect(DB_PATH)
    cur = con.cursor()
    cur.execute(sql, args)
    res = cur.fetchall()
    return res

def create_database():
    con = connect(DB_PATH)
    cur = con.cursor()
    with open(SCHEMA_PATH) as fp:
        cur.executescript(fp.read())
    con.commit()
    con.close()
    return "Database created successfully"

def add_user(username, password, pepper):
    password_hash, password_salt = generate_hash_and_salt(password, pepper)
    # "?" is used to prevent SQL injections
    execute_action("INSERT INTO Users (Username, PasswordHash, PasswordSalt, DateCreated) VALUES (?, ?, ?, ?);",
                   username, password_hash, password_salt, datetime.today().strftime('%Y-%m-%d'))
    execute_action("INSERT INTO UserStatistics (Username, GamesPlayed, TotalTokens, TotalWins, TotalLosses) " +
                   "VALUES (?, ?, ?, ?, ?);",
                   username, 0, 0, 0, 0)
    return f"User '{username}' added successfully"

def get_user_statistics(username):
    res = execute_query("SELECT GamesPlayed, TotalTokens, TotalWins, TotalLosses FROM UserStatistics " +
                        "WHERE Username = ?;", username)
    # User statistics are returned as a tuple
    return res[0]

def update_user_statistics(username, score, winner):
    current_statistics = get_user_statistics(username)
    games_played, total_tokens = current_statistics[0] + 1, current_statistics[1] + score
    total_wins, total_losses = current_statistics[2] + winner, current_statistics[3] + (not winner)
    execute_action("UPDATE UserStatistics SET GamesPlayed = ?, TotalTokens = ?, TotalWins = ?, " +
                   "TotalLosses = ? WHERE Username = ?;",
                   games_played, total_tokens, total_wins, total_losses, username)
    return "User Statistics updated successfully"

def check_username_exists(username):
    res = execute_query("SELECT 0 FROM Users WHERE Username = ?;", username)
    return len(res) > 0

def get_date_user_created(username):
    res = execute_query("SELECT DateCreated FROM Users WHERE Username = ?;", username)
    return res[0][0]

def get_hash_and_salt(username):
    res = execute_query("SELECT PasswordHash, PasswordSalt FROM Users WHERE Username = ?;", username)
    return res[0]

def create_custom_questions(username, questions_json):
    date = datetime.today().strftime('%Y-%m-%d')
    for question in questions_json["questions"]:
        execute_action("INSERT INTO CustomQuestions (Username, QuestionText, DateCreated) VALUES (?, ?, ?);",
                       username, question, date)
    return f"Custom questions added to user '{username}' successfully"

def reset_custom_questions(username):
    execute_action("DELETE FROM CustomQuestions WHERE Username = ?;", username)
    return f"All custom questions belonging to user '{username}' deleted successfully"

def get_custom_questions(username):
    res = execute_query("SELECT QuestionText FROM CustomQuestions WHERE Username = ?;", username)
    return res

def delete_user(username):
    execute_action("DELETE FROM Users WHERE Username = ?;", username)
    execute_action("DELETE FROM UserStatistics WHERE Username = ?;", username)
    execute_action("DELETE FROM CustomQuestions WHERE Username = ?;", username)
    return f"User '{username}' deleted successfully"