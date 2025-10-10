import React from 'react';
import './LoadingIndicator.css';

const LoadingIndicator = () => {
  return (
    <div className="loading-dots">
      <span>.</span><span>.</span><span>.</span>
    </div>
  );
};

export default LoadingIndicator;