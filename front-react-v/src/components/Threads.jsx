import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Edit2, MessageSquare } from 'lucide-react';

function Threads({ currentThread, setCurrentThread, currentThreadDetails, threadsVersion }) {
  const [threads, setThreads] = useState([]);
  const [editingThreadId, setEditingThreadId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const inputRef = useRef(null);

  const fetchThreads = async () => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/threads`);
      setThreads(response.data || []);
    } catch (error) {
      console.error("Error fetching threads:", error);
      setThreads([]); // Reset on error
    }
  };

  useEffect(() => {
    fetchThreads();
  }, [threadsVersion]);

  useEffect(() => {
    if (currentThreadDetails) {
      setThreads(prevThreads =>
        prevThreads.map(thread => {
          if (thread.id === currentThreadDetails.id) {
            const updatedThread = { ...thread, ...currentThreadDetails };
            if (currentThreadDetails.document_ids) {
              updatedThread.document_count = currentThreadDetails.document_ids.length;
            }
            return updatedThread;
          }
          return thread;
        })
      );
    }
  }, [currentThreadDetails]);

  const createNewThread = async () => {
    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/threads`);
      const newThread = response.data;
      setThreads(prevThreads => [newThread, ...prevThreads]);
      setCurrentThread(newThread);
    } catch (error) {
      console.error("Error creating new thread:", error);
    }
  };
  const handleRenameStart = (thread) => {
    setEditingThreadId(thread.id);
    setEditingName(thread.name || '');
  };

  const handleRenameCancel = () => {
    setEditingThreadId(null);
    setEditingName('');
  };

  const handleRenameSave = async (threadId) => {
    if (!editingName.trim()) {
      handleRenameCancel();
      return;
    }
    try {
      await axios.put(`${import.meta.env.VITE_API_BASE_URL}/api/threads/${threadId}/rename`, { name: editingName });
      fetchThreads(); // Refresh the list
      if (currentThread?.id === threadId) {
        setCurrentThread(prev => ({ ...prev, name: editingName }));
      }
    } catch (error) {
      console.error("Error renaming thread:", error);
    } finally {
      handleRenameCancel();
    }
  };

  const handleKeyDown = (e, threadId) => {
    if (e.key === 'Enter') {
      handleRenameSave(threadId);
    } else if (e.key === 'Escape') {
      handleRenameCancel();
    }
  };

  const handleSelectThread = async (thread) => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/threads/${thread.id}/details`);
      setCurrentThread(response.data);
    } catch (error) {
      console.error("Error fetching thread details:", error);
    }
  };

  return (
    <div className="threads-panel">
      <div className="panel-header">
        <h2>Threads</h2>
        <button onClick={createNewThread} className="new-thread-btn">+</button>
      </div>
      <ul>
        {threads.length > 0 ? (
          threads.map(thread => (
            <li 
              key={thread.id} 
              className={currentThread?.id === thread.id ? 'active' : ''}
              onClick={() => !editingThreadId && setCurrentThread(thread)}
            >
              {editingThreadId === thread.id ? (
                <input
                  ref={inputRef}
                  type="text"
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  onBlur={() => handleRenameSave(thread.id)}
                  onKeyDown={(e) => handleKeyDown(e, thread.id)}
                  className="rename-input"
                />
              ) : (
                <>
                  <span className="thread-name">
                    <MessageSquare size={16} className="thread-icon" />
                    {thread.name || 'Untitled Thread'}
                  </span>
                  <div className="thread-meta">
                    {thread.document_count > 0 && (
                      <span className="doc-count-badge">{thread.document_count}</span>
                    )}
                    <div className="thread-actions">
                      <button onClick={() => handleRenameStart(thread)} className="icon-button">
                        <Edit2 size={16} />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </li>
          ))
        ) : (
          <li className="empty-state">No threads yet. Create one!</li>
        )}
      </ul>
    </div>
  );
}

export default Threads;