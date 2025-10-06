import React, { useState, useEffect } from 'react';
import { Box, Tabs, Tab, Paper, List, ListItem, ListItemText, Button, Typography } from '@mui/material';
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from "react-resizable-panels";
import Chat from './components/Chat';
import Settings from './components/Settings';
import axios from 'axios';
import './App.css';

const API_URL = 'http://localhost:8000/api';

function App() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [threads, setThreads] = useState([]);
  const [activeThread, setActiveThread] = useState(null);

  useEffect(() => {
    fetchThreads();
  }, []);

  const fetchThreads = async () => {
    try {
      const response = await axios.get(`${API_URL}/threads`);
      setThreads(response.data);
    } catch (error) {
      console.error('Failed to fetch threads:', error);
    }
  };

  const handleCreateThread = async () => {
    try {
      const response = await axios.post(`${API_URL}/threads`);
      setThreads([response.data, ...threads]);
      setActiveThread(response.data.id);
    } catch (error) {
      console.error('Failed to create thread:', error);
    }
  };

  const handleChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Paper square>
        <Tabs value={selectedTab} onChange={handleChange} centered>
          <Tab label="Chat" />
          <Tab label="Settings" />
        </Tabs>
      </Paper>
      <PanelGroup direction="horizontal" style={{ flexGrow: 1 }}>
        <Panel defaultSize={20} minSize={15}>
          <Box sx={{ height: '100%', overflow: 'auto', p: 2 }}>
            <Button variant="contained" fullWidth onClick={handleCreateThread}>
              New Thread
            </Button>
            <List>
              {threads.map((thread) => (
                <ListItem button key={thread.id} onClick={() => setActiveThread(thread.id)} selected={activeThread === thread.id}>
                  <ListItemText primary={thread.name} />
                </ListItem>
              ))}
            </List>
          </Box>
        </Panel>
        <PanelResizeHandle style={{ width: '8px', background: '#f1f1f1' }} />
        <Panel minSize={30}>
          <Box sx={{ height: '100%', overflow: 'auto' }}>
            {selectedTab === 0 && (activeThread ? <Chat threadId={activeThread} /> : <Typography sx={{ p: 2 }}>Select or create a thread to start chatting.</Typography>)}
            {selectedTab === 1 && <Settings />}
          </Box>
        </Panel>
      </PanelGroup>
    </Box>
  );
}

export default App;
