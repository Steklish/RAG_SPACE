import React, { useState } from 'react';

const ChatInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');
  const [useDbExplorer, setUseDbExplorer] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message, useDbExplorer);
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-form" autoComplete="off">
      <div className="input-wrapper">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={disabled ? "Waiting for response..." : "Type a message..."}
          className="chat-input"
          disabled={disabled}
          autoComplete="new-password"
        />
        <button type="submit" className="send-button" disabled={disabled}>
          Send
        </button>
      </div>
      <div className="checkbox-wrapper">
        <input
          type="checkbox"
          id="db-explorer"
          checked={useDbExplorer}
          onChange={(e) => setUseDbExplorer(e.target.checked)}
          disabled={disabled}
        />
        <label htmlFor="db-explorer">database explorer</label>
      </div>
    </form>
  );
};

export default ChatInput;
