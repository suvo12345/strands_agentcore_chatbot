# Run the AgentCore chat client

These steps run `invoke_chat_agent.py` on a new computer and connect it to an **already-deployed** Amazon Bedrock AgentCore Runtime. They do not deploy the agent.

## 1. Get the client

Clone the GitHub repository and move into its directory:

```bash
git clone <repository-url>
cd <repository-directory>
```

Only `invoke_chat_agent.py` is needed from the repository to run the chat client. The agent source and CDK files are needed to develop or deploy the Runtime, not to invoke an existing one.

## 2. Install Python dependencies

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the packages used by the client:

```bash
python -m pip install boto3 python-dotenv
```

## 3. Configure AWS access

Authenticate using your organization's approved AWS method. For an AWS CLI profile, for example:

```bash
aws configure
aws sts get-caller-identity
```

For an IAM Identity Center profile, use its configured profile and sign in:

```bash
aws sso login --profile <profile-name>
```

The active AWS identity needs permission to invoke the deployed AgentCore Runtime. Runtime auto-discovery also needs permission to list runtimes; supplying the Runtime ARN directly avoids discovery.

## 4. Set the Runtime region and ARN

Create a local `.env` file beside `invoke_chat_agent.py`:

```dotenv
# AWS region where the Runtime is deployed.
AWS_DEFAULT_REGION=<runtime-region>

# ARN of the deployed Runtime. Recommended to avoid needing discovery permission.
AGENT_RUNTIME_ARN=<your-agent-runtime-arn>
```

Get the region and ARN from the Runtime owner. Keep `.env` private: do not commit it, and do not put AWS credentials in it. AWS authentication should come from the AWS CLI profile, SSO, or another approved credential provider.

If `AGENT_RUNTIME_ARN` is omitted, the script tries to discover a ready/active Runtime in `AWS_DEFAULT_REGION`; if discovery fails, it asks for the ARN interactively.

## 5. Start chatting

Run:

```bash
python invoke_chat_agent.py
```

At the prompts:

1. Enter a user ID, or press Enter to use `user_1`.
2. Enter a session ID. Reuse the same ID to continue that Runtime session. For a new session, enter a unique ID of at least 33 characters (for example, `chat-` followed by a UUID). The script's blank-input fallback currently creates a shorter ID, so enter an ID explicitly.
3. Type a message. Type `exit`, `quit`, or `q` to end the chat.

## Logs and troubleshooting

- The client creates or appends to `agent_raw_debug.log` in the current directory. It records prompts and raw streamed response events, so treat it as sensitive and do not commit it.
- If AWS reports an authorization error, confirm the active identity with `aws sts get-caller-identity` and ask the Runtime administrator to check its invocation permissions.
- If the Runtime cannot be found or invoked, confirm the ARN and region match the deployment.
- If the session ID is rejected, provide a new ID at least 33 characters long.
