# Slack Leak

Slack Leak scans all Slack public and private channels for sensitive information such as credit cards, API tokens, private keys, passwords and creating Jira tickets

### Requirements

* Slack Bot Token
* Jira API credentials 

Install packages

`pip install python-dotenv slack_sdk requests`


* Slack Bot Token Permissions
  
channels:history

channels:read

files:read

groups:history

groups:read

im:history

im:read

links:read

mpim:history

mpim:read

remote_files:read

search:read

team:read

users:read

users:read.email


* Create a .env file

`SLACK_BOT_TOKEN=xoxb-your-slack-bot-token`

`JIRA_URL=https://yourcompany.atlassian.net`

`JIRA_USER=your-email@example.com`

`JIRA_API_TOKEN=your-jira-api-token`

`JIRA_PROJECT_KEY=PROJECT`


* Run the script in a Docker container, Kubernetes pod, or virtual machine

# Jira ticket example

![image](https://github.com/user-attachments/assets/426ecc75-5374-47af-a48a-5a32504ea98d)

![image](https://github.com/user-attachments/assets/63329bab-4ffd-40b7-8105-d9945bde57b4)



