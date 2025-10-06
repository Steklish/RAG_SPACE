import React, { useState, useEffect } from 'react';
import axios from 'axios';

function Settings() {
  const [availableModels, setAvailableModels] = useState([]);
  const [chatModel, setChatModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        setIsLoading(true);
        const [available, chat, embedding] = await Promise.all([
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/get_loaded_models`),
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/chat_model`),
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/embedding_model`)
        ]);
        setAvailableModels(available.data.models || []);
        setChatModel(chat.data.model || '');
        setEmbeddingModel(embedding.data.model || '');
        setError(null);
      } catch (err) {
        setError('Failed to fetch model information.');
        console.error("Error fetching models:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchModels();
  }, []);

  const handleChatModelChange = (e) => {
    setChatModel(e.target.value);
  };

  const handleEmbeddingModelChange = (e) => {
    setEmbeddingModel(e.target.value);
  };

  return (
    <div className="settings-panel">
      <div className="panel-header">
        <h2>Settings</h2>
      </div>
      <div className="settings-content">
        {isLoading && <p>Loading settings...</p>}
        {error && <p className="error-message">{error}</p>}
        {!isLoading && !error && (
          <>
            <div className="setting-item">
              <label htmlFor="chat-model-select">Chat Model</label>
              <select id="chat-model-select" value={chatModel} onChange={handleChatModelChange}>
                {availableModels.map((model, index) => (
                  <option key={index} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>
            <div className="setting-item">
              <label htmlFor="embedding-model-select">Embedding Model</label>
              <select id="embedding-model-select" value={embeddingModel} onChange={handleEmbeddingModelChange}>
                {availableModels.map((model, index) => (
                  <option key={index} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Settings;