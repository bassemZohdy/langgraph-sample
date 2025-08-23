import { useState } from 'react';
import { MessageContent } from './MessageContent';

interface ReasoningStep {
  step: number;
  thought: string;
  action: string;
  action_params?: Record<string, any>;
}

interface ToolResult {
  step: number;
  tool_name: string;
  tool_params: Record<string, any>;
  success: boolean;
  content: string;
  error?: string;
  metadata?: any;
}

interface ReActMessageData {
  final_answer: string;
  reasoning_steps?: ReasoningStep[];
  tool_results?: ToolResult[];
  current_step?: number;
}

type Props = {
  content: string;
  theme?: 'light' | 'dark';
  showReasoningSteps?: boolean;
};

function isReActMessage(content: string): boolean {
  try {
    const parsed = JSON.parse(content);
    return parsed.final_answer || parsed.reasoning_steps || parsed.tool_results;
  } catch {
    return false;
  }
}

function parseReActContent(content: string): ReActMessageData | null {
  try {
    const parsed = JSON.parse(content);
    return parsed;
  } catch {
    return null;
  }
}

export function ReActMessage({ content, theme = 'dark', showReasoningSteps = true }: Props) {
  const [showDetails, setShowDetails] = useState(false);
  
  // Check if this is a ReAct message with reasoning steps
  if (!isReActMessage(content)) {
    // Regular message, use normal MessageContent
    return <MessageContent content={content} theme={theme} />;
  }
  
  const reactData = parseReActContent(content);
  if (!reactData) {
    return <MessageContent content={content} theme={theme} />;
  }
  
  const hasReasoningSteps = reactData.reasoning_steps && reactData.reasoning_steps.length > 0;
  const hasToolResults = reactData.tool_results && reactData.tool_results.length > 0;
  
  return (
    <div className="react-message">
      {/* Final Answer */}
      <div className="react-final-answer">
        <MessageContent content={reactData.final_answer} theme={theme} />
      </div>
      
      {/* Reasoning Steps Toggle */}
      {showReasoningSteps && (hasReasoningSteps || hasToolResults) && (
        <div className="react-reasoning-toggle">
          <button 
            className="reasoning-toggle-btn"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? '🧠 Hide Reasoning' : '🧠 Show Reasoning Process'}
            <span className="step-count">
              ({(reactData.reasoning_steps?.length || 0) + (reactData.tool_results?.length || 0)} steps)
            </span>
          </button>
        </div>
      )}
      
      {/* Detailed Reasoning Steps */}
      {showDetails && (
        <div className="react-reasoning-details">
          <div className="reasoning-header">
            <h4>🔍 Reasoning Process</h4>
          </div>
          
          {/* Interleave reasoning steps and tool results by step number */}
          {renderReasoningTimeline(reactData.reasoning_steps || [], reactData.tool_results || [])}
        </div>
      )}
    </div>
  );
}

function renderReasoningTimeline(reasoningSteps: ReasoningStep[], toolResults: ToolResult[]) {
  // Combine and sort by step number
  const allSteps: Array<{type: 'reasoning' | 'tool', step: number, data: any}> = [
    ...reasoningSteps.map(step => ({ type: 'reasoning' as const, step: step.step, data: step })),
    ...toolResults.map(result => ({ type: 'tool' as const, step: result.step, data: result }))
  ].sort((a, b) => a.step - b.step);
  
  return (
    <div className="reasoning-timeline">
      {allSteps.map((item, index) => (
        <div key={`${item.type}-${item.step}-${index}`} className={`timeline-item ${item.type}`}>
          {item.type === 'reasoning' ? (
            <ReasoningStepItem step={item.data} />
          ) : (
            <ToolResultItem result={item.data} />
          )}
        </div>
      ))}
    </div>
  );
}

function ReasoningStepItem({ step }: { step: ReasoningStep }) {
  return (
    <div className="reasoning-step">
      <div className="step-header">
        <span className="step-number">Step {step.step}</span>
        <span className="step-type">🤔 Reasoning</span>
      </div>
      <div className="step-content">
        <div className="thought">
          <strong>Thought:</strong> {step.thought}
        </div>
        <div className="action">
          <strong>Action:</strong> 
          <code className="action-name">{step.action}</code>
          {step.action_params && Object.keys(step.action_params).length > 0 && (
            <div className="action-params">
              {Object.entries(step.action_params).map(([key, value]) => (
                <span key={key} className="param">
                  {key}: <code>{String(value)}</code>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ToolResultItem({ result }: { result: ToolResult }) {
  const [showFullContent, setShowFullContent] = useState(false);
  const isLongContent = result.content && result.content.length > 300;
  const displayContent = showFullContent ? result.content : result.content?.slice(0, 300) + (isLongContent ? '...' : '');
  
  return (
    <div className={`tool-result ${result.success ? 'success' : 'error'}`}>
      <div className="step-header">
        <span className="step-number">Step {result.step}</span>
        <span className="step-type">
          {result.success ? '🛠️ Tool Result' : '❌ Tool Error'}
        </span>
      </div>
      <div className="step-content">
        <div className="tool-info">
          <strong>Tool:</strong> <code>{result.tool_name}</code>
          {result.tool_params && Object.keys(result.tool_params).length > 0 && (
            <div className="tool-params">
              {Object.entries(result.tool_params).map(([key, value]) => (
                <span key={key} className="param">
                  {key}: <code>{String(value)}</code>
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="tool-content">
          {result.success ? (
            <>
              <strong>Result:</strong>
              <div className="result-text">{displayContent}</div>
              {isLongContent && (
                <button 
                  className="show-more-btn"
                  onClick={() => setShowFullContent(!showFullContent)}
                >
                  {showFullContent ? 'Show Less' : 'Show More'}
                </button>
              )}
            </>
          ) : (
            <>
              <strong>Error:</strong>
              <div className="error-text">{result.error}</div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}