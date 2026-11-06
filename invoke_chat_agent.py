import os
import sys
import uuid
import json
import datetime
import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
EXPLICIT_ARN = os.getenv("AGENT_RUNTIME_ARN")
LOG_FILE = "agent_raw_debug.log"
SHOW_THINKING = False


def log_debug(message: str):
    """Appends raw text/events to the local debug log file."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def resolve_runtime_arn(region_name: str) -> str:
    if EXPLICIT_ARN:
        return EXPLICIT_ARN

    try:
        control_client = boto3.client("bedrock-agentcore-control", region_name=region_name)
        response = control_client.list_agent_runtimes()
        for r in response.get("agentRuntimes", []):
            if r.get("status") in ("READY", "ACTIVE"):
                return r.get("agentRuntimeArn")
    except Exception as e:
        log_debug(f"[WARN] Runtime auto-discovery failed: {e}")

    return input("Enter your Agent Runtime ARN: ").strip()


class StreamTextFilter:
    """Filters or formats Claude's <thinking> blocks from streaming text."""
    def __init__(self, show_thinking: bool = False):
        self.show_thinking = show_thinking
        self.in_thinking = False
        self.buffer = ""

    def feed(self, chunk: str):
        self.buffer += chunk
        while self.buffer:
            if not self.in_thinking:
                if "<thinking>" in self.buffer:
                    before, _, after = self.buffer.partition("<thinking>")
                    if before:
                        sys.stdout.write(before)
                        sys.stdout.flush()
                    self.in_thinking = True
                    self.buffer = after
                    if self.show_thinking:
                        sys.stdout.write("\n\033[90m[Thinking: ")
                        sys.stdout.flush()
                elif any("<thinking>".startswith(self.buffer[-i:]) for i in range(1, len("<thinking>"))):
                    break
                else:
                    sys.stdout.write(self.buffer)
                    sys.stdout.flush()
                    self.buffer = ""
            else:
                if "</thinking>" in self.buffer:
                    thought, _, after = self.buffer.partition("</thinking>")
                    if self.show_thinking:
                        sys.stdout.write(thought + "]\033[0m\n\n")
                        sys.stdout.flush()
                    self.in_thinking = False
                    self.buffer = after
                elif self.show_thinking:
                    sys.stdout.write(self.buffer)
                    sys.stdout.flush()
                    self.buffer = ""
                else:
                    if any("</thinking>".startswith(self.buffer[-i:]) for i in range(1, len("</thinking>"))):
                        break
                    else:
                        self.buffer = ""

    def finish(self):
        if self.buffer and not self.in_thinking:
            sys.stdout.write(self.buffer)
            sys.stdout.flush()
        if self.in_thinking and self.show_thinking:
            sys.stdout.write("]\033[0m\n")
            sys.stdout.flush()


def run_chatbot():
    runtime_arn = resolve_runtime_arn(REGION)
    if not runtime_arn:
        print("[!] No runtime ARN provided. Exiting.")
        sys.exit(1)

    agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)

    # User & Session Setup
    user_id = input("Enter User ID (or press Enter for default 'user_1'): ").strip() or "user_1"
    # session_id = "deploy-session-00000000000000000001"  # For testing with a fixed session
    session_id = input("Enter Session ID (or press Enter for a new session): ").strip() or f"session-{uuid.uuid4().hex[:12]}"

    log_debug(f"=== NEW SESSION INITIALIZED | User: {user_id} | Session: {session_id} ===")

    print("\n" + "=" * 60)
    print(" Strands Bedrock Chatbot (AgentCore Runtime)")
    print(f" User ID    : {user_id}")
    print(f" Session ID : {session_id}")
    print(f" Debug Log  : {LOG_FILE}")
    print(" Type 'exit' or 'quit' to end.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                log_debug(f"=== SESSION TERMINATED BY USER ===")
                print("\nGoodbye!")
                break

            log_debug(f"PROMPT [{user_id} | {session_id}]: {user_input}")

            payload = {
                "prompt": user_input,
                "session_id": session_id,
                "user_id": user_id
            }

            # 1. Invoke Bedrock AgentCore Runtime with session and user tracking
            response = agentcore_client.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                runtimeSessionId=session_id,
                runtimeUserId=user_id,
                payload=json.dumps(payload).encode("utf-8"),
                contentType="application/json"
            )

            print("Agent: ", end="", flush=True)
            stream_filter = StreamTextFilter(show_thinking=SHOW_THINKING)

            # 2. Capture and log raw response chunks
            body_stream = response.get("response")
            if body_stream:
                for line in body_stream.iter_lines():
                    if not line:
                        continue

                    # Decode raw line directly from SSE stream
                    decoded_line = line.decode("utf-8")
                    
                    # Record the untouched raw stream event into the log file
                    log_debug(f"RAW_CHUNK: {decoded_line}")

                    # 3. Parse with error trapping
                    if decoded_line.startswith("data: "):
                        raw_json_str = decoded_line[6:].strip()
                        try:
                            event = json.loads(raw_json_str)

                            # Handle both Bedrock Converse and custom delta payload shapes
                            delta = (
                                event.get("event", {}).get("contentBlockDelta", {}).get("delta", {})
                                or event.get("contentBlockDelta", {}).get("delta", {})
                                or {}
                            )
                            text_chunk = delta.get("text", "")

                            if text_chunk:
                                stream_filter.feed(text_chunk)

                        except json.JSONDecodeError as json_err:
                            log_debug(f"[PARSING ERROR] JSON decode failed: {json_err} | Line: {decoded_line}")
                        except Exception as parse_err:
                            log_debug(f"[PARSING ERROR] Unexpected error: {parse_err} | Line: {decoded_line}")

            stream_filter.finish()
            print("\n")

        except KeyboardInterrupt:
            log_debug(f"=== SESSION ABORTED via KeyboardInterrupt ===")
            print("\nSession interrupted. Exiting...")
            break
        except Exception as err:
            log_debug(f"[INVOCATION ERROR]: {err}")
            print(f"\n[Error]: {err}\n")


if __name__ == "__main__":
    run_chatbot()