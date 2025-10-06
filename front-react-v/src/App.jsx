import React, { useState, useEffect, useCallback } from 'react';
import Split from 'react-split';
import axios from 'axios';
import Threads from './components/Threads';
import Chat from './components/Chat';
import DocumentManagement from './components/DocumentManagement';
import Settings from './components/Settings';
import './App.css';

function App() {
  const [currentThread, setCurrentThread] = useState(null);
  const [currentThreadDetails, setCurrentThreadDetails] = useState(null);

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

  return (
    <Split
      className="app-container"
      sizes={[20, 60, 20]}
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
        sizes={[75, 25]}
        minSize={100}
      >
        <Threads 
          currentThread={currentThread}
          setCurrentThread={setCurrentThread} 
        />
        <Settings />
      </Split>
      <Chat 
        currentThread={currentThreadDetails}
      />
      <DocumentManagement 
        currentThread={currentThreadDetails}
        onThreadUpdate={fetchThreadDetails} // Pass the callback here
      />
    </Split>
  );
}

export default App;