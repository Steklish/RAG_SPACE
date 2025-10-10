import React, { useState, useEffect, useCallback } from 'react';
import Split from 'react-split';
import axios from 'axios';
import Threads from './components/Threads';
import Chat from './components/Chat';
import DocumentManagement from './components/DocumentManagement';
import Settings from './components/Settings';
import LoadingIndicator from './components/LoadingIndicator';
import './App.css';

function App() {
  const [currentThread, setCurrentThread] = useState(null);
  const [currentThreadDetails, setCurrentThreadDetails] = useState(null);
  const [serverStatus, setServerStatus] = useState('loading');
  const [threadsVersion, setThreadsVersion] = useState(0);

  const forceThreadsRefetch = () => {
    setThreadsVersion(v => v + 1);
  };

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/status`);
        if (response.data.status === 'ready' || response.data.status === 'error') {
          setServerStatus(response.data.status);
        } else {
          setTimeout(pollStatus, 2000);
        }
      } catch (error) {
        console.error("Error polling server status:", error);
        setServerStatus('error');
      }
    };
    pollStatus();
  }, []);

  const fetchThreadDetails = useCallback(async () => {
    if (currentThread) {
      try {
        const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/threads/${currentThread.id}/details`);
        setCurrentThreadDetails(response.data);
      } catch (error) {
        console.error("Error fetching thread details:", error);
        setCurrentThreadDetails(null);
      }
    } else {
      setCurrentThreadDetails(null);
    }
  }, [currentThread]);

  useEffect(() => {
    fetchThreadDetails();
  }, [fetchThreadDetails]);

  if (serverStatus === 'loading') {
    return <LoadingIndicator />;
  }

  if (serverStatus === 'error') {
    return <div className="app-container">Error connecting to the server. Please check the server logs.</div>;
  }

  return (
    <Split
      className="app-container"
      sizes={[15, 70, 15]}
      minSize={250}
      expandToMin={false}
      gutterSize={10}
      gutterAlign="center"
      snapOffset={30}
      dragInterval={1}
      direction="horizontal"
      cursor="col-resize"
    >
      <Split
        className="left-panel"
        direction="vertical"
        sizes={[60, 40]}
        minSize={100}
      >
        <Threads 
          currentThread={currentThread}
          setCurrentThread={setCurrentThread} 
          currentThreadDetails={currentThreadDetails}
          threadsVersion={threadsVersion}
        />
        <Settings disabled={serverStatus !== 'ready'} />
      </Split>
      <Chat 
        currentThread={currentThreadDetails}
        onThreadUpdate={fetchThreadDetails}
        disabled={serverStatus !== 'ready'}
      />
      <DocumentManagement 
        currentThread={currentThreadDetails}
        onThreadUpdate={fetchThreadDetails}
        onDocumentChange={forceThreadsRefetch}
      />
    </Split>
  );
}

export default App;