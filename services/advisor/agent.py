import os
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

# 1. Configure the LLM
# Make sure to set the GROQ_API_KEY environment variable
# export GROQ_API_KEY="your_api_key"
llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=1,
    max_tokens=1024,
)

# 2. Define tools for the agent (initially empty)
tools = []

# 3. Create the ReAct agent
agent_advisor = create_react_agent(
    model=llm,
    tools=tools,
    prompt=""  # Empty prompt as requested
) 