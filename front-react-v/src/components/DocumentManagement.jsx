import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import FileDropzone from './FileDropzone';
import FileIcon from './FileIcon';
import { PlusCircle, Trash2 } from 'lucide-react'; // Using lucide-react for icons

function DocumentManagement({ currentThread, onThreadUpdate }) {
  const [activeTab, setActiveTab] = useState('Global');
  const [globalFiles, setGlobalFiles] = useState([]);
  const [threadFiles, setThreadFiles] = useState([]);

  const fetchGlobalFiles = useCallback(async () => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/documents`);
      setGlobalFiles(response.data || []);
    } catch (error) {
      console.error("Error fetching global files:", error);
    }
  }, []);

  const fetchThreadFiles = useCallback(async () => {
    if (!currentThread) {
      setThreadFiles([]);
      return;
    }
    try {
        const response = await axios.get('http://127.0.0.1:8000/api/documents');
        const allDocs = response.data || [];
        const threadDocIds = new Set(currentThread.document_ids || []);
        setThreadFiles(allDocs.filter(doc => threadDocIds.has(doc.id)));
    } catch (error) {
        console.error("Error fetching thread files:", error);
        setThreadFiles([]);
    }
  }, [currentThread]);

  useEffect(() => {
    fetchGlobalFiles();
    fetchThreadFiles();
  }, [fetchGlobalFiles, fetchThreadFiles]);

  const handleFilesDrop = useCallback(async (acceptedFiles) => {
    const formData = new FormData();
    acceptedFiles.forEach(file => formData.append('files', file));
    try {
      await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/documents`, formData);
      fetchGlobalFiles(); // Refresh global list
    } catch (error) {
      console.error("Error uploading files:", error);
    }
  }, [fetchGlobalFiles]);

  const handleDeleteDocument = async (docId) => {
    try {
      await axios.delete(`${import.meta.env.VITE_API_BASE_URL}/api/documents/${docId}`);
      fetchGlobalFiles(); // Refresh global list
    } catch (error) {
      console.error("Error deleting document:", error);
    }
  };

  const handleAddDocToThread = async (docId) => {
    if (!currentThread) return;
    try {
      await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/threads/${currentThread.id}/documents`, { document_id: docId });
      fetchThreadFiles(); // Refresh thread list
      if(onThreadUpdate) onThreadUpdate(); // Notify parent to refetch thread details
    } catch (error) {
      console.error("Error adding document to thread:", error);
    }
  };

  const renderFileActions = (doc) => {
    if (activeTab === 'Global') {
      return (
        <div className="file-actions">
          <button 
            onClick={() => handleAddDocToThread(doc.id)} 
            disabled={!currentThread}
            title={currentThread ? "Add to current thread" : "Select a thread to add"}
            className="icon-button"
          >
            <PlusCircle size={18} />
          </button>
          <button 
            onClick={() => handleDeleteDocument(doc.id)}
            title="Delete globally"
            className="icon-button"
          >
            <Trash2 size={18} />
          </button>
        </div>
      );
    }
    // Potentially add a remove-from-thread button here in the future
    return null; 
  };

  const filesToShow = activeTab === 'Global' ? globalFiles : threadFiles;

  return (
    <div className="document-management-panel">
      <h2>Files</h2>
      <div className="tabs">
        <button onClick={() => setActiveTab('Global')} className={activeTab === 'Global' ? 'active' : ''}>Global</button>
        <button onClick={() => setActiveTab('Thread')} className={activeTab === 'Thread' ? 'active' : ''}>Thread</button>
      </div>
      <ul className="document-list">
        {filesToShow.map(doc => (
          <li key={doc.id}>
            <span className="file-name">
              <FileIcon filename={doc.name} />
              {doc.name}
            </span>
            {renderFileActions(doc)}
          </li>
        ))}
      </ul>
      <FileDropzone onFilesDrop={handleFilesDrop} />
    </div>
  );
}

export default DocumentManagement;
