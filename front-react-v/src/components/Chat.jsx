/* eslint-disable no-unused-vars */
import React, { useState, useEffect } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import LoadingIndicator from './LoadingIndicator';
import axios from 'axios';

function Chat({ currentThread, onThreadUpdate }) {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isThinking, setIsThinking] = useState(false);

  useEffect(() => {
    if (currentThread) {
      const formattedHistory = (currentThread.history || []).map((msg, index) => ({
        id: `hist-${index}`,
        text: msg.content,
        sender: msg.sender,
        retrieved_docs: msg.retrieved_docs || [],
        follow_up: msg.follow_up || false,
      }));
      setMessages(formattedHistory);
    } else {
      setMessages([]);
    }
  }, [currentThread]);

  const handleDeleteMessage = async (messageIndex) => {
    if (!currentThread) return;
    try {
      await axios.delete(`${import.meta.env.VITE_API_BASE_URL}/api/threads/${currentThread.id}/messages/${messageIndex}`);
      onThreadUpdate(); // Refetch thread details to update the message list
    } catch (error) {
      console.error("Error deleting message:", error);
    }
  };

  const handleSendMessage = (text) => {
    if (!currentThread) return;

    const userMessage = { id: Date.now(), text, sender: 'user' };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setIsStreaming(true);
    setIsThinking(false);

    const url = `${import.meta.env.VITE_API_BASE_URL}/api/threads/${currentThread.id}/chat`;
    const botMessage = { id: Date.now() + 1, text: '', sender: 'agent', retrieved_docs: [], follow_up: false };
    
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
				  const eventData = JSON.parse(JSON.parse(jsonStr).data);
                  if (eventData.answer.startsWith('<internal>')) {
                    setIsThinking(true);
                    return; // Don't display internal messages
                  }
                  setIsThinking(false);
				  console.log(eventData)
              setMessages(prev => prev.map(msg => 
				msg.id === botMessage.id 
                ? { ...msg, text: msg.text + eventData.answer, retrieved_docs: eventData.retrieved_docs || [], follow_up: eventData.follow_up || false }
                : msg
              ));
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
        setIsThinking(false);
      }
    };
    
    postAndStream();
  };

  return (
    <div className="chat-panel">
      {currentThread ? (
        <>
          <MessageList messages={messages} onDeleteMessage={handleDeleteMessage} isThinking={isThinking} />
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
