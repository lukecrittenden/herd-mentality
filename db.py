import os
from sqlite3 import *
from utils import PasswordManager
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        # Setting base directory so file path is independent of where python is run from
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.__schema_path = os.path.join(base_dir, "schema.sql")
        self.__db_path = os.path.join(base_dir, "users.db")

    def __execute_action(self, sql, *args):
        con = connect(self.__db_path)
        cur = con.cursor()
        cur.execute(sql, args)
        con.commit()
        con.close()

    def __execute_query(self, sql, *args):
        con = connect(self.__db_path)
        cur = con.cursor()
        cur.execute(sql, args)
        res = cur.fetchall()
        con.close()
        return res

    def create_database(self):
        con = connect(self.__db_path)
        cur = con.cursor()
        # Create database from schema
        with open(self.__schema_path) as fp:
            cur.executescript(fp.read())
        con.commit()
        con.close()
        return "Database created successfully"

    def add_user(self, username, password, pepper):
        password_hash, password_salt = PasswordManager.generate_hash_and_salt(password, pepper)
        # "?" is used to prevent SQL injections
        self.__execute_action("INSERT INTO Users (Username, PasswordHash, PasswordSalt, DateCreated)"
                              "VALUES (?, ?, ?, ?);", username, password_hash, password_salt,
                              datetime.today().strftime('%Y-%m-%d'))
        self.__execute_action("INSERT INTO UserStatistics (Username, GamesPlayed, TotalTokens, TotalWins,"
                              "TotalLosses) VALUES (?, ?, ?, ?, ?);",username, 0, 0, 0, 0)
        return f"User '{username}' added successfully"

    def get_user_statistics(self, username):
        res = self.__execute_query("SELECT GamesPlayed, TotalTokens, TotalWins, TotalLosses FROM UserStatistics "
                            "WHERE Username = ?;", username)
        # User statistics are returned as a tuple
        return res[0]

    def update_user_statistics(self, username, score, winner):
        current_statistics = self.get_user_statistics(username)
        games_played, total_tokens = current_statistics[0] + 1, current_statistics[1] + score
        total_wins, total_losses = current_statistics[2] + winner, current_statistics[3] + (not winner)
        self.__execute_action("UPDATE UserStatistics SET GamesPlayed = ?, TotalTokens = ?, TotalWins = ?, "
                       "TotalLosses = ? WHERE Username = ?;",
                       games_played, total_tokens, total_wins, total_losses, username)
        return "User Statistics updated successfully"

    def check_username_exists(self, username):
        res = self.__execute_query("SELECT 0 FROM Users WHERE Username = ?;", username)
        # Return True when the number of players with the username is greater than 0 (i.e. the username exists)
        return len(res) > 0

    def get_date_user_created(self, username):
        res = self.__execute_query("SELECT DateCreated FROM Users WHERE Username = ?;", username)
        return res[0][0]

    def get_hash_and_salt(self, username):
        res = self.__execute_query("SELECT PasswordHash, PasswordSalt FROM Users WHERE Username = ?;", username)
        return res[0]

    def create_custom_questions(self, username, questions_json):
        date = datetime.today().strftime('%Y-%m-%d')
        for question in questions_json["questions"]:
            self.__execute_action("INSERT INTO CustomQuestions (Username, QuestionText, DateCreated) VALUES (?, ?, ?);",
                           username, question, date)
        return f"Custom questions added to user '{username}' successfully"

    def reset_custom_questions(self, username):
        self.__execute_action("DELETE FROM CustomQuestions WHERE Username = ?;", username)
        return f"All custom questions belonging to user '{username}' deleted successfully"

    def get_custom_questions(self, username):
        res = self.__execute_query("SELECT QuestionText FROM CustomQuestions WHERE Username = ?;", username)
        return [row[0] for row in res]

    def delete_user(self, username):
        self.__execute_action("DELETE FROM Users WHERE Username = ?;", username)
        self.__execute_action("DELETE FROM UserStatistics WHERE Username = ?;", username)
        self.__execute_action("DELETE FROM CustomQuestions WHERE Username = ?;", username)
        return f"User '{username}' deleted successfully"