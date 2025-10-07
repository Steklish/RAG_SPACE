import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

function Settings() {
  const [chatModel, setChatModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [serverConfigs, setServerConfigs] = useState({ chat: [], embedding: [] });
  const [selectedChatConfig, setSelectedChatConfig] = useState('');
  const [selectedEmbeddingConfig, setSelectedEmbeddingConfig] = useState('');
  const [serverStatus, setServerStatus] = useState({});

  const fetchServerStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/servers/status`);
      setServerStatus(response.data);
    } catch (err) {
      console.error("Error fetching server status:", err);
    }
  }, []);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setIsLoading(true);
        const [chat, embedding, configs, activeConfigs] = await Promise.all([
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/chat_model`),
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/embedding_model`),
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/servers/configs`),
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/servers/active_configs`)
        ]);
        
        setChatModel(chat.data.model || 'Not available');
        setEmbeddingModel(embedding.data.model || 'Not available');
        setServerConfigs(configs.data);

        if (activeConfigs.data.chat !== undefined) {
          setSelectedChatConfig(activeConfigs.data.chat);
        }
        if (activeConfigs.data.embedding !== undefined) {
          setSelectedEmbeddingConfig(activeConfigs.data.embedding);
        }
        
        await fetchServerStatus();
        setError(null);
      } catch (err) {
        setError('Failed to fetch initial settings.');
        console.error("Error fetching initial data:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchInitialData();
    const interval = setInterval(fetchServerStatus, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [fetchServerStatus]);

  const handleServerAction = async (serverType, configName, action, configIndex = 0) => {
    try {
      if (action === 'update_config') {
        await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/servers/update_config`, {
          server_type: serverType,
          config_name: configName,
          config_index: configIndex
        });
      } else {
        await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/servers/${action}`, {
          server_type: serverType,
          config_name: configName
        });
      }
      await fetchServerStatus();
    } catch (err) {
      console.error(`Error ${action}ing server ${serverType}:`, err);
      setError(`Failed to ${action} ${serverType} server.`);
    }
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
              <h3>Chat Server</h3>
              <p>Status: 
                {serverStatus.chat 
                  ? <span className="status-indicator status-running">Running</span> 
                  : <span className="status-indicator status-stopped">Stopped</span>}
              </p>
              <p>Model: {chatModel}</p>
              <label htmlFor="chat-config-select">Configuration</label>
              <select 
                id="chat-config-select" 
                value={selectedChatConfig} 
                onChange={(e) => setSelectedChatConfig(e.target.value)}
              >
                {serverConfigs.chat.map((config, index) => (
                  <option key={index} value={index}>{config.name}</option>
                ))}
              </select>
              {!serverStatus.chat ? (
                <div className="button-group">
                  <button onClick={() => handleServerAction('chat', 'chat_server.json', 'start')}>Start</button>
                </div>
              ) : (
                <div className="button-group">
                  <button className="stop-button" onClick={() => handleServerAction('chat', 'chat_server.json', 'stop')}>Stop</button>
                  <button onClick={() => handleServerAction('chat', 'chat_server.json', 'update_config', selectedChatConfig)}>Save & Restart</button>
                </div>
              )}
            </div>

            <div className="setting-item">
              <h3>Embedding Server</h3>
              <p>Status: 
                {serverStatus.embedding 
                  ? <span className="status-indicator status-running">Running</span> 
                  : <span className="status-indicator status-stopped">Stopped</span>}
              </p>
              <p>Model: {embeddingModel}</p>
              <label htmlFor="embedding-config-select">Configuration</label>
              <select 
                id="embedding-config-select" 
                value={selectedEmbeddingConfig} 
                onChange={(e) => setSelectedEmbeddingConfig(e.target.value)}
              >
                {serverConfigs.embedding.map((config, index) => (
                  <option key={index} value={index}>{config.name}</option>
                ))}
              </select>
              {!serverStatus.embedding ? (
                <div className="button-group">
                  <button onClick={() => handleServerAction('embedding', 'embedding_server.json', 'start')}>Start</button>
                </div>
              ) : (
                <div className="button-group">
                  <button className="stop-button" onClick={() => handleServerAction('embedding', 'embedding_server.json', 'stop')}>Stop</button>
                  <button onClick={() => handleServerAction('embedding', 'embedding_server.json', 'update_config', selectedEmbeddingConfig)}>Save & Restart</button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Settings;