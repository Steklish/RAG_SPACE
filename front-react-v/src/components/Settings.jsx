/* eslint-disable no-unused-vars */
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import JsonEditPopup from './JsonEditPopup';
import './JsonEditPopup.css';

function Settings() {
  const [chatModel, setChatModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [serverConfigs, setServerConfigs] = useState({ chat: [], embedding: [] });
  const [selectedChatConfig, setSelectedChatConfig] = useState('');
  const [selectedEmbeddingConfig, setSelectedEmbeddingConfig] = useState('');
  const [serverStatus, setServerStatus] = useState({});
  const [launchConfigs, setLaunchConfigs] = useState([]);
  const [showJsonPopup, setShowJsonPopup] = useState(false);
  const [editingConfigName, setEditingConfigName] = useState('');
  const [language, setLanguage] = useState('Russian');

  const fetchServerStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/servers/status`);
      setServerStatus(response.data);
    } catch (err) {
      console.error("Error fetching server status:", err);
    }
  }, []);

  const fetchServerConfigs = useCallback(async () => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/servers/configs`);
      setServerConfigs(response.data);
    } catch (err) {
      console.error("Error fetching server configs:", err);
    }
  }, []);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setIsLoading(true);
        const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/settings`);
        const settings = response.data;

        setChatModel(settings.chat_model.model || 'Not available');
        setEmbeddingModel(settings.embedding_model.model || 'Not available');
        setServerConfigs(settings.server_configs);
        setLaunchConfigs(settings.launch_configs);
        setLanguage(settings.language || 'English');

        if (settings.active_configs.chat !== undefined) {
          setSelectedChatConfig(settings.active_configs.chat);
        }
        if (settings.active_configs.embedding !== undefined) {
          setSelectedEmbeddingConfig(settings.active_configs.embedding);
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

  const handleLanguageChange = async (e) => {
    const newLanguage = e.target.value;
    setLanguage(newLanguage);
    try {
      await axios.put(`${import.meta.env.VITE_API_BASE_URL}/api/settings`, { language: newLanguage });
    } catch (err) {
      console.error("Error updating language:", err);
      setError("Failed to update language.");
    }
  };

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

  const handleSaveJson = async (configName, content) => {
    try {
      await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/launch_configs/${configName}`, content);
      await fetchServerConfigs();
    } catch (err) {
      console.error(`Error saving ${configName}:`, err);
      setError(`Failed to save ${configName}.`);
    }
  };

  const handleSelectOther = (serverType) => {
    const configName = serverType === 'chat' ? 'chat_server.json' : 'embedding_server.json';
    setEditingConfigName(configName);
    setShowJsonPopup(true);
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
              <h3>Language</h3>
              <select value={language} onChange={handleLanguageChange}>
                <option value="Russian">Russian</option>
                <option value="English">English</option>
              </select>
            </div>
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
                onChange={(e) => {
                  if (e.target.value === 'other') {
                    handleSelectOther('chat');
                  } else {
                    setSelectedChatConfig(parseInt(e.target.value, 10));
                  }
                }}
              >
                {serverConfigs.chat.map((config, index) => (
                  <option key={index} value={index}>{config.name}</option>
                ))}
                <option value="other">Other...</option>
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
                onChange={(e) => {
                  if (e.target.value === 'other') {
                    handleSelectOther('embedding');
                  }
                  else {
                    setSelectedEmbeddingConfig(parseInt(e.target.value, 10));
                  }
                }}
              >
                {serverConfigs.embedding.map((config, index) => (
                  <option key={index} value={index}>{config.name}</option>
                ))}
                <option value="other">Other...</option>
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
      <JsonEditPopup 
        show={showJsonPopup}
        configName={editingConfigName}
        onClose={() => setShowJsonPopup(false)}
        onSave={handleSaveJson}
      />
    </div>
  );
}

export default Settings;