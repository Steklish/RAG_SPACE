import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ModelList() {
  const [models, setModels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        setIsLoading(true);
        const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/get_loaded_models`);
        setModels(response.data.models || []);
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
            models.map((model, index) => (
              <li key={index} className="model-item">
                <span className="model-name">{model}</span>
              </li>
            ))
          ) : (
            <p>No models loaded.</p>
          )}
        </ul>
      )}
    </div>
  );
}

export default ModelList;
