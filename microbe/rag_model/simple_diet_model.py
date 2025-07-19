from typing import Annotated, TypedDict

from langchain.agents import AgentExecutor
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_ollama import OllamaLLM
from langchain_core.tools import Tool

from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda

class SimpleDietModel:
    def __init__(self, model_id, model_provider, retriever, tools=None):
        self.model_id = model_id
        self.model_provider = model_provider
        self.retriever = retriever
        self.tools = tools

    def set_tools(self, tools):
        """
        Set the tools for the ReAct agent.

        Args:
            tools: List of tools to be used by the agent.
        """
        self.tools = tools

    def get_runnable_app(self):
        class AgentState(TypedDict):
            messages: Annotated[list[BaseMessage], "chat_history"]

        # Build the ReAct agent node
        agent_node = create_react_agent(
            model=":".join([self.model_provider, self.model_id]),
            tools=self.tools,
        )

        #agent_executor = AgentExecutor(agent=agent_node, tools=self.tools, verbose=True)

        # Define the graph
        graph = StateGraph(AgentState)
        graph.add_node("agent", agent_node)
        graph.set_entry_point("agent")
        graph.set_finish_point("agent")

        # Compile it into a runnable app
        app = graph.compile()

        return app

    def get_ollama_llm(self):
        return OllamaLLM(model=self.model_id)

    def retrieve_docs(self, query: str):
        results = self.retriever.get_relevant_documents(query)
        return "\n".join([doc.page_content for doc in results])

    def get_rag_tool(self):
        return Tool(
        name="GuidelineRetriever",
        func=self.retrieve_docs,
        description="Retrieves food guideline passages relevant to a user query"
    )

    def retrieve_guidelines_node(self, state):
        query = state["messages"][-1].content
        results = self.retrieve_docs(query)  # calls your retriever tool
        candidate_foods = [line.strip() for line in results.split('\n') if line.strip()]
        return {**state, "selected_foods": candidate_foods}

    def compose_response_node(state):
        subs = "\n".join([f"- {f}" for f in state.get("valid_substitutions", [])])
        nutrients = state.get("nutrient_analysis", "No analysis available.")
        final_msg = f"### Suggested Live Microbe Food Replacements:\n{subs}\n\n### Nutrient Summary:\n{nutrients}"
        state["messages"].append(AIMessage(content=final_msg))
        return state

    def invoke_model(self, messages):
        """
        Invoke the model with the given messages.

        Args:
            app: The runnable app created from the graph.
            messages: List of messages to send to the model.

        Returns:
            The response from the model.
        """
        app = self.get_runnable_app()

        # Prepare the initial state
        state = {"messages": messages}

        # Run the app
        response = app.invoke(state)

        final_response = None
        for message in reversed(response['messages']):
            if isinstance(message, AIMessage) and message.content.strip():
                final_response = message.content
                break

        return final_response