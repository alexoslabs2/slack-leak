##################################################
## Slack Leak - Extended with Confluence and Jira Scanning
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
import base64
from datetime import datetime, timedelta
import time

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# Confluence specific environment variables
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")

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

class ConfluenceScanner:
    """Scanner for Atlassian Confluence spaces and pages"""
    
    def __init__(self, base_url, username, api_token):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.session = requests.Session()
        self.session.auth = (username, api_token)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def get_spaces(self, limit=50):
        """Get all accessible Confluence spaces"""
        try:
            url = f"{self.base_url}/rest/api/space"
            params = {'limit': limit, 'expand': 'description.plain'}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            spaces = response.json().get('results', [])
            print(f"Found {len(spaces)} Confluence spaces")
            return spaces
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Confluence spaces: {e}")
            return []
    
    def get_pages_in_space(self, space_key, limit=100):
        """Get all pages in a specific Confluence space"""
        try:
            url = f"{self.base_url}/rest/api/space/{space_key}/content"
            params = {
                'limit': limit,
                'expand': 'body.storage,version,space'
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            pages = response.json().get('results', [])
            print(f"Found {len(pages)} pages in space '{space_key}'")
            return pages
        except requests.exceptions.RequestException as e:
            print(f"Error fetching pages from space {space_key}: {e}")
            return []
    
    def get_page_content(self, page_id):
        """Get detailed content of a specific page"""
        try:
            url = f"{self.base_url}/rest/api/content/{page_id}"
            params = {'expand': 'body.storage,space,version'}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page content {page_id}: {e}")
            return None
    
    def scan_page_for_sensitive_data(self, page, patterns):
        """Scan a Confluence page for sensitive data"""
        findings = []
        
        # Extract text content from page
        page_title = page.get('title', '')
        page_body = ''
        
        if 'body' in page and 'storage' in page['body']:
            page_body = page['body']['storage'].get('value', '')
            # Remove HTML tags for text analysis
            page_body = re.sub(r'<[^>]+>', ' ', page_body)
        
        # Combine title and body for scanning
        full_content = f"{page_title} {page_body}"
        
        # Check against all patterns
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, full_content, re.IGNORECASE | re.MULTILINE)
            if matches:
                findings.append({
                    'type': pattern_name,
                    'page_id': page.get('id'),
                    'page_title': page_title,
                    'space_key': page.get('space', {}).get('key', ''),
                    'matches': matches[:5],  # Limit to first 5 matches
                    'url': f"{self.base_url}/pages/viewpage.action?pageId={page.get('id')}"
                })
        
        return findings
    
    def scan_all_spaces(self, patterns):
        """Scan all accessible Confluence spaces for sensitive data"""
        all_findings = []
        spaces = self.get_spaces()
        
        for space in spaces:
            space_key = space.get('key')
            print(f"Scanning Confluence space: {space_key}")
            
            pages = self.get_pages_in_space(space_key)
            
            for page in pages:
                findings = self.scan_page_for_sensitive_data(page, patterns)
                all_findings.extend(findings)
                
                # Add delay to avoid rate limiting
                time.sleep(0.1)
        
        return all_findings

