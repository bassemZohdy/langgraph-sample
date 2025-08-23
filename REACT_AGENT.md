# 🧠 LangGraph ReAct Agent Architecture

## Overview

Our agent has been transformed from a simple linear chat bot to a sophisticated **ReAct (Reasoning + Acting) Agent** that can:

- 🔍 **Reason** through complex problems step-by-step
- 🛠️ **Use tools** to gather information and perform actions  
- 🔄 **Iterate** through multiple reasoning-action cycles
- 📝 **Synthesize** comprehensive responses from all gathered information

## 🏗️ Architecture

### ReAct Flow Diagram
```
START → reasoning → tool_execution → reasoning (loop)
            ↓              ↓               ↑
            ↓              └───────────────┘
            ↓
        intermediate_synthesis → reasoning (continue loop)
            ↓
        final_answer → END
```

**Corrected Architecture**: The key insight is that after each tool execution, the agent goes back to reasoning. Then after reasoning, it either executes more tools OR does intermediate synthesis to evaluate progress. The synthesis can then decide to continue reasoning or provide the final answer.

### Core Components

#### 1. **Reasoning Node** (`reasoning_node`)
- Analyzes the current situation
- Decides what action to take next
- Generates structured thoughts using ReAct prompting
- Parses AI responses to extract: Thought, Action, Parameters

#### 2. **Tool Execution Node** (`tool_execution_node`) 
- Executes the selected tool with parameters
- Captures results and error handling
- Updates state with tool outcomes

#### 3. **Intermediate Synthesis Node** (`intermediate_synthesis_node`)
- Evaluates current progress and information gathered
- Decides if more reasoning/tools are needed
- Acts as a "checkpoint" to assess completeness

#### 4. **Final Answer Node** (`final_answer_node`)
- Generates the final comprehensive response
- Only reached when synthesis confirms sufficient information
- Provides natural, helpful answers to users

#### 5. **Routing Logic** 
- **`should_continue_reasoning`**: Decides if reasoning should execute tools or evaluate progress
- **`should_continue_synthesis`**: Decides if synthesis should continue reasoning or provide final answer
- Respects max iteration limits and handles decision points

## 🛠️ Available Tools

### 1. **Web Search Tool** (`web_search`)
- Searches current information online
- **Parameters**: `query`, `max_results`
- **Use case**: Recent news, current events, latest information

### 2. **Document Search Tool** (`document_search`) 
- Searches uploaded documents using vector similarity
- **Parameters**: `query`, `max_results`, `similarity_threshold`
- **Use case**: Finding information in uploaded files

### 3. **Calculator Tool** (`calculator`)
- Performs mathematical calculations
- **Parameters**: `expression`
- **Use case**: Math operations, scientific functions

### 4. **Code Execution Tool** (`code_execution`)
- Executes Python code safely in sandbox
- **Parameters**: `code`, `timeout`
- **Use case**: Data processing, complex calculations, analysis

### 5. **List Documents Tool** (`list_documents`)
- Shows available uploaded documents
- **Parameters**: `limit`
- **Use case**: Seeing what documents are available to search

## 🔄 ReAct Process Example

### User Query: *"What's the average of the numbers in my uploaded budget file?"*

**Step 1: Reasoning**
- **Thought**: "I need to first see what documents are available, then search for the budget file, and finally calculate the average."
- **Action**: `list_documents`

**Step 2: Tool Execution**
- Lists available documents
- **Result**: Found "budget_2024.xlsx"

**Step 3: Reasoning** 
- **Thought**: "Now I should search the budget document for numerical data."
- **Action**: `document_search`
- **Parameters**: `query="numbers data values budget"`

**Step 4: Tool Execution**
- Searches document content
- **Result**: Found text containing "Revenue: 150000, Expenses: 120000, Profit: 30000"

**Step 5: Reasoning**
- **Thought**: "I found the numbers. Now I need to calculate the average of 150000, 120000, and 30000."
- **Action**: `calculator` 
- **Parameters**: `expression="(150000 + 120000 + 30000) / 3"`

**Step 6: Tool Execution**
- Performs calculation
- **Result**: 100000

**Step 7: Reasoning**
- **Thought**: "I have all the information needed to provide a comprehensive answer."
- **Action**: `final_answer`

**Step 8: Synthesis**
- Combines all steps into final response
- **Final Answer**: "Based on your budget file, I found three key numbers: Revenue (150,000), Expenses (120,000), and Profit (30,000). The average of these values is 100,000."

## ⚙️ Configuration

### Environment Variables
```bash
# ReAct Agent Settings
REACT_MAX_ITERATIONS=5          # Max reasoning steps
EMBEDDING_CHUNK_SIZE=1000       # Document chunk size  
EMBEDDING_CHUNK_OVERLAP=200     # Chunk overlap for context

# Embedding Model (for document search)
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

### State Management
The agent maintains rich state across the conversation:
- `current_step`: Current reasoning iteration
- `reasoning_steps`: All reasoning steps taken
- `tool_results`: All tool execution results  
- `final_answer`: Synthesized response
- `max_iterations`: Safety limit for reasoning loops

## 🎯 Key Benefits

### 1. **Multi-Step Problem Solving**
- Breaks complex queries into manageable steps
- Can handle problems requiring multiple information sources
- Iterative refinement of understanding

### 2. **Tool Integration**  
- Seamlessly uses external tools and APIs
- Combines multiple data sources (web + documents + calculations)
- Extensible tool system for new capabilities

### 3. **Transparent Reasoning**
- Shows step-by-step thought process
- Provides visibility into decision making
- Builds trust through explainable AI

### 4. **Robust Error Handling**
- Continues working even if tools fail
- Provides fallback responses  
- Graceful degradation of capabilities

## 🔧 Adding New Tools

To add a new tool, create a class inheriting from `BaseTool`:

```python
class MyCustomTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property  
    def description(self) -> str:
        return "Description of what my tool does and its parameters"
    
    def execute(self, **kwargs) -> ToolResult:
        # Tool implementation
        return ToolResult(success=True, content="Result")

# Register the tool
tool_registry.register_tool(MyCustomTool())
```

## 🚀 Usage Examples

### Research Query
*"What are the latest developments in AI and how do they compare to information in my research notes?"*

**ReAct Process:**
1. Web search for latest AI developments
2. Document search through uploaded research notes
3. Synthesis comparing current info with existing notes

### Data Analysis  
*"Calculate the ROI for each project in my spreadsheet and tell me which performed best"*

**ReAct Process:**
1. List available documents
2. Search spreadsheet for project data
3. Use code execution to calculate ROI for each project
4. Synthesize results with recommendations

### Complex Problem Solving
*"I need help planning a budget. What's the current inflation rate and how should I adjust my expenses from last year's budget?"*

**ReAct Process:**  
1. Web search for current inflation rate
2. Document search in last year's budget file
3. Calculator tool for adjustment calculations
4. Comprehensive budget planning response

The ReAct agent transforms simple questions into sophisticated, multi-step problem-solving workflows! 🎉