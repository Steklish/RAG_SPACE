import React from 'react';
import './LoadingIndicator.css';

const LoadingIndicator = () => {
  return (
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p>Loading model...</p>
    </div>
  );
};

export default LoadingIndicator;