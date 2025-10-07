import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ModelList() {
  const [models, setModels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeChatModel, setActiveChatModel] = useState('');
  const [activeEmbeddingModel, setActiveEmbeddingModel] = useState('');

  useEffect(() => {
    const fetchModels = async () => {
      try {
        setIsLoading(true);
        const [modelsResponse, configsResponse, activeConfigsResponse] = await Promise.all([
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/get_loaded_models`),
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/servers/configs`),
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/servers/active_configs`)
        ]);

        setModels(modelsResponse.data.models || []);
        
        const configs = configsResponse.data;
        const activeConfigs = activeConfigsResponse.data;

        if (configs.chat && activeConfigs.chat !== undefined && configs.chat[activeConfigs.chat]) {
          setActiveChatModel(configs.chat[activeConfigs.chat].name);
        }
        if (configs.embedding && activeConfigs.embedding !== undefined && configs.embedding[activeConfigs.embedding]) {
          setActiveEmbeddingModel(configs.embedding[activeConfigs.embedding].name);
        }

        setError(null);
      } catch (err) {
        setError('Failed to fetch models.');
        console.error("Error fetching models:", err);
        setModels([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchModels();
  }, []);

  return (
    <div className="model-list-container">
      <h4>Loaded Models</h4>
      {isLoading && <p>Loading models...</p>}
      {error && <p className="error-message">{error}</p>}
      {!isLoading && !error && (
        <ul className="model-list">
          {models.length > 0 ? (
            models.map((model, index) => {
              const isChat = model === activeChatModel;
              const isEmbedding = model === activeEmbeddingModel;
              let className = "model-item";
              if (isChat) className += " active-model-chat";
              if (isEmbedding) className += " active-model-embedding";

              return (
                <li key={index} className={className}>
                  <span className="model-name">{model}</span>
                  {isChat && <span className="model-label-chat"> (Chat)</span>}
                  {isEmbedding && <span className="model-label-embedding"> (Embedding)</span>}
                </li>
              );
            })
          ) : (
            <p>No models loaded.</p>
          )}
        </ul>
      )}
    </div>
  );
}

export default ModelList;
