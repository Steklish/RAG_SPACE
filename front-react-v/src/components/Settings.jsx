/* eslint-disable no-unused-vars */
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './JsonEditPopup.css';

function Settings({ disabled }) {
  const [chatModel, setChatModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [serverUrls, setServerUrls] = useState({ chat_base_url: '', embed_base_url: '' });
  const [language, setLanguage] = useState('Russian');

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setIsLoading(true);
        const settingsPromise = axios.get(`${import.meta.env.VITE_API_BASE_URL}/api`);
        const urlsPromise = axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/server_urls`);
        
        const [settingsResponse, urlsResponse] = await Promise.all([settingsPromise, urlsPromise]);

        const settings = settingsResponse.data;
        setChatModel(settings.chat_model.model || 'Not available');
        setEmbeddingModel(settings.embedding_model.model || 'Not available');
        setLanguage(settings.language || 'English');
        setServerUrls(urlsResponse.data);

        setError(null);
      } catch (err) {
        setError('Failed to fetch initial settings.');
        console.error("Error fetching initial data:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchInitialData();
  }, []);

  const handleLanguageChange = async (e) => {
    const newLanguage = e.target.value;
    setLanguage(newLanguage);
    try {
      await axios.put(`${import.meta.env.VITE_API_BASE_URL}/api`, { language: newLanguage });
    } catch (err) {
      console.error("Error updating language:", err);
      setError("Failed to update language.");
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
              <h3>Language</h3>
              <select value={language} onChange={handleLanguageChange} disabled={disabled}>
                <option value="Russian">Russian</option>
                <option value="English">English</option>
              </select>
            </div>
            <div className="setting-item">
              <h3>Chat Server</h3>
              <p>Status: 
                {chatModel && chatModel !== 'Not available' 
                  ? <span className="status-indicator status-running">Connected</span> 
                  : <span className="status-indicator status-stopped">Not Connected</span>}
              </p>
              <p>URL: {serverUrls.chat_base_url}</p>
              <p>Model: {chatModel}</p>
            </div>

            <div className="setting-item">
              <h3>Embedding Server</h3>
              <p>Status: 
                {embeddingModel && embeddingModel !== 'Not available'
                  ? <span className="status-indicator status-running">Connected</span> 
                  : <span className="status-indicator status-stopped">Not Connected</span>}
              </p>
              <p>URL: {serverUrls.embed_base_url}</p>
              <p>Model: {embeddingModel}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Settings;