import os
import random
import hashlib
import hmac
import json
from string import ascii_uppercase

def generate_unique_code(length, rooms):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code

# NOTE: Implement rules for passwords LAST to make testing easier
# TODO: Make sure that the password is not equal to the username
# TODO: Create rules for generating passwords: must contain letters and numbers, >6 characters (disable during testing)

def generate_hash_and_salt(text, pepper):
    # Salting improves security - for example, attackers cannot use rainbow tables
    salt = os.urandom(16) # "urandom" ensures cryptographic randomness
    text_bin, pepper_bin = text.encode(), pepper.encode()
    new_hash = hashlib.pbkdf2_hmac('sha256', text_bin + pepper_bin, salt, 200_000)
    return new_hash, salt

def check_hash_match(text, hash_salt, pepper):
    hashed_text, salt = hash_salt[0], hash_salt[1]
    text_bin, pepper_bin = text.encode(), pepper.encode()
    new_hash = hashlib.pbkdf2_hmac('sha256', text_bin + pepper_bin, salt, 200_000)
    return hmac.compare_digest(new_hash, hashed_text)

def select_random_member(members):
    return random.choice(members)

def select_random_question():
    with open("questions.json", "r") as file:
        questions_file = json.load(file)
    return random.choice(questions_file["questions"])

def automatically_match_responses(responses):
    matched_responses = {}
    for user, response in responses.items():
        key = response.lower().strip()
        if key in matched_responses:
            matched_responses[key].append((user, response))
        else:
            matched_responses[key] = [(user, response)]
    return matched_responses

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

def select_cattle_wrangler(members, current_cattle_wrangler):
    # Remove current cattle wrangler from the pool of possible cattle wranglers for the next round
    members.remove(current_cattle_wrangler)
    return select_random_member(members)

def check_winners(scores):
    winners = []
    for member in scores:
        if scores[member] >= 8:
            winners.append(member)
    if winners:
        return winners
    else:
        return None