"""
LangGraph ReAct Agent implementation with reasoning, tool calling, and multi-step problem solving.
This is a pure open-source solution without licensing requirements.
"""

import os
import re
import json
import logging
from typing import Annotated, Dict, Any, List, Optional, Literal
from typing_extensions import TypedDict

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from .models import model_manager
from .tools import tool_registry, ToolResult

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Enhanced state definition for the ReAct agent."""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    thread_id: str
    current_step: int
    reasoning_steps: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    final_answer: Optional[str]
    max_iterations: int
    current_thought: Optional[str]
    next_action: Optional[str]


def reasoning_node(state: AgentState) -> Dict[str, Any]:
    """
    ReAct Reasoning Node: Analyzes the problem and decides on next actions.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with reasoning and next action
    """
    messages = state.get("messages", [])
    thread_id = state.get("thread_id", "default")
    current_step = state.get("current_step", 0)
    reasoning_steps = state.get("reasoning_steps", [])
    tool_results = state.get("tool_results", [])
    
    # Extract the user query
    user_message = ""
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            user_message = last_message.get("content", "")
        else:
            user_message = str(last_message)
    
    logger.info(f"ReAct Reasoning Step {current_step + 1} for thread {thread_id}")
    
    # Build ReAct reasoning prompt
    reasoning_prompt = build_react_reasoning_prompt(
        user_query=user_message,
        reasoning_steps=reasoning_steps,
        tool_results=tool_results,
        available_tools=tool_registry.get_tools_description(),
        current_step=current_step
    )
    
    # Get reasoning response from AI model
    reasoning_response = model_manager.call_model(reasoning_prompt, thread_id)
    
    # Parse the reasoning response to extract thought and action
    thought, action, action_params = parse_react_response(reasoning_response)
    
    # Update reasoning steps
    new_reasoning_step = {
        "step": current_step + 1,
        "thought": thought,
        "action": action,
        "action_params": action_params,
        "timestamp": "now()"
    }
    
    return {
        "current_step": current_step + 1,
        "reasoning_steps": reasoning_steps + [new_reasoning_step],
        "current_thought": thought,
        "next_action": action,
        **action_params  # Add action parameters to state
    }


def tool_execution_node(state: AgentState) -> Dict[str, Any]:
    """
    Tool Execution Node: Executes the selected tool and captures results.
    
    Args:
        state: Current agent state with next_action defined
        
    Returns:
        Updated state with tool results
    """
    next_action = state.get("next_action")
    tool_results = state.get("tool_results", [])
    current_step = state.get("current_step", 0)
    
    if not next_action or next_action == "final_answer":
        # No tool to execute, return state unchanged
        return {}
    
    logger.info(f"Executing tool: {next_action}")
    
    # Extract tool parameters from state (added by reasoning node)
    tool_params = {}
    for key, value in state.items():
        if key.startswith("tool_"):
            param_name = key[5:]  # Remove 'tool_' prefix
            tool_params[param_name] = value
    
    # Execute the tool
    tool_result = tool_registry.execute_tool(next_action, **tool_params)
    
    # Create tool result record
    result_record = {
        "step": current_step,
        "tool_name": next_action,
        "tool_params": tool_params,
        "success": tool_result.success,
        "content": tool_result.content,
        "error": tool_result.error,
        "metadata": tool_result.metadata,
        "timestamp": "now()"
    }
    
    logger.info(f"Tool {next_action} executed. Success: {tool_result.success}")
    
    return {
        "tool_results": tool_results + [result_record]
    }


def intermediate_synthesis_node(state: AgentState) -> Dict[str, Any]:
    """
    Intermediate Synthesis Node: Evaluates current progress and decides next steps.
    This allows the agent to assess what it has learned and decide if more reasoning is needed.
    
    Args:
        state: Current agent state with reasoning and tool results
        
    Returns:
        Updated state with synthesis evaluation
    """
    messages = state.get("messages", [])
    reasoning_steps = state.get("reasoning_steps", [])
    tool_results = state.get("tool_results", [])
    thread_id = state.get("thread_id", "default")
    current_step = state.get("current_step", 0)
    
    user_message = ""
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            user_message = last_message.get("content", "")
        else:
            user_message = str(last_message)
    
    logger.info(f"Intermediate synthesis evaluation for thread {thread_id}")
    
    # Build synthesis evaluation prompt
    synthesis_prompt = build_intermediate_synthesis_prompt(
        user_query=user_message,
        reasoning_steps=reasoning_steps,
        tool_results=tool_results,
        current_step=current_step
    )
    
    # Get synthesis evaluation from AI model
    synthesis_response = model_manager.call_model(synthesis_prompt, thread_id)
    
    # Parse the synthesis response to determine if we need more reasoning
    evaluation, next_action, action_params = parse_synthesis_response(synthesis_response)
    
    # Update state with synthesis evaluation
    return {
        "current_thought": evaluation,
        "next_action": next_action,
        **action_params  # Add any new action parameters
    }


def final_answer_node(state: AgentState) -> Dict[str, Any]:
    """
    Final Answer Node: Generates the final comprehensive response.
    Only reached when the agent is confident it has enough information.
    
    Args:
        state: Current agent state with all reasoning and tool results
        
    Returns:
        Updated state with final assistant response
    """
    messages = state.get("messages", [])
    reasoning_steps = state.get("reasoning_steps", [])
    tool_results = state.get("tool_results", [])
    thread_id = state.get("thread_id", "default")
    
    user_message = ""
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            user_message = last_message.get("content", "")
        else:
            user_message = str(last_message)
    
    logger.info(f"Generating final answer for thread {thread_id}")
    
    # Build final synthesis prompt
    synthesis_prompt = build_final_synthesis_prompt(
        user_query=user_message,
        reasoning_steps=reasoning_steps,
        tool_results=tool_results
    )
    
    # Generate final response
    final_response = model_manager.call_model(synthesis_prompt, thread_id)
    
    # Clean up the response
    if isinstance(final_response, dict):
        final_response = final_response.get("content", str(final_response))
    elif not isinstance(final_response, str):
        final_response = str(final_response)
    
    return {
        "final_answer": final_response.strip(),
        "messages": [{"role": "assistant", "content": final_response.strip()}]
    }


def should_continue_reasoning(state: AgentState) -> Literal["continue", "synthesize"]:
    """
    Routing function to determine if ReAct loop should continue reasoning or do intermediate synthesis.
    
    Args:
        state: Current agent state
        
    Returns:
        "continue" to execute tools, "synthesize" to evaluate progress
    """
    next_action = state.get("next_action")
    
    # If action is "final_answer", go to synthesis to evaluate
    if next_action == "final_answer":
        logger.info("Agent decided to synthesize and evaluate progress")
        return "synthesize"
    
    # If there's a tool to execute, continue
    if next_action and next_action != "final_answer":
        logger.info(f"Continuing to execute tool: {next_action}")
        return "continue"
    
    # Default to synthesis for evaluation
    return "synthesize"


def should_continue_synthesis(state: AgentState) -> Literal["continue", "final_answer"]:
    """
    Routing function after synthesis to determine if more reasoning is needed or provide final answer.
    
    Args:
        state: Current agent state
        
    Returns:
        "continue" to keep reasoning, "final_answer" to end with response
    """
    current_step = state.get("current_step", 0)
    max_iterations = state.get("max_iterations", 5)
    next_action = state.get("next_action")
    
    # Stop if we've reached max iterations
    if current_step >= max_iterations:
        logger.info(f"Reached max iterations ({max_iterations}), providing final answer")
        return "final_answer"
    
    # Stop if synthesis determined we have enough information
    if next_action == "final_answer":
        logger.info("Synthesis determined we have enough information for final answer")
        return "final_answer"
    
    # Continue reasoning if synthesis identified more work needed
    logger.info(f"Synthesis determined more reasoning needed (step {current_step}/{max_iterations})")
    return "continue"


def build_react_reasoning_prompt(
    user_query: str, 
    reasoning_steps: List[Dict[str, Any]], 
    tool_results: List[Dict[str, Any]], 
    available_tools: str, 
    current_step: int
) -> str:
    """
    Build ReAct reasoning prompt for the AI model.
    
    Args:
        user_query: The user's original query
        reasoning_steps: Previous reasoning steps
        tool_results: Results from tool executions
        available_tools: Description of available tools
        current_step: Current reasoning step number
        
    Returns:
        Formatted ReAct reasoning prompt
    """
    prompt = f"""You are an expert ReAct (Reasoning + Acting) AI agent. Your job is to solve problems through systematic reasoning and tool usage.

AVAILABLE TOOLS:
{available_tools}

INSTRUCTIONS:
1. Think step by step about the user's query
2. Decide what action to take next (use a tool or provide final answer)
3. Always format your response as:

**Thought:** [Your reasoning about what to do next]
**Action:** [tool_name OR "final_answer"]
**Action Parameters:** [If using a tool, provide parameters as key=value pairs]

USER QUERY: {user_query}

PREVIOUS REASONING STEPS:"""
    
    # Add previous reasoning steps
    for step in reasoning_steps:
        prompt += f"\nStep {step['step']}:\n"
        prompt += f"**Thought:** {step['thought']}\n"
        prompt += f"**Action:** {step['action']}\n"
        if step.get('action_params'):
            prompt += f"**Action Parameters:** {step['action_params']}\n"
    
    # Add tool results
    if tool_results:
        prompt += "\nTOOL RESULTS:\n"
        for result in tool_results:
            prompt += f"\nTool: {result['tool_name']} (Step {result['step']})\n"
            prompt += f"Success: {result['success']}\n"
            if result['success']:
                prompt += f"Result: {result['content'][:500]}{'...' if len(result['content']) > 500 else ''}\n"
            else:
                prompt += f"Error: {result['error']}\n"
    
    prompt += f"\nNow, what is your next step? (This is step {current_step + 1})\n\n**Thought:**"
    
    return prompt


def build_intermediate_synthesis_prompt(
    user_query: str, 
    reasoning_steps: List[Dict[str, Any]], 
    tool_results: List[Dict[str, Any]],
    current_step: int
) -> str:
    """
    Build intermediate synthesis prompt to evaluate progress and decide next steps.
    
    Args:
        user_query: The user's original query
        reasoning_steps: All reasoning steps taken so far
        tool_results: All tool execution results so far
        current_step: Current step number
        
    Returns:
        Formatted intermediate synthesis prompt
    """
    prompt = f"""You are evaluating your progress on solving a user's query. Based on what you've learned so far, decide if you need to gather more information or if you have enough to provide a comprehensive answer.

USER QUERY: {user_query}

REASONING STEPS TAKEN:"""
    
    # Add reasoning steps
    for step in reasoning_steps:
        prompt += f"\nStep {step['step']}: {step['thought']}"
        if step.get('action') != 'final_answer':
            prompt += f" (Action: {step['action']})"
    
    # Add tool results
    if tool_results:
        prompt += "\n\nINFORMATION GATHERED:"
        for result in tool_results:
            if result['success']:
                prompt += f"\n\nFrom {result['tool_name']}: {result['content'][:300]}{'...' if len(result['content']) > 300 else ''}"
            else:
                prompt += f"\n\nFrom {result['tool_name']}: Failed - {result['error']}"
    
    prompt += f"""

EVALUATION INSTRUCTIONS:
1. Assess if you have sufficient information to fully answer the user's query
2. Identify any gaps in information or additional tools needed
3. Format your response as:

**Evaluation:** [Your assessment of current progress and what's missing, if anything]
**Action:** [tool_name if more information needed, OR "final_answer" if ready to respond]
**Action Parameters:** [If using a tool, provide parameters as key=value pairs]

Current step: {current_step}

**Evaluation:**"""
    
    return prompt


def build_final_synthesis_prompt(
    user_query: str, 
    reasoning_steps: List[Dict[str, Any]], 
    tool_results: List[Dict[str, Any]]
) -> str:
    """
    Build final synthesis prompt to generate comprehensive final response.
    
    Args:
        user_query: The user's original query
        reasoning_steps: All reasoning steps taken
        tool_results: All tool execution results
        
    Returns:
        Formatted final synthesis prompt
    """
    prompt = f"""You are providing a final, comprehensive response to the user based on all your reasoning and information gathering. Create a helpful, natural response that fully addresses their question.

USER QUERY: {user_query}

YOUR COMPLETE REASONING PROCESS:"""
    
    # Add reasoning steps
    for step in reasoning_steps:
        prompt += f"\nStep {step['step']}: {step['thought']}"
    
    # Add tool results
    if tool_results:
        prompt += "\n\nALL INFORMATION GATHERED:"
        for result in tool_results:
            if result['success']:
                prompt += f"\n\nFrom {result['tool_name']}: {result['content']}"
            else:
                prompt += f"\n\nFrom {result['tool_name']}: Failed - {result['error']}"
    
    prompt += f"""

Now provide a comprehensive, helpful response to the user's query: "{user_query}"

Your response should:
- Be natural and conversational
- Directly answer their question
- Include relevant details from the information you gathered
- Be well-organized and easy to understand
- Show how the information relates to their original question

Response:"""
    
    return prompt


def parse_synthesis_response(response: str) -> tuple[str, str, Dict[str, Any]]:
    """
    Parse synthesis evaluation response to extract evaluation, action, and parameters.
    
    Args:
        response: Raw response from AI model during synthesis
        
    Returns:
        Tuple of (evaluation, action, action_parameters)
    """
    evaluation = ""
    action = ""
    action_params = {}
    
    try:
        # Extract evaluation
        eval_match = re.search(r'\*\*Evaluation:\*\*\s*(.*?)(?=\*\*Action:\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if eval_match:
            evaluation = eval_match.group(1).strip()
        
        # Extract action
        action_match = re.search(r'\*\*Action:\*\*\s*(.*?)(?=\*\*Action Parameters:\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()
        
        # Extract action parameters
        params_match = re.search(r'\*\*Action Parameters:\*\*\s*(.*?)$', response, re.DOTALL | re.IGNORECASE)
        if params_match:
            params_text = params_match.group(1).strip()
            # Parse key=value pairs
            for line in params_text.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    # Add tool_ prefix for state management
                    action_params[f'tool_{key}'] = value
        
        logger.info(f"Parsed synthesis response - Evaluation: {evaluation[:100]}..., Action: {action}")
        
    except Exception as e:
        logger.error(f"Failed to parse synthesis response: {e}")
        # Fallback
        evaluation = response[:200] + "..." if len(response) > 200 else response
        action = "final_answer"  # Default to final answer if parsing fails
    
    return evaluation, action, action_params


def parse_react_response(response: str) -> tuple[str, str, Dict[str, Any]]:
    """
    Parse ReAct reasoning response to extract thought, action, and parameters.
    
    Args:
        response: Raw response from AI model
        
    Returns:
        Tuple of (thought, action, action_parameters)
    """
    thought = ""
    action = ""
    action_params = {}
    
    try:
        # Extract thought
        thought_match = re.search(r'\*\*Thought:\*\*\s*(.*?)(?=\*\*Action:\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
        
        # Extract action
        action_match = re.search(r'\*\*Action:\*\*\s*(.*?)(?=\*\*Action Parameters:\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()
        
        # Extract action parameters
        params_match = re.search(r'\*\*Action Parameters:\*\*\s*(.*?)$', response, re.DOTALL | re.IGNORECASE)
        if params_match:
            params_text = params_match.group(1).strip()
            # Parse key=value pairs
            for line in params_text.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    # Add tool_ prefix for state management
                    action_params[f'tool_{key}'] = value
        
        logger.info(f"Parsed ReAct response - Thought: {thought[:100]}..., Action: {action}")
        
    except Exception as e:
        logger.error(f"Failed to parse ReAct response: {e}")
        # Fallback parsing
        thought = response[:200] + "..." if len(response) > 200 else response
        action = "final_answer"  # Default to final answer if parsing fails
    
    return thought, action, action_params




def create_postgres_checkpointer():
    """
    Create PostgreSQL checkpointer for conversation memory.
    
    Returns:
        PostgresSaver instance or None if setup fails
    """
    try:
        # Import lazily so missing package doesn't crash service startup
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError:
            logger.warning("LangGraph Postgres checkpointer not installed; using in-memory checkpointer.")
            from langgraph.checkpoint.memory import MemorySaver
            return MemorySaver()

        database_url = os.getenv(
            "DATABASE_URI",
            "postgresql://langgraph:langgraph_password@postgres:5432/langgraph",
        )

        logger.info("🔧 Setting up PostgreSQL checkpointer...")

        # Create connection pool
        pool = SimpleConnectionPool(1, 10, database_url)

        # Initialize PostgreSQL checkpointer
        checkpointer = PostgresSaver(pool)

        # Setup database tables if they don't exist
        checkpointer.setup()

        logger.info("✅ PostgreSQL checkpointer initialized successfully")
        return checkpointer

    except Exception as e:
        logger.error(f"❌ Failed to create PostgreSQL checkpointer: {e}")
        logger.info("🔄 Falling back to in-memory checkpointer")

        # Fallback to memory saver
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()


# Build the ReAct LangGraph with proper loop
def create_react_graph() -> StateGraph:
    """
    Create and compile the ReAct agent graph with proper reasoning loop.
    
    Architecture:
    START → reasoning → tool_execution → intermediate_synthesis → reasoning (loop)
                ↓                              ↓
            synthesis_evaluation          final_answer → END
    
    Returns:
        Compiled LangGraph ReAct agent instance
    """
    logger.info("🔧 Building LangGraph ReAct Agent with proper reasoning loop...")
    
    # Create PostgreSQL checkpointer
    checkpointer = create_postgres_checkpointer()
    
    # Create graph builder with enhanced state
    builder = StateGraph(AgentState)
    
    # Add ReAct nodes
    builder.add_node("reasoning", reasoning_node)
    builder.add_node("tool_execution", tool_execution_node)
    builder.add_node("intermediate_synthesis", intermediate_synthesis_node)
    builder.add_node("final_answer", final_answer_node)
    
    # Add edges for ReAct flow
    builder.add_edge(START, "reasoning")
    
    # Conditional routing from reasoning
    builder.add_conditional_edges(
        "reasoning",
        should_continue_reasoning,
        {
            "continue": "tool_execution",
            "synthesize": "intermediate_synthesis"
        }
    )
    
    # After tool execution, always go back to reasoning
    builder.add_edge("tool_execution", "reasoning")
    
    # Conditional routing from intermediate synthesis
    builder.add_conditional_edges(
        "intermediate_synthesis",
        should_continue_synthesis,
        {
            "continue": "reasoning",      # Loop back for more reasoning
            "final_answer": "final_answer"  # End with final response
        }
    )
    
    # Final answer goes to END
    builder.add_edge("final_answer", END)
    
    # Compile graph with checkpointer for persistent memory
    compiled_graph = builder.compile(checkpointer=checkpointer)
    
    logger.info("✅ LangGraph ReAct Agent compiled with proper reasoning loop")
    return compiled_graph


def initialize_react_state(messages: List[Dict[str, Any]], thread_id: str, react_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Initialize state for ReAct agent with default values.
    
    Args:
        messages: Conversation messages
        thread_id: Thread identifier
        react_settings: Optional ReAct settings from UI
        
    Returns:
        Initialized state dictionary
    """
    # Use settings from UI or environment defaults
    max_iterations = 5
    if react_settings:
        max_iterations = react_settings.get('maxIterations', 5)
    else:
        max_iterations = int(os.getenv("REACT_MAX_ITERATIONS", "5"))
    
    return {
        "messages": messages,
        "thread_id": thread_id,
        "current_step": 0,
        "reasoning_steps": [],
        "tool_results": [],
        "final_answer": None,
        "max_iterations": max_iterations,
        "current_thought": None,
        "next_action": None
    }


# Create the global ReAct graph instance
graph = create_react_graph()
