# Strands AgentCore

A sample Strands agent backed by Amazon Bedrock, with a deployable Amazon Bedrock AgentCore Runtime application and small local/client scripts.

## Choose how to use it

- **Run an agent locally against Bedrock:** use the root `agent_local.py` example.
- **Deploy the Runtime application:** use the AgentCore CLI project under `strandsbedrock/`.
- **Chat with an existing deployed Runtime:** use `invoke_chat_agent.py` from the repository root.

These are separate paths. Running the local example does not deploy the Runtime application. For component details, see [architecture.md](./architecture.md).

## Prerequisites

- Python 3 and `pip` for root scripts. The deployable application specifies Python `>=3.10` in `pyproject.toml` and Python `3.14` in its AgentCore runtime configuration.
- AWS CLI v2 with credentials configured for an AWS account. Use an IAM role or your organization's approved SSO/credential flow; do not put AWS credentials in source files.
- Bedrock access to `amazon.nova-micro-v1:0` in the AWS region you use.
- For deployment: the current Amazon Bedrock AgentCore CLI, Node.js/npm, and AWS CDK prerequisites. Install/upgrade the CLI by following the current [Amazon Bedrock AgentCore documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html).

## 1. Clone and configure AWS credentials

```bash
git clone <your-github-repository-url>
cd Strands_agentcore
aws configure
aws sts get-caller-identity
```

If your organization uses AWS IAM Identity Center/SSO, authenticate using its approved AWS CLI workflow instead of `aws configure`. Confirm that your selected region supports the model and that model access is enabled.

## 2. Run the standalone local example

From the repository root, create a virtual environment and install the root-level dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

Optionally create a local `.env` file in the repository root to choose the AWS region:

```dotenv
AWS_DEFAULT_REGION=ap-southeast-2
```

Do not commit `.env` or put access keys in it. The AWS SDK uses the normal AWS credential chain. `agent_local.py` defaults to `us-east-1` if `AWS_DEFAULT_REGION` is not set.

Run the local example:

```bash
python agent_local.py
```

This calls Bedrock directly from your machine. It is not the AgentCore Runtime deployment.

## 3. Develop or deploy the AgentCore Runtime application

The deployable project is the `strandsbedrock/` directory. Before deployment:

1. Install the AgentCore CLI following the current official instructions linked above.
2. Ensure your AWS CLI identity has the permissions required to create/update the configured AgentCore and CDK resources.
3. Review `strandsbedrock/agentcore/aws-targets.json` and configure it for your own AWS account and region. Do not deploy to another account's target.
4. Confirm that the runtime's model is available and enabled in that region.

From the `strandsbedrock/` directory, run the local Runtime server:

```bash
cd strandsbedrock
agentcore dev
```

The generated project documents the local server on port `8080`. Stop it with `Ctrl+C`.

To synthesize and deploy:

```bash
agentcore build
agentcore deploy
agentcore status
```

Deploying creates or updates AWS resources and may incur charges. Review the selected target and synthesized changes before deployment. `agentcore status` reports the resources declared by `agentcore/agentcore.json`.

Invoke the deployed runtime using the AgentCore CLI:

```bash
agentcore invoke --runtime agent --payload '{"prompt":"Add 7 and 9","actorId":"user-123"}'
```

The runtime accepts either a `prompt` string or a `messages` array. `actorId` is optional and defaults to `"default"`. The AgentCore Runtime session ID is passed in the invocation context; reuse the same session ID with a compatible client when you need session continuity.

The application declares AgentCore Memory in `agentcore/agentcore.json`. The runtime code uses Memory only when `MEMORY_AGENTMEMORY_ID` is available; local development without that setting can run without the Memory session manager.

## 4. Use the terminal chat client with a deployed Runtime

From the repository root, use the same Python environment and dependencies from step 2. Set the runtime region and, optionally, the ARN in the root `.env` file:

```dotenv
AWS_DEFAULT_REGION=ap-southeast-2
AGENT_RUNTIME_ARN=<your-agent-runtime-arn>
```

If `AGENT_RUNTIME_ARN` is omitted, the client tries to discover an active/ready runtime and prompts for an ARN if discovery does not succeed. Then run:

```bash
python invoke_chat_agent.py
```

Enter a user ID and a session ID when prompted. Press Enter at the session prompt to create a new session; use the same session ID to continue one. Type `exit`, `quit`, or `q` to end the chat.

The client logs prompts and raw response events to `agent_raw_debug.log`. These logs may contain sensitive conversation content; protect or remove them according to your organization's data-handling rules. The client currently sends a `user_id` payload field, while the Runtime reads `actorId`; update the client payload if you need to scope Memory to the entered user ID.

> **Note:** `invoke_cloud.py` is a single-request sample with a hard-coded runtime ARN. Update it to your own Runtime ARN before running, or use `invoke_chat_agent.py`.

## Project layout

- `agent.py`, `agent_local.py`: root-level direct-to-Bedrock examples.
- `invoke_chat_agent.py`: interactive streaming client for a deployed Runtime.
- `invoke_cloud.py`: one-shot Runtime invocation sample.
- `requirements.txt`: dependencies for root-level scripts.
- `strandsbedrock/app/agent/`: deployable Runtime agent source and Python dependency lock.
- `strandsbedrock/agentcore/agentcore.json`: Runtime and Memory configuration.
- `strandsbedrock/agentcore/cdk/`: CDK app used by AgentCore CLI to synthesize/deploy the configured project.

## Troubleshooting

- **Credential errors:** check `aws sts get-caller-identity` and confirm the intended profile/role is active.
- **Model access errors:** verify the region and that `amazon.nova-micro-v1:0` is enabled for the account.
- **Runtime invocation errors:** run `agentcore status`, verify the runtime ARN and region, and check that the runtime has finished deploying.
- **No Memory behavior locally:** confirm whether `MEMORY_AGENTMEMORY_ID` is set in the runtime environment and that `actorId` is sent as expected.

For detailed component and data-flow notes, see [architecture.md](./architecture.md).
