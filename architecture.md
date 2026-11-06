# Architecture

## Overview

This repository contains a small Strands agent example in two forms:

1. **Standalone Python examples and clients** at the repository root. These support local model invocation and a terminal chat client for an already-deployed AgentCore Runtime.
2. **An AgentCore Runtime application** in `strandsbedrock/`. This is the deployable application, configured as an HTTP runtime and provisioned through the AgentCore CLI and AWS CDK.

The root examples and the deployable application are related demonstrations, but they are separate implementations. The root scripts do not start or deploy the runtime application.

## Runtime request flow

```text
Caller
  ├─ AgentCore CLI invocation
  └─ invoke_chat_agent.py (terminal streaming client)
         │ JSON payload + runtime session ID
         ▼
Amazon Bedrock AgentCore Runtime (HTTP)
         │ invoke(payload, context)
         ▼
strandsbedrock/app/agent/main.py
  ├─ parse.py: validate/normalize prompt or message history and actor ID
  ├─ memory/session.py: create AgentCore Memory session manager if configured
  ├─ model/load.py: configure the Amazon Nova Micro Bedrock model
  └─ Strands Agent: run the model/tool loop and stream events
         │
         ├─ Amazon Bedrock model inference
         ├─ AgentCore Memory (when a Memory ID is available)
         └─ add_numbers tool
```

The runtime entrypoint is asynchronous and yields Strands events to the caller. The application uses the `HTTP` protocol and the AgentCore Runtime SDK's `BedrockAgentCoreApp` wrapper.

## Runtime components

### Agent construction and execution

- `strandsbedrock/app/agent/main.py` defines the `add_numbers` tool and the runtime entrypoint.
- The entrypoint calls `parse_payload()` to accept either a `prompt` string or a `messages` array. The `actorId` is used for Memory scoping and defaults to `"default"`.
- `_get_agent()` caches up to 128 Strands `Agent` instances by `(session_id, actor_id)`.
- The agent uses `NullConversationManager`; persistent conversation/memory integration is supplied separately through the AgentCore Memory session manager.
- The entrypoint streams event dictionaries from `agent.stream_async()`.

### Model

`strandsbedrock/app/agent/model/load.py` constructs a Strands `BedrockModel` using `amazon.nova-micro-v1:0`. It relies on the AWS SDK credential chain and the AWS region supplied by the runtime/environment.

At the repository root, `agent.py` and `agent_local.py` are standalone examples that also use Nova Micro and expose a rectangle-area tool. Their system prompts and defaults are not the same as the deployable runtime.

### Memory and sessions

- The runtime session ID is read from the AgentCore invocation context, not from the JSON body.
- `strandsbedrock/app/agent/memory/session.py` returns an `AgentCoreMemorySessionManager` when `MEMORY_AGENTMEMORY_ID` is set; otherwise it returns `None`.
- Memory retrieval uses actor- and session-scoped namespaces for facts, preferences, episodes, and summaries.
- `strandsbedrock/agentcore/agentcore.json` declares the `agentMemory` resource, its 30-day event expiry, and semantic, preference, summarization, and episodic strategies.

### Payload handling

The runtime accepts a JSON object:

```json
{"prompt": "Add 7 and 9", "actorId": "user-123"}
```

It also accepts a `messages` array, which takes precedence over `prompt`. The parser validates payload, actor, prompt, and message content types. For a supplied message history, it removes trailing `toolUse` blocks before passing the history to the agent.

`invoke_chat_agent.py` currently sends `user_id`, whereas the deployable runtime reads `actorId`. As a result, that client does not select a matching Memory actor unless it is updated to send `actorId`. Runtime session continuity is passed separately through `runtimeSessionId`.

## Deployment and infrastructure

`strandsbedrock/agentcore/agentcore.json` declares the runtime name, Python runtime version, HTTP protocol, code location (`app/agent`), entrypoint (`main.py`), and Memory configuration.

The AgentCore CLI reads that configuration and uses the CDK application in `strandsbedrock/agentcore/cdk/` to synthesize and deploy infrastructure:

- `cdk/bin/cdk.ts` loads the AgentCore project and resolves deployment target stacks.
- `cdk/lib/cdk-stack.ts` creates an `AgentCoreApplication`; it is the extension point for additional AWS resources.
- `cdk/package.json` describes the TypeScript/CDK dependencies.
- `agentcore/aws-targets.json` selects AWS deployment target information. Set this up for your own AWS account and region before deploying.

The deployable runtime's Python dependencies are defined in `strandsbedrock/app/agent/pyproject.toml` and pinned by its `uv.lock`. The root `requirements.txt` is for the root-level examples and clients.

## Repository map

```text
.
├── agent.py                         # Standalone Strands + Bedrock example
├── agent_local.py                   # Local example that loads .env
├── invoke_chat_agent.py             # Interactive client for a deployed Runtime
├── invoke_cloud.py                  # Single-request client (contains a fixed runtime ARN)
├── requirements.txt                 # Root example/client dependencies
├── architecture.md
├── readme.md
└── strandsbedrock/
    ├── app/agent/
    │   ├── main.py                  # AgentCore Runtime entrypoint and Strands agent
    │   ├── parse.py                 # Payload validation and normalization
    │   ├── model/load.py            # Bedrock model setup
    │   ├── memory/session.py        # Optional AgentCore Memory integration
    │   ├── pyproject.toml
    │   └── uv.lock
    └── agentcore/
        ├── agentcore.json           # Runtime and Memory declarations
        ├── aws-targets.json         # Deployment target configuration
        └── cdk/                     # CDK application used by AgentCore CLI
```

## Operational considerations

- Model access must be enabled for the selected Bedrock model in the deployment region, and the invoking/deployed identity must have the necessary AWS permissions.
- `invoke_chat_agent.py` writes prompts and raw streamed response events to `agent_raw_debug.log`. Treat this file as potentially sensitive and avoid sending private data during debugging.
- The root `invoke_cloud.py` has a hard-coded runtime ARN. Prefer the environment-configured/auto-discovery flow in `invoke_chat_agent.py`, or replace the ARN with one from your own deployment before using the single-request example.