class JiraScanner:
    """Scanner for Atlassian Jira issues and comments"""
    
    def __init__(self, base_url, username, api_token):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.session = requests.Session()
        self.session.auth = (username, api_token)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def get_projects(self):
        """Get all accessible Jira projects"""
        try:
            url = f"{self.base_url}/rest/api/2/project"
            response = self.session.get(url)
            response.raise_for_status()
            
            projects = response.json()
            print(f"Found {len(projects)} Jira projects")
            return projects
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Jira projects: {e}")
            return []
    
    def search_issues(self, jql, max_results=100):
        """Search for Jira issues using JQL"""
        try:
            url = f"{self.base_url}/rest/api/2/search"
            params = {
                'jql': jql,
                'maxResults': max_results,
                'expand': 'changelog',
                'fields': 'summary,description,comment,project,issuetype,status,created,updated'
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            issues = result.get('issues', [])
            print(f"Found {len(issues)} Jira issues")
            return issues
        except requests.exceptions.RequestException as e:
            print(f"Error searching Jira issues: {e}")
            return []
    
    def get_issue_comments(self, issue_key):
        """Get all comments for a specific Jira issue"""
        try:
            url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment"
            response = self.session.get(url)
            response.raise_for_status()
            
            comments = response.json().get('comments', [])
            return comments
        except requests.exceptions.RequestException as e:
            print(f"Error fetching comments for issue {issue_key}: {e}")
            return []
    
    def scan_issue_for_sensitive_data(self, issue, patterns):
        """Scan a Jira issue for sensitive data"""
        findings = []
        
        # Extract text content from issue
        issue_key = issue.get('key', '')
        fields = issue.get('fields', {})
        
        summary = fields.get('summary', '')
        description = fields.get('description', '') or ''
        
        # Get comments
        comments_text = ''
        if 'comment' in fields and 'comments' in fields['comment']:
            for comment in fields['comment']['comments']:
                comments_text += f" {comment.get('body', '')}"
        
        # Combine all text content
        full_content = f"{summary} {description} {comments_text}"
        
        # Check against all patterns
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, full_content, re.IGNORECASE | re.MULTILINE)
            if matches:
                findings.append({
                    'type': pattern_name,
                    'issue_key': issue_key,
                    'issue_summary': summary,
                    'project_key': fields.get('project', {}).get('key', ''),
                    'matches': matches[:5],  # Limit to first 5 matches
                    'url': f"{self.base_url}/browse/{issue_key}"
                })
        
        return findings
    
    def scan_recent_issues(self, patterns, days_back=30):
        """Scan recent Jira issues for sensitive data"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        jql = f"updated >= '{start_date.strftime('%Y-%m-%d')}'"
        
        print(f"Scanning Jira issues updated in the last {days_back} days")
        issues = self.search_issues(jql)
        
        all_findings = []
        for issue in issues:
            findings = self.scan_issue_for_sensitive_data(issue, patterns)
            all_findings.extend(findings)
            
            # Add delay to avoid rate limiting
            time.sleep(0.1)
        
        return all_findings
    
    def scan_project_issues(self, project_key, patterns, max_results=100):
        """Scan all issues in a specific project"""
        jql = f"project = {project_key}"
        
        print(f"Scanning Jira project: {project_key}")
        issues = self.search_issues(jql, max_results)
        
        all_findings = []
        for issue in issues:
            findings = self.scan_issue_for_sensitive_data(issue, patterns)
            all_findings.extend(findings)
            
            # Add delay to avoid rate limiting
            time.sleep(0.1)
        
        return all_findings

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
                        send_jira_alert(channel_name, label, text, "Slack")
    except SlackApiError as e:
        print(f"Error fetching messages for {channel_name}: {e.response['error']}")

def detect_sensitive_info(text):
    
    findings = []
    for key, pattern in SENSITIVE_PATTERNS.items():
        if re.search(pattern, text):
            findings.append(key)
    return findings

def send_jira_alert(location, issue_type, content, source_type="Slack"):
    """Send Jira alert for detected sensitive data"""
    jira_api_url = f"{JIRA_SERVER}/rest/api/2/issue"
    headers = {"Content-Type": "application/json"}
    auth = (JIRA_USERNAME, JIRA_API_TOKEN)

    # Truncate content if too long
    if len(content) > 1000:
        content = content[:1000] + "... [truncated]"

    issue_data = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": f"Sensitive Data Detected in {source_type} ({location})",
            "description": f"A {issue_type} was detected in {source_type} location: *{location}*.\n\nDetected content:\n```{content}```",
            "issuetype": {"name": "INCIDENT"} #Change the issuetype
        }
    }

    response = requests.post(jira_api_url, json=issue_data, headers=headers, auth=auth)
    if response.status_code == 201:
        print(f"Jira alert created for {issue_type} in {source_type}: {location}")
    else:
        print(f"Failed to create Jira issue: {response.text}")

def scan_confluence():
    """Scan Confluence for sensitive data"""
    if not all([CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN]):
        print("Confluence credentials not configured. Skipping Confluence scan.")
        return
    
    print("Starting Confluence scan...")
    confluence_scanner = ConfluenceScanner(CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
    
    findings = confluence_scanner.scan_all_spaces(SENSITIVE_PATTERNS)
    
    # Create Jira alerts for findings
    for finding in findings:
        location = f"{finding['space_key']}/{finding['page_title']}"
        content = f"Page: {finding['page_title']}\nURL: {finding['url']}\nMatches: {finding['matches']}"
        send_jira_alert(location, finding['type'], content, "Confluence")
    
    print(f"Confluence scan completed. Found {len(findings)} sensitive data instances.")

def scan_jira_content():
    """Scan Jira issues for sensitive data"""
    if not all([JIRA_SERVER, JIRA_USERNAME, JIRA_API_TOKEN]):
        print("Jira credentials not configured. Skipping Jira content scan.")
        return
    
    print("Starting Jira content scan...")
    jira_scanner = JiraScanner(JIRA_SERVER, JIRA_USERNAME, JIRA_API_TOKEN)
    
    # Scan recent issues (last 30 days)
    findings = jira_scanner.scan_recent_issues(SENSITIVE_PATTERNS, days_back=30)
    
    # Create Jira alerts for findings (only if different project or self-reporting is desired)
    for finding in findings:
        location = f"{finding['project_key']}/{finding['issue_key']}"
        content = f"Issue: {finding['issue_summary']}\nURL: {finding['url']}\nMatches: {finding['matches']}"
        send_jira_alert(location, finding['type'], content, "Jira")
    
    print(f"Jira content scan completed. Found {len(findings)} sensitive data instances.")

def scan_slack():
    """Scan Slack channels for sensitive data"""
    if not SLACK_BOT_TOKEN:
        print("Slack bot token not configured. Skipping Slack scan.")
        return
    
    print("Starting Slack scan...")
    try:
        channels_response = slack_client.conversations_list(types="public_channel,private_channel")
        if channels_response.get("channels"):
            for channel in channels_response["channels"]:
               scan_messages(channel["id"], channel["name"])
    except SlackApiError as e:
        print(f"Error fetching channels: {e.response['error']}")
    
    print("Slack scan completed.")

def main():
    """Main function to run all scans"""
    print("=== Starting Sensitive Data Scan ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Run all scans
    scan_slack()
    scan_confluence()
    scan_jira_content()
    
    print("=== All scans completed ===")

if __name__ == "__main__":
    main()
