import React, { useEffect, useRef } from 'react';
import { FileText, Trash2 } from 'lucide-react';

const MessageList = ({ messages, onDeleteMessage }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="message-list">
      {messages.map((msg, index) => (
        <div key={index} className="message-container">
          <div className={`message ${msg.sender}`}>
            {msg.text}
            {msg.sender === 'agent' && msg.retrieved_docs && Array.isArray(msg.retrieved_docs) && msg.retrieved_docs.length > 0 && (
              <div className="retrieved-docs">
                <strong>Sources:</strong>
                <ul>
                  {msg.retrieved_docs.map((doc, i) => (
                    <li key={i}>
                      <a href={`/documents/${doc.id}`} onClick={(e) => e.preventDefault()}>
                        <FileText size={14} />
                        {doc.name} ({doc.id.substring(0, 8)}...)
                      </a>
                    </li>
                  ))}
                </ul>
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
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;