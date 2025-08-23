import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

type Props = {
  content: string;
  theme?: 'light' | 'dark';
};


function parseMessageContent(content: string): Array<{ type: 'text' | 'code'; content: string; language?: string }> {
  const parts: Array<{ type: 'text' | 'code'; content: string; language?: string }> = [];
  
  // Regex to match code blocks with optional language
  const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    // Add text before code block
    if (match.index > lastIndex) {
      const textContent = content.slice(lastIndex, match.index).trim();
      if (textContent) {
        parts.push({ type: 'text', content: textContent });
      }
    }

    // Add code block
    const language = match[1] || 'text';
    const code = match[2] || '';
    parts.push({ 
      type: 'code', 
      content: code.trim(), 
      language: language.toLowerCase() 
    });

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after last code block
  if (lastIndex < content.length) {
    const textContent = content.slice(lastIndex).trim();
    if (textContent) {
      parts.push({ type: 'text', content: textContent });
    }
  }

  // If no code blocks found, return the entire content as text
  if (parts.length === 0) {
    parts.push({ type: 'text', content: content });
  }

  return parts;
}

function renderTextWithInlineCode(text: string): JSX.Element {
  // Handle inline code blocks (`code`)
  const parts = text.split(/(`[^`]+`)/g);
  
  return (
    <span>
      {parts.map((part, index) => {
        if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
          const code = part.slice(1, -1);
          return (
            <code key={index} className="inline-code">
              {code}
            </code>
          );
        }
        
        // Convert newlines to <br> tags for text parts
        return (
          <span key={index}>
            {part.split('\n').map((line, lineIndex, lines) => (
              <span key={lineIndex}>
                {line}
                {lineIndex < lines.length - 1 && <br />}
              </span>
            ))}
          </span>
        );
      })}
    </span>
  );
}

export function MessageContent({ content, theme = 'dark' }: Props) {
  const parts = parseMessageContent(content);
  
  // Determine the syntax highlighter theme based on the app theme
  const syntaxTheme = theme === 'dark' ? oneDark : oneLight;
  
  return (
    <div className="message-content">
      {parts.map((part, index) => {
        if (part.type === 'code') {
          return (
            <div key={index} className="code-block-container">
              <div className="code-block-header">
                <span className="code-language">{part.language}</span>
                <button 
                  className="copy-button"
                  onClick={() => navigator.clipboard.writeText(part.content)}
                  title="Copy code"
                >
                  Copy
                </button>
              </div>
              <SyntaxHighlighter
                language={part.language}
                style={syntaxTheme}
                customStyle={{
                  margin: 0,
                  borderRadius: '0 0 8px 8px',
                  fontSize: '13px',
                }}
                wrapLongLines={true}
              >
                {part.content}
              </SyntaxHighlighter>
            </div>
          );
        } else {
          return (
            <div key={index} className="text-content">
              {renderTextWithInlineCode(part.content)}
            </div>
          );
        }
      })}
    </div>
  );
}