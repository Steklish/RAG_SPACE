/* eslint-disable no-unused-vars */
import React, { useState, useEffect } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import LoadingIndicator from './LoadingIndicator';

function Chat({ currentThread }) {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    if (currentThread) {
      const formattedHistory = (currentThread.history || []).map((msg, index) => ({
        id: `hist-${index}`,
        text: msg,
        sender: index % 2 === 0 ? 'user' : 'bot',
      }));
      setMessages(formattedHistory);
    } else {
      setMessages([]);
    }
  }, [currentThread]);

  const handleSendMessage = (text) => {
    if (!currentThread) return;

    const userMessage = { id: Date.now(), text, sender: 'user' };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setIsStreaming(true);

    const url = `${import.meta.env.VITE_API_BASE_URL}/api/threads/${currentThread.id}/chat`;
    const botMessage = { id: Date.now() + 1, text: '', sender: 'bot' };
    
    // Add a placeholder for the bot's message immediately
    setMessages(prev => [...prev, botMessage]);

    const postAndStream = async () => {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: text }),
        });

        if (!response.body) return;
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let streaming = true;
        while (streaming) {
          const { done, value } = await reader.read();
          if (done) {
            streaming = false;
            break;
          }
          
          const chunk = decoder.decode(value, { stream: true });
          const jsonStrings = chunk.replace(/^data: /, '').split('\n\n').filter(s => s);
          
          jsonStrings.forEach(jsonStr => {
            try {
              const eventData = JSON.parse(jsonStr);
              if (eventData.type === 'chunk') {
                setMessages(prev => prev.map(msg => 
                  msg.id === botMessage.id 
                  ? { ...msg, text: msg.text + eventData.data }
                  : msg
                ));
              }
            } catch (e) {
              // Ignore parsing errors
            }
          });
        }
      } catch (error) {
        console.error("Streaming failed:", error);
        setMessages(prev => prev.map(msg => 
          msg.id === botMessage.id 
          ? { ...msg, text: msg.text + '\n[Error receiving response]' }
          : msg
        ));
      } finally {
        setIsStreaming(false);
      }
    };
    
    postAndStream();
  };

  return (
    <div className="chat-panel">
      {currentThread ? (
        <>
          <MessageList messages={messages} />
          {isStreaming && <LoadingIndicator />}
          <ChatInput onSendMessage={handleSendMessage} disabled={isStreaming} />
        </>
      ) : (
        <div className="empty-state centered">
          <h2>Select a thread to start chatting</h2>
        </div>
      )}
    </div>
  );
}

export default Chat;
