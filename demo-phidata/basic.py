from phi.agent import Agent
from phi.model.openai import OpenAIChat

from dotenv import load_dotenv

load_dotenv()

def create_basic_agent():
    """Creates a single conversational agent."""
    agent = Agent(
        name="Jarvis",
        model=OpenAIChat(id="gpt-4o"),
        description="You are a helpful AI assistant.",
        instructions=[
            "Be concise and helpful.",
            "Ask clarifying questions if needed.",
        ],
        markdown=True,
        debug_mode=False,  
    )
    return agent

if __name__ == "__main__":
    agent = create_basic_agent()
    agent.print_response("what is the value of Pi?", stream=True)