from services.tools import send_email_tool, image_generation_tool, repl_tool
from langchain.agents import AgentType, initialize_agent, load_tools
from dependencies import llm

def create_agent_with_tools():
    """Create agent with tools"""
    tools = load_tools(["searx-search"], searx_host="http://localhost:8080", llm=llm)
    tools.append(repl_tool)
    tools.append(send_email_tool)
    tools.append(image_generation_tool)

    system_prompt = """You are a helpful AI assistant named Lumen. You where created by Bojan Radulović. Use tools only when necessary or when asked explicitly"""

    return initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        agent_kwargs={
            "prefix": system_prompt + "\n\nYou have access to the following tools:"
        }
    )