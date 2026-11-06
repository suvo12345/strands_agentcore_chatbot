import os
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# 1. Initialize the AgentCore App
app = BedrockAgentCoreApp()

# 2. Define Tools
@tool
def calculate_rectangle_area(length: float, width: float) -> float:
    """Calculates the area of a rectangle given length and width."""
    return length * width

# 3. Configure the Bedrock Model Provider
bedrock_model = BedrockModel(
    model_id="amazon.nova-micro-v1:0",  # Or amazon.nova-lite-v1:0
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2"),
    temperature=0.3,
    max_tokens=1000
)

# 4. Instantiate the Strands Agent
agent = Agent(
    model=bedrock_model,
    tools=[calculate_rectangle_area],
    system_prompt="You are a helpful assistant deployed on Bedrock AgentCore. Use your tools when needed."
)

# 5. Define the AgentCore Entrypoint Handler
@app.entrypoint
def invoke(payload, context=None):
    """
    AgentCore runtime forwards incoming HTTP payloads here.
    Supports input keys such as {"prompt": "..."} or standard message objects.
    """
    user_prompt = payload.get("prompt", "Hello")
    response = agent(user_prompt)
    
    return {
        "status": "success",
        "result": str(response)
    }

if __name__ == "__main__":
    # Runs the local HTTP server on port 8080 for testing
    app.run()
    