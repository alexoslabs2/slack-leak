# Slack Leak - Extended with Confluence and Jira Scanning

Slack Leak scans Slack channels, Atlassian Confluence spaces, and Jira issues for sensitive information such as credit cards, API tokens, private keys, passwords, and creates Jira tickets for detected sensitive data.

## Features

- **Slack Scanning**: Scans all public and private Slack channels for sensitive data
- **Confluence Scanning**: Scans all accessible Confluence spaces and pages for sensitive information
- **Jira Content Scanning**: Scans Jira issues and comments for sensitive data
- **Automated Alerting**: Creates Jira tickets when sensitive data is detected
- **Comprehensive Pattern Detection**: Detects various types of sensitive data including:
  - Credit card numbers
  - API tokens (GitHub, AWS, Azure, Atlassian, etc.)
  - Private keys (RSA, SSH, etc.)
  - Passwords and secrets
  - Database connection strings
  - Internal URLs and IP addresses
  - Personal information (emails, phone numbers, SSNs)

### Requirements

* Python 3.7+
* Slack Bot Token (for Slack scanning)
* Jira API credentials (for creating alerts and scanning Jira content)
* Confluence API credentials (for Confluence scanning)

Install packages

`pip install python-dotenv slack_sdk requests`

### Slack Bot Token Permissions

For Slack scanning, your bot token needs the following permissions:

- channels:history
- channels:read
- files:read
- groups:history
- groups:read
- im:history
- im:read
- links:read
- mpim:history
- mpim:read
- remote_files:read
- search:read
- team:read
- users:read
- users:read.email

### Environment Configuration

Create a `.env` file with the following variables:

#### Required for Jira Alerting
```
JIRA_SERVER=https://yourcompany.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=PROJECT
```

#### Optional - Slack Scanning
```
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
```

#### Optional - Confluence Scanning
```
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-confluence-api-token
```

**Note**: You can use the same Atlassian credentials for both Jira and Confluence if they're on the same instance.

### API Token Generation

#### Atlassian API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label and click "Create"
4. Copy the token immediately (it won't be shown again)

#### Slack Bot Token
1. Go to https://api.slack.com/apps
2. Create a new app or select an existing one
3. Go to "OAuth & Permissions"
4. Add the required bot token scopes listed above
5. Install the app to your workspace
6. Copy the "Bot User OAuth Token"

### Usage

Run the script in a Docker container, Kubernetes pod, or virtual machine:

```bash
python slackleak.py
```

The script will:
1. Scan Slack channels (if configured)
2. Scan Confluence spaces and pages (if configured)
3. Scan recent Jira issues (if configured)
4. Create Jira tickets for any detected sensitive data

### Scanning Behavior

- **Slack**: Scans the last 100 messages in each channel
- **Confluence**: Scans all accessible spaces and their pages
- **Jira**: Scans issues updated in the last 30 days
- **Rate Limiting**: Includes delays between API calls to avoid rate limiting
- **Error Handling**: Gracefully handles API errors and continues scanning

### Customizing Patterns

Edit `patterns.json` to add, remove, or modify sensitive data detection patterns. Each pattern is a regular expression that will be matched against the content.

### Security Considerations

- Store API tokens securely using environment variables
- Use dedicated service accounts with minimal required permissions
- Regularly rotate API tokens
- Monitor the Jira project for sensitive data alerts
- Consider running in a secure, isolated environment

### Example Jira Ticket

When sensitive data is detected, a Jira ticket is created with:
- Summary indicating the source (Slack/Confluence/Jira) and location
- Description with the detected content type and location details
- Issue type set to "INCIDENT" (configurable in code)

![image](https://github.com/user-attachments/assets/63329bab-4ffd-40b7-8105-d9945bde57b4)



