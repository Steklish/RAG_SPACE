import React from 'react';
import { File, FileText, FileJson, FileCode } from 'lucide-react';

const FileIcon = ({ filename }) => {
  const getExtension = (name) => {
    if (typeof name !== 'string' || name.indexOf('.') === -1) {
      return '';
    }
    return name.split('.').pop().toLowerCase();
  };

  const extension = getExtension(filename);

  const getIcon = () => {
    switch (extension) {
      case 'pdf':
        return <FileText size={18} color="#e53e3e" />;
      case 'txt':
        return <FileText size={18} color="#4a5568" />;
      case 'json':
        return <FileJson size={18} color="#38a169" />;
      case 'js':
      case 'jsx':
      case 'ts':
      case 'tsx':
      case 'py':
      case 'css':
      case 'html':
        return <FileCode size={18} color="#3182ce" />;
      default:
        return <File size={18} color="#a0aec0" />;
    }
  };

  return <span className="file-icon">{getIcon()}</span>;
};

export default FileIcon;
