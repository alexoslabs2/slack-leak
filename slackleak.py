import os
import re
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

slack_client = WebClient(token=SLACK_BOT_TOKEN)

SENSITIVE_PATTERNS = {
    "Credit Card": r"\b(?:\d[ -]*?){13,16}\b",
    "API Token1": r"(?i)(?:api[_-]?key|token|secret)[\s:]*([A-Za-z0-9-_.]{10,})",
    "API Token2": r"(?i)(?:user[_-]?key|token|secret)[\s:]*([A-Za-z0-9-_.]{10,})",
    "API Token3": r"\b[a-zA-Z0-9_-]{20,100}\b",
    "API Token4": r"\bAPI_KEY_[a-zA-Z0-9]{20,100}\b",
    "API Token5": r"\bBearer\s+[a-zA-Z0-9_-]{20,100}\b",
    "Private Key": r"-----BEGIN (RSA|DSA|EC|PRIVATE) KEY-----[\s\S]+?-----END (RSA|DSA|EC|PRIVATE) KEY-----",
    "Password1": r"(?i)(password|pass)[=:]\s*['\"]?([A-Za-z0-9@#\$%\^&\*\(\)_\+\-]+)['\"]?",
    "Password2": r"(?i)(password|passwd|pwd|pass)[\s:=]+[A-Za-z0-9@#$%^&+=*!?.]{6,}",
    "Password3": r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
    "Github API Token": r"gh[pous]_[A-Za-z0-9]{36,}",
    "Azure API Token": r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
}

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
