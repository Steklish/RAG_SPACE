import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import LoadingIndicator from './LoadingIndicator';
import remarkGfm from 'remark-gfm';

const MessageList = ({ messages, onDeleteMessage, isStreaming }) => {
  const messagesEndRef = useRef(null);
  const [expandedSources, setExpandedSources] = useState({});

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const toggleSources = (index) => {
    setExpandedSources(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const components = {
    table: ({ ...props}) => <div className="table-container"><table {...props} /></div>
  };

  return (
    <div className="message-list">
      {messages.map((msg, index) => (
        <div key={index} className="message-container">
          <div className={`message ${msg.sender} ${msg.follow_up ? 'follow-up' : ''}`}>
            <ReactMarkdown components={components} remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
            {msg.sender === 'agent' && msg.retrieved_docs && Array.isArray(msg.retrieved_docs) && msg.retrieved_docs.length > 0 && (
              <div className="retrieved-docs">
                <button onClick={() => toggleSources(index)} className="sources-toggle-button">
                  {expandedSources[index] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  <strong>Sources ({msg.retrieved_docs.length})</strong>
                </button>
                {expandedSources[index] && (
                  <ul>
                    {msg.retrieved_docs.map((doc, i) => (
                      <li key={i}>
                        {doc.id == "SQL" ? (
                          // TRUE: If doc.id starts with '[query]', display as a code block
                          <pre>
                            <code>{doc.name}</code>
                          </pre>
                        ) : (
                          // FALSE: Otherwise, display as the original link
                          <a href={`/documents/${doc.id}`} onClick={(e) => e.preventDefault()}>
                            <FileText size={14} />
                            {doc.name} ({doc.id.substring(0, 8)}...)
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
          <button 
            className="delete-message-btn icon-button" 
            onClick={() => onDeleteMessage(index)}
          >
            <Trash2 size={16} />
          </button>
        </div>
      ))}
      {isStreaming && <LoadingIndicator />}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;