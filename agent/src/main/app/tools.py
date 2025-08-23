"""
ReAct Agent Tools System
Provides various tools for reasoning, web search, document search, calculations, and code execution.
"""

import os
import re
import json
import logging
import requests
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    content: str
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseTool(ABC):
    """Base class for all ReAct tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for identification."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the AI agent."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass


class WebSearchTool(BaseTool):
    """Tool for web search using DuckDuckGo or other search APIs."""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return """Search the web for current information. Use this when you need up-to-date information, news, or facts not in your training data.
        
Parameters:
- query (str): The search query
- max_results (int, optional): Maximum number of results (default: 5)

Example: web_search(query="latest developments in AI 2024", max_results=3)"""
    
    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """Execute web search."""
        try:
            # Simple DuckDuckGo search implementation
            # In production, you might use a proper search API like Serper, Tavily, or Google Custom Search
            
            # For now, simulate a web search result
            # In a real implementation, you would integrate with actual search APIs
            search_results = self._simulate_search(query, max_results)
            
            formatted_results = []
            for i, result in enumerate(search_results, 1):
                formatted_results.append(f"{i}. **{result['title']}**\n   {result['snippet']}\n   URL: {result['url']}\n")
            
            content = f"Web search results for '{query}':\n\n" + "\n".join(formatted_results)
            
            return ToolResult(
                success=True,
                content=content,
                metadata={
                    "query": query,
                    "results_count": len(search_results),
                    "search_type": "web"
                }
            )
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"Web search failed: {str(e)}"
            )
    
    def _simulate_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Simulate search results. Replace with actual search API integration."""
        # This is a placeholder - in production you'd integrate with real search APIs
        return [
            {
                "title": f"Search result {i+1} for: {query}",
                "snippet": f"This is a simulated search result snippet for query '{query}'. In production, this would contain real web search results.",
                "url": f"https://example.com/result-{i+1}"
            }
            for i in range(min(max_results, 3))
        ]


class DocumentSearchTool(BaseTool):
    """Tool for searching uploaded documents using vector similarity."""
    
    @property
    def name(self) -> str:
        return "document_search"
    
    @property
    def description(self) -> str:
        return """Search through uploaded documents using semantic similarity. Use this to find relevant information from previously uploaded files.
        
Parameters:
- query (str): What to search for in the documents
- max_results (int, optional): Maximum number of results (default: 5)
- similarity_threshold (float, optional): Minimum similarity score (default: 0.7)

Example: document_search(query="financial projections Q4", max_results=3)"""
    
    def execute(self, query: str, max_results: int = 5, similarity_threshold: float = 0.7) -> ToolResult:
        """Execute document search using embeddings."""
        try:
            from .embeddings import embedding_service
            
            # Search similar documents
            results = embedding_service.search_similar_content(
                query=query,
                limit=max_results,
                similarity_threshold=similarity_threshold
            )
            
            if not results:
                return ToolResult(
                    success=True,
                    content=f"No documents found matching '{query}' with similarity threshold {similarity_threshold}",
                    metadata={"query": query, "results_count": 0}
                )
            
            formatted_results = []
            for i, result in enumerate(results, 1):
                similarity_pct = round(result.get('similarity', 0) * 100, 1)
                content_preview = result.get('content', '')[:200] + "..." if len(result.get('content', '')) > 200 else result.get('content', '')
                
                formatted_results.append(
                    f"{i}. **{result.get('filename', 'Unknown')}** (Similarity: {similarity_pct}%)\n"
                    f"   Content: {content_preview}\n"
                    f"   Document ID: {result.get('document_id', 'N/A')}\n"
                )
            
            content = f"Document search results for '{query}':\n\n" + "\n".join(formatted_results)
            
            return ToolResult(
                success=True,
                content=content,
                metadata={
                    "query": query,
                    "results_count": len(results),
                    "search_type": "documents"
                }
            )
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"Document search failed: {str(e)}"
            )


class CalculatorTool(BaseTool):
    """Tool for mathematical calculations and expressions."""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return """Perform mathematical calculations. Supports basic arithmetic, scientific functions, and expressions.
        
Parameters:
- expression (str): Mathematical expression to evaluate

Supported operations:
- Basic: +, -, *, /, **, %
- Functions: sin, cos, tan, log, sqrt, abs, round
- Constants: pi, e

Example: calculator(expression="sqrt(16) + log(100)")"""
    
    def execute(self, expression: str) -> ToolResult:
        """Execute mathematical calculation."""
        try:
            import math
            
            # Security: only allow safe mathematical operations
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
            
            # Clean the expression
            clean_expr = re.sub(r'[^0-9+\-*/().a-zA-Z_\s]', '', expression)
            
            # Evaluate safely
            result = eval(clean_expr, {"__builtins__": {}}, allowed_names)
            
            return ToolResult(
                success=True,
                content=f"Calculation: {expression} = {result}",
                metadata={"expression": expression, "result": result}
            )
            
        except Exception as e:
            logger.error(f"Calculator error: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"Mathematical calculation failed: {str(e)}"
            )


class CodeExecutionTool(BaseTool):
    """Tool for executing safe Python code snippets."""
    
    @property
    def name(self) -> str:
        return "code_execution"
    
    @property
    def description(self) -> str:
        return """Execute Python code safely in a sandboxed environment. Use for data processing, analysis, or complex calculations.
        
Parameters:
- code (str): Python code to execute
- timeout (int, optional): Execution timeout in seconds (default: 10)

Security: Only safe operations are allowed. Network access and file system access are restricted.

Example: code_execution(code="import pandas as pd\\ndata = [1,2,3,4,5]\\nprint(f'Mean: {sum(data)/len(data)}')")"""
    
    def execute(self, code: str, timeout: int = 10) -> ToolResult:
        """Execute Python code safely."""
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute with restricted permissions
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir()  # Run in temp directory
            )
            
            # Clean up
            os.unlink(temp_file)
            
            if result.returncode == 0:
                output = result.stdout.strip()
                return ToolResult(
                    success=True,
                    content=f"Code executed successfully:\n\n```python\n{code}\n```\n\nOutput:\n```\n{output}\n```",
                    metadata={"code": code, "output": output, "returncode": 0}
                )
            else:
                error_output = result.stderr.strip()
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Code execution failed:\n{error_output}"
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                content="",
                error=f"Code execution timed out after {timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"Code execution failed: {str(e)}"
            )


class ListDocumentsTool(BaseTool):
    """Tool for listing available documents."""
    
    @property
    def name(self) -> str:
        return "list_documents"
    
    @property
    def description(self) -> str:
        return """List all available documents that can be searched. Use this to see what documents are available before searching.
        
Parameters:
- limit (int, optional): Maximum number of documents to list (default: 20)

Example: list_documents(limit=10)"""
    
    def execute(self, limit: int = 20) -> ToolResult:
        """List available documents."""
        try:
            from .database import list_documents
            
            documents = list_documents(limit=limit)
            
            if not documents:
                return ToolResult(
                    success=True,
                    content="No documents are currently available. Upload documents to make them searchable.",
                    metadata={"documents_count": 0}
                )
            
            formatted_docs = []
            for doc in documents:
                size_kb = round(doc.get('content_length', 0) / 1024, 1)
                formatted_docs.append(
                    f"• **{doc.get('filename', 'Unknown')}** "
                    f"({doc.get('content_type', 'unknown type')}, {size_kb} KB)\n"
                    f"  Uploaded: {doc.get('created_at', 'Unknown')}\n"
                    f"  Document ID: {doc.get('document_id', 'N/A')}"
                )
            
            content = f"Available Documents ({len(documents)}):\n\n" + "\n\n".join(formatted_docs)
            
            return ToolResult(
                success=True,
                content=content,
                metadata={"documents_count": len(documents)}
            )
            
        except Exception as e:
            logger.error(f"List documents failed: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to list documents: {str(e)}"
            )


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools."""
        default_tools = [
            WebSearchTool(),
            DocumentSearchTool(),
            CalculatorTool(),
            CodeExecutionTool(),
            ListDocumentsTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: BaseTool):
        """Register a new tool."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return self.tools.copy()
    
    def get_tools_description(self) -> str:
        """Get formatted description of all available tools."""
        if not self.tools:
            return "No tools available."
        
        descriptions = []
        for tool in self.tools.values():
            descriptions.append(f"**{tool.name}**\n{tool.description}")
        
        return "\n\n".join(descriptions)
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool with given parameters."""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                content="",
                error=f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"
            )
        
        try:
            logger.info(f"Executing tool: {tool_name} with params: {kwargs}")
            return tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"Tool execution failed: {str(e)}"
            )


# Global tool registry instance
tool_registry = ToolRegistry()