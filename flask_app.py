from os import path, getenv
from flask import Flask, flash, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, emit, SocketIO
from utils import *
from db import *
from dotenv import load_dotenv
from string import ascii_uppercase

class Server:
    def __init__(self, name, database_manager):
        # Stores rooms as key-value pairs: the key is the room code and the value is the room object
        self.__rooms = {}
        self.__app = Flask(name)
        self.__socketio = SocketIO(self.__app)
        # Sets keys for server
        load_dotenv()
        keys = ["SECRET_KEY", "PEPPER_KEY", "RECAPTCHA_SITE_KEY", "RECAPTCHA_SECRET_KEY"]
        for key in keys:
            self.__app.config[key] = getenv(key)
        # Secure app configurations
        self.__app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            MAX_CONTENT_LENGTH=1 * 1024 * 1024, # Limits file uploads to 1MB
            ROOM_CODE_LENGTH=4,
            MAX_MEMBERS=10
        )
        # Create manager objects
        self.__database_manager = database_manager
        self.__recaptcha_manager = RecaptchaManager(self.__app.config["RECAPTCHA_SECRET_KEY"])

        @self.__app.route("/", methods=["POST", "GET"])
        def home():
            # Check if signed in to an account
            if "user" in session:
                if "room" in session:
                    # Delete session key for room
                    session.pop("room")
                if request.method == "POST":
                    code = request.form.get("code").upper()
                    create = request.form.get("create", False) # If the value does not exist, create defaults to False
                    user = session.get("user")
                    error = None
                    if create == "":
                        # Create a new room
                        code = (Server.generate_unique_code(
                            self.__app.config["ROOM_CODE_LENGTH"], self.__rooms.keys()))
                        self.__rooms[code] = Room(user, code,
                                                  database_manager.get_custom_questions(session.get("user")))
                        self.__app.logger.info("Room created - Room " + code)
                    elif code == "":
                        error = "Please enter a room code"
                    elif code not in self.__rooms.keys():
                        error = "Room does not exist"
                    elif len(self.__rooms[code].get_members()) >= self.__app.config["MAX_MEMBERS"]:
                        error = "Room full"
                    if error:
                        return render_template("signed_in_home.html", error=error, code=code)
                    else:
                        session["room"] = code
                        return redirect(url_for("room"))

                return render_template("signed_in_home.html")
            else:
                return render_template("signed_out_home.html")

        @self.__app.route("/login", methods=["POST", "GET"])
        def login():
            session.clear()
            if request.method == "POST":
                error = None
                username = request.form.get("username")
                password = request.form.get("password")
                captcha_response = request.form['g-recaptcha-response']
                if not username:
                    error = "Please enter a username"
                elif not password:
                    error = "Please enter a password"
                # Checks that the user has completed the reCAPTCHA successfully
                elif not captcha_response or not self.__recaptcha_manager.is_human(captcha_response):
                    error = "Please complete the reCAPTCHA"
                elif self.__database_manager.check_username_exists(username):
                    # Check that users password matches the password stored in the database as a hash
                    pepper = self.__app.config["PEPPER_KEY"]
                    if PasswordManager.check_hash_match(password, self.__database_manager.get_hash_and_salt(username),
                                                        pepper):
                        session["user"] = username
                    else:
                       error = "Password or username is incorrect"
                else:
                    error = "Password or username is incorrect"
                if error:
                    # Logs IP address and error
                    self.__app.logger.info(f"{request.remote_addr} - {error}")
                    return render_template("account/login.html", error=error, username=username,
                                           password=password, site_key=self.__app.config["RECAPTCHA_SITE_KEY"])
                else:
                    return redirect(url_for("home"))
            return render_template("account/login.html",
                                   site_key=self.__app.config["RECAPTCHA_SITE_KEY"])

        @self.__app.route("/register", methods=["POST", "GET"])
        def register():
            session.clear()
            if request.method == "POST":
                username = request.form.get("username")
                password = request.form.get("password")
                captcha_response = request.form['g-recaptcha-response']
                if not username:
                    error = "Please enter a username"
                elif self.__database_manager.check_username_exists(username):
                    error = "Account with that username already exists"
                else:
                    error = PasswordManager.validate_password(username, password)
                    if not error:
                        if not captcha_response or not self.__recaptcha_manager.is_human(captcha_response):
                            error = "Please complete the reCAPTCHA"
                if error:
                    # Logs IP address and error
                    self.__app.logger.info(f"{request.remote_addr} - {error}")
                    return render_template("account/register.html", username=username,
                                           password=password, error=error,
                                           site_key=self.__app.config["RECAPTCHA_SITE_KEY"])
                else:
                    # Add user and log message if user created successfully
                    pepper = self.__app.config["PEPPER_KEY"]
                    self.__app.logger.info(self.__database_manager.add_user(username, password, pepper))
                    return redirect(url_for("home"))
            return render_template("account/register.html",
                                   site_key=self.__app.config["RECAPTCHA_SITE_KEY"])

        @self.__app.route("/account", methods=["POST", "GET"])
        def account():
            if "user" in session:
                if request.method == "POST":
                    if request.form["submit-button"] == "upload-custom-questions":
                        return redirect(url_for("custom_questions"))
                    elif request.form["submit-button"] == "log-out":
                        # Clearing the session removes "user" from the session, logging out the user
                        session.clear()
                    elif request.form["submit-button"] == "delete":
                        # Deletes user from database and logs response
                        self.__app.logger.info(self.__database_manager.delete_user(session.get("user")))
                        session.clear()
                    return redirect(url_for("home"))
                user_statistics = self.__database_manager.get_user_statistics(session.get("user"))
                if user_statistics[2] + user_statistics[3] == 0:
                    # If no wins or losses, add "N/A" to tuple to avoid divide by 0 error
                    user_statistics += ("N/A",)
                else:
                    # Add W/L ratio to user_statistics tuple
                    user_statistics += ((user_statistics[2]/(user_statistics[2] + user_statistics[3])) * 100,)
                date_created = self.__database_manager.get_date_user_created(session.get("user"))
                return render_template("account/account.html",  user=session.get("user"),
                                       account_created=date_created,
                                       user_statistics=user_statistics)
            else:
                return redirect(url_for("home"))

        @self.__app.route("/custom-questions", methods=["POST", "GET"])
        def custom_questions():
            if "user" in session:
                if request.method == "POST":
                    # Documentation: https://flask.palletsprojects.com/en/stable/patterns/fileuploads/
                    if request.form["submit-button"] == "upload":
                        # Check if the post request has the file part
                        if "file" not in request.files:
                            flash("No file part")
                            return redirect(request.url)
                        file = request.files["file"]
                        # If the user does not select a file, the browser submits an empty file without a filename
                        if file.filename == "":
                            flash("No selected file")
                            return redirect(request.url)
                        if file and file.filename.endswith(".json"):
                            try:
                                # Load custom json file
                                questions_json = json.load(file)
                                # Add custom questions to database and log result
                                self.__app.logger.info(
                                    self.__database_manager.create_custom_questions(session.get("user"),questions_json))
                            except json.JSONDecodeError:
                                flash("Uploaded file is not valid JSON")
                                return redirect(request.url)
                    elif request.form["submit-button"] == "reset":
                        # Reset questions belonging to the user and log the result
                        self.__app.logger.info(
                            self.__database_manager.reset_custom_questions(session.get("user")))
                    return redirect(url_for("home"))
                return render_template("custom_questions.html")
            else:
                return redirect(url_for("home"))

        @self.__app.route("/room", methods=["POST", "GET"])
        def room():
            # If the user is not signed in or the remove does not exist, the user is returned to the homepage
            if session.get("user") is None or session.get("room") not in self.__rooms.keys():
                return redirect(url_for("home"))
            room = self.__rooms[session.get("room")]
            return render_template("room.html", code=session.get("room"), stage=room.get_stage(),
                                   user=session.get("user"), time_per_question=room.get_time_per_question(),
                                   host=room.get_host(), messages=room.get_messages())

        # Join room from link (requires user to be signed in)
        @self.__app.route("/room/<code>")
        def room_link(code):
            session["room"] = code
            return redirect(url_for("room"))

        @self.__app.route("/rules")
        def rules():
            return render_template("rules.html")

        @self.__socketio.on("message")
        def message(data):
            # If room exists
            if session.get("room") in self.__rooms.keys():
                # Adds message to room
                self.__rooms[session.get("room")].add_message(data["data"], session.get("user"))
            else:
                return redirect(url_for("room"))

        @self.__socketio.on("connect")
        def connect():
            # If room of user not in session
            if not session.get("room") or not session.get("user"):
                # Redirect user home
                return redirect(url_for("home"))
            # If room does not exist
            if session.get("room") not in self.__rooms.keys():
                leave_room(session.get("room"))
                return redirect(url_for("home"))
            # Add the user to the room
            join_room(session.get("room"))
            room = self.__rooms[session.get("room")]
            room.add_member(session.get("user"))
            room.load_previous_messages()

        @self.__socketio.on("disconnect")
        def disconnect():
            if session.get("room") in self.__rooms.keys():
                self.__rooms[session.get("room")].remove_member(session.get("user"))
                self.__delete_room_if_empty(session.get("room"))

        @self.__socketio.on("kick-user")
        def kick_member(user):
            if session.get("room") in self.__rooms.keys():
                self.__rooms[session.get("room")].kick_member(user)

        @self.__socketio.on("start-game")
        def start_game():
            self.__app.logger.info("Game started - Room " + session.get("room"))
            self.__rooms[session.get("room")].start_game()

        @self.__socketio.on("end-game")
        def end_game():
            self.__app.logger.info("Game ended - Room " + session.get("room"))
            self.__rooms[session.get("room")].end_game()

        @self.__socketio.on("answer-question")
        def answer_question(user, response):
            self.__rooms[session.get("room")].answer_question(user, response)

        @self.__socketio.on("change-time-per-question")
        def change_time_per_question():
            self.__rooms[session.get("room")].change_time_per_question()

        @self.__socketio.on("match-responses")
        def match_responses():
            self.__rooms[session.get("room")].match_responses()

        @self.__socketio.on("next-question")
        def next_question():
            self.__rooms[session.get("room")].next_question()

        @self.__socketio.on("submit-matched-responses")
        def submit_matched_responses(matched_responses):
            self.__rooms[session.get("room")].submit_matched_responses(matched_responses, self.__database_manager)

    @staticmethod
    def generate_unique_code(length, room_keys):
        # Creates a random fixed-length string of uppercase characters
        while True:
            code = ""
            for _ in range(length):
                code += random.choice(ascii_uppercase)
            if code not in room_keys:
                # If code does already exist in rooms
                break
        return code

    def __delete_room_if_empty(self, code):
        # If room has no members
        if not self.__rooms[code].get_members():
            self.__app.logger.info("Room deleted - Room " + code)
            del self.__rooms[code]

    def run(self, host, port, debug):
        self.__app.run(host=host, port=port, debug=debug)


class Room:
    def __init__(self, host, code, custom_questions):
        # Initialise room settings
        self.__code = code
        self.__members = []
        self.__messages = []
        self.__host = host
        # Time is in seconds
        self.__time_per_question = 10
        # The stages of the game are: lobby, questions, match_responses, final_results
        self.__stage = "lobby"
        self.__cattle_wrangler = None
        self.__pink_cow_token = None
        self.__winners = None
        self.__questions = []
        with open("questions.json", "r") as file:
            questions_json = json.load(file)
        for question in questions_json["questions"]:
            self.__questions.append(question)
        for question in custom_questions:
            self.__questions.append(question)
        self.__game_manager = GameManager(self.__questions)

    def __refresh_users_list(self):
        users_list = []
        for member in self.__members:
            users_list.append(member.get_user())
        # Users list must be cleared before any new users are added
        emit("clear-users-list", to=self.__code)
        emit("add-users", users_list, to=self.__code)

    def __all_users_responded(self):
        for member in self.__members:
            # When a user does not have a response, return False
            if member.get_response() is None:
                return False
        return True

    def __reset_scores(self):
        for member in self.__members:
            member.reset_score()

    def __reset_responses(self):
        for member in self.__members:
            member.set_response(None)

    def add_message(self, message, user):
        chat_message = {
            "user": user,
            "message": message
        }
        emit("message", chat_message, to=self.__code)
        self.__messages.append(chat_message)
        self.__refresh_users_list()

    def load_previous_messages(self):
        for message in self.__messages:
            chat_message = {
                "user": message["user"],
                "message": message["message"]
            }
            emit("message", chat_message, to=self.__code)

    def add_member(self, user):
        self.__members.append(Player(user))
        emit("message", user + " has entered the room", to=self.__code)
        self.__refresh_users_list()

    def remove_member(self, user):
        emit("message", user + " has left the room", to=self.__code)
        for member in self.__members:
            if member.get_user() == user:
                self.__members.remove(member)
                leave_room(session.get("room"))
        # If the host leaves the room while other users are in it, a user is randomly assigned as the host
        if self.__host == user and len(self.__members) != 0:
            self.__host = GameManager.select_random_member(self.__members).get_user()
            emit("message", self.__host + " is now the host", to=self.__code)
            emit("update-host", self.__host, to=self.__code)
        self.__refresh_users_list()

    def kick_member(self, user):
        emit("kick-user", user, to=self.__code)

    def start_game(self):
        # A minimum of 3 players is required to start a game
        if len(self.__members) >= 3:
            # If stage has changed, display game start message and questions
            if self.__stage != "questions":
                self.__stage = "questions"
                self.__cattle_wrangler = GameManager.select_random_member(self.__members)
                self.__reset_scores()
                self.__reset_responses()
                self.__winners = None
                emit("message", "GAME STARTED", to=self.__code)
                emit("update-scores", [self.__get_all_scores(), self.__pink_cow_token], to=self.__code)
                self.next_question()
                self.__refresh_users_list()
        else:
            emit("message", "3 or more players needed to start the game!", to=self.__code)

    def end_game(self):
        self.__stage = "lobby"
        emit("message", "GAME ENDED", to=self.__code)
        emit("lobby", to=self.__code)
        self.load_previous_messages()

    def answer_question(self, user, response):
        for member in self.__members:
            if member.get_user() == user:
                member.set_response(response)
        if self.__all_users_responded():
            emit("all-users-responded", to=self.__code)

    def change_time_per_question(self):
        if self.__time_per_question == 10:
            self.__time_per_question = 20
        elif self.__time_per_question == 20:
            self.__time_per_question = 30
        else:
            self.__time_per_question = 10
        emit("change-time-per-question", self.__time_per_question, to=self.__code)
        # Reload previous messages: otherwise they will be reset by room refresh
        self.load_previous_messages()

    def match_responses(self):
        responses = self.__get_all_responses()
        if responses == {}:
            self.next_question(no_responses=True)
        else:
            # The copy function ensures that the function does not mutate the original members list
            self.__cattle_wrangler = GameManager.select_cattle_wrangler(self.__members.copy(), self.__cattle_wrangler)
            self.__stage = "match_responses"
            matched_responses = GameManager.automatically_match_responses(responses)
            emit("match-responses", [responses, matched_responses, self.__cattle_wrangler.get_user()],
                 to=self.__code)

    def next_question(self, no_responses=False):
        emit("questions", [self.__game_manager.select_random_question(self.__questions), no_responses],
             to=self.__code)
        self.__reset_responses()

    def submit_matched_responses(self, matched_responses, database_manager):
        round_results, self.__pink_cow_token = GameManager.calculate_results(matched_responses)
        for username in round_results:
            for member in self.__members:
                if username == member.get_user():
                    member.add_score(round_results[username])
        scores = self.__get_all_scores()
        emit("update-scores", [scores, self.__pink_cow_token], to=self.__code)
        self.__refresh_users_list()
        self.__winners = GameManager.check_winners(scores)
        if self.__winners:
            self.__stage = "final_results"
            emit("final-results", [scores, self.__winners], to=self.__code)
            for member in self.__members:
                if member.get_user() in self.__winners:
                    winner = True
                else:
                    winner = False
                database_manager.update_user_statistics(member.get_user(), member.get_score(), winner)
        else:
            self.next_question()

    def get_code(self):
        return self.__code

    def get_members(self):
        return self.__members

    def get_messages(self):
        return self.__messages

    def get_host(self):
        return self.__host

    def get_time_per_question(self):
        return self.__time_per_question

    def get_stage(self):
        return self.__stage

    def __get_all_scores(self):
        scores = {}
        for member in self.__members:
            scores[member.get_user()] = member.get_score()
        return scores

    def __get_all_responses(self):
        responses = {}
        for member in self.__members:
            if member.get_response():
                responses[member.get_user()] = member.get_response()
        return responses


class Member:
    def __init__(self, username):
        self.__username = username

    def get_user(self):
        return self.__username


class Player(Member):
    def __init__(self, username):
        super().__init__(username)
        self.__score = 0
        self.__response = None

    def get_response(self):
        return self.__response

    def get_score(self):
        return self.__score

    def add_score(self, value):
        # Value must be int
        if isinstance(value, int):
            self.__score += value
        else:
            raise ValueError("Score must be an integer")

    def reset_score(self):
        self.__score = 0

    def set_response(self, value):
        # Response must be string or None
        if isinstance(value, (str, type(None))):
            self.__response = value
        else:
            raise ValueError("Response must be a string")


def main():
    database_manager = DatabaseManager()
    if not path.exists("users.db"):
        print(database_manager.create_database())
    server = Server(__name__, database_manager)
    server.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == "__main__":
    main()