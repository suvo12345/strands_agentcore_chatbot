import os
from dotenv import load_dotenv
from strands import Agent, tool
from strands.models import BedrockModel

# Load AWS credentials from .env
load_dotenv()

# 1. Define custom tools for the agent (optional)
@tool
def calculate_rectangle_area(length: float, width: float) -> float:
    """
    Calculates the area of a rectangle given length and width.
    """
    return length * width

# 2. Configure the Bedrock Model Provider
# Use Amazon Nova Micro / Lite (or Anthropic Claude if enabled)
bedrock_model = BedrockModel(
    model_id="amazon.nova-micro-v1:0",  # or "amazon.nova-lite-v1:0" / "anthropic.claude-3-haiku-20240307-v1:0"
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    temperature=0.3,
    max_tokens=1000
)

# 3. Instantiate the Strands Agent
agent = Agent(
    model=bedrock_model,
    tools=[calculate_rectangle_area],
    system_prompt=(
        "You are an intelligent, helpful assistant. "
        "Use your attached tools whenever exact calculations are required."
    )
)

def run():
    prompt = "I have a garden measuring 14.5 meters by 8 meters. What is its area? Then suggest two plants that would fit well in it."
    print(f"User Prompt: {prompt}\n")
    
    # Execute the agent loop
    response = agent(prompt)
    print("Agent Response:")
    print(response)

if __name__ == "__main__":
    run()