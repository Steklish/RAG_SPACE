import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

function JsonEditPopup({ configName, show, onClose, onSave }) {
  const [content, setContent] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (show) {
      fetchConfig();
    }
  }, [show, configName]);

  const fetchConfig = async () => {
    try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/launch_configs/${configName}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setContent(JSON.stringify(data, null, 2));
    } catch (e) {
        setError('Failed to fetch config: ' + e.message);
    }
  };

  const handleSave = async () => {
    try {
      const parsedContent = JSON.parse(content);
      await onSave(configName, parsedContent);
      onClose();
    } catch (e) {
      setError('Invalid JSON format: ' + e.message);
    }
  };

  if (!show) {
    return null;
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-content settings-panel">
        <div className="panel-header">
          <h2>Edit {configName}</h2>
        </div>
        {error && <p className="error-message">{error}</p>}
        <textarea
          className="chat-input"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows="20"
        />
        <div className="setting-item .button-group">
          <button className="setting-item button" onClick={handleSave}>Save</button>
          <button className="setting-item button" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

JsonEditPopup.propTypes = {
  configName: PropTypes.string.isRequired,
  show: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
};

export default JsonEditPopup;
