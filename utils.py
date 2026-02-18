import os
import random
import hashlib
import hmac
from requests import post
import json
import re

class RecaptchaManager:
    def __init__(self, secret_key):
        self.__secret_key = secret_key

    def is_human(self, captcha_response):
        # Sends data to Google
        data = {'response': captcha_response, 'secret': self.__secret_key}
        response = post("https://www.google.com/recaptcha/api/siteverify", data=data, timeout=10)
        # Returns formatted response
        return json.loads(response.text)['success']

class PasswordManager:
    @staticmethod
    def validate_password(username, password):
        if not password:
            return "Please enter a password"
        if len(password) < 7:
            return "Password must be more than 6 characters"
        if password == username:
            return "Password cannot be the same as username"
        if not re.search(r'\d', password):
            return "Password must contain a digit"
        if not re.search(r'[A-Za-z]', password):
            return "Password must contain a letter"
        return None

    @staticmethod
    def generate_hash_and_salt(text, pepper):
        # Salting improves security - for example, attackers cannot use rainbow tables
        salt = os.urandom(16) # "urandom" ensures cryptographic randomness
        text_bin, pepper_bin = text.encode(), pepper.encode()
        new_hash = hashlib.pbkdf2_hmac('sha256', text_bin + pepper_bin, salt, 200_000)
        return new_hash, salt

    @staticmethod
    def check_hash_match(text, hash_salt, pepper):
        hashed_text, salt = hash_salt[0], hash_salt[1]
        text_bin, pepper_bin = text.encode(), pepper.encode()
        new_hash = hashlib.pbkdf2_hmac('sha256', text_bin + pepper_bin, salt, 200_000)
        return hmac.compare_digest(new_hash, hashed_text)

class GameManager:
    def __init__(self, questions):
        self.__questions = questions

    @staticmethod
    def select_random_member(members):
        return random.choice(members)

    def select_random_question(self):
        return random.choice(self.__questions)

    @staticmethod
    def automatically_match_responses(responses):
        matched_responses = {}
        for user, response in responses.items():
            key = response.lower().strip()
            if key in matched_responses:
                matched_responses[key].append((user, response))
            else:
                matched_responses[key] = [(user, response)]
        return matched_responses

    @staticmethod
    def calculate_results(matched_responses):
        scores = {}
        pink_cow_token = None
        max_length = 0
        longest_groups = []
        for group in matched_responses.values():
            if len(group) == 1:
                if pink_cow_token is None:
                    pink_cow_token = group[0][0]
                else:
                    pink_cow_token = None
            if len(group) > max_length:
                max_length = len(group)
                longest_groups = [group]
            elif len(group) == max_length:
                longest_groups.append(group)
        if len(longest_groups) == 1 and max_length > 1:
            for response in longest_groups[0]:
                scores[response[0]] = 1
        return scores, pink_cow_token

    @staticmethod
    def select_cattle_wrangler(members, current_cattle_wrangler):
        # Remove current cattle wrangler from the pool of possible cattle wranglers for the next round
        if current_cattle_wrangler in members:
            members.remove(current_cattle_wrangler)
        return GameManager.select_random_member(members)

    @staticmethod
    def check_winners(scores):
        winners = []
        for member in scores:
            if scores[member] >= 8:
                winners.append(member)
        if winners:
            return winners
        else:
            return None