##################################################
## Slack Leak
##################################################
## Author: Alexos
## Alexos Core Labs
##################################################

import os
import re
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

slack_client = WebClient(token=SLACK_BOT_TOKEN)

class PatternLoader:
    def __init__(self, patterns_file="patterns.json"):
        self.patterns_file = patterns_file
        self.patterns = {}
        self.load_patterns()
    
    def load_patterns(self):
        try:
            if os.path.exists(self.patterns_file):
                with open(self.patterns_file, 'r') as f:
                    self.patterns = json.load(f)
            else:
                raise FileNotFoundError(f"Patterns file '{self.patterns_file}' not found.")
            
            
            for key, pattern in self.patterns.items():
                try:
                    re.compile(pattern)
                except re.error as e:
                    print(f"Warning: Invalid regex pattern for '{key}': {str(e)}")
                    
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in patterns file: {str(e)}")

    def reload_patterns(self):
       self.load_patterns()

pattern_loader = PatternLoader()
SENSITIVE_PATTERNS = pattern_loader.patterns

def scan_messages(channel_id, channel_name):
   
    try:
        response = slack_client.conversations_history(channel=channel_id, limit=100)
        if response.get("messages"):
            for message in response["messages"]:
                text = message.get("text", "")
                for label, pattern in SENSITIVE_PATTERNS.items():
                    if re.search(pattern, text):
                        send_jira_alert(channel_name, label, text)
    except SlackApiError as e:
        print(f"Error fetching messages for {channel_name}: {e.response['error']}")

def detect_sensitive_info(text):
    
    findings = []
    for key, pattern in SENSITIVE_PATTERNS.items():
        if re.search(pattern, text):
            findings.append(key)
    return findings

def send_jira_alert(channel_name, issue_type, message_text):
   
    jira_api_url = f"{JIRA_SERVER}/rest/api/2/issue"
    headers = {"Content-Type": "application/json"}
    auth = (JIRA_USERNAME, JIRA_API_TOKEN)

    issue_data = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": f"Sensitive Data Detected in Slack ({channel_name})",
            "description": f"A {issue_type} was detected in channel *{channel_name}*.\n\nDetected message:\n```{message_text}```",
            "issuetype": {"name": "INCIDENT"} #Change the issutype
        }
    }

    response = requests.post(jira_api_url, json=issue_data, headers=headers, auth=auth)
    if response.status_code == 201:
        print(f"Jira alert created for {issue_type} in {channel_name}")
    else:
        print(f"Failed to create Jira issue: {response.text}")

def main():

    try:
        channels_response = slack_client.conversations_list(types="public_channel,private_channel")
        if channels_response.get("channels"):
            for channel in channels_response["channels"]:
               scan_messages(channel["id"], channel["name"])
    except SlackApiError as e:
        print(f"Error fetching channels: {e.response['error']}")
if __name__ == "__main__":
    main()
