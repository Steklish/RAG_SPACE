import React, { useState } from 'react';
import { Box, Tabs, Tab, Paper } from '@mui/material';
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from "react-resizable-panels";
import Chat from './components/Chat';
import Settings from './components/Settings';
import './App.css';

function App() {
  const [selectedTab, setSelectedTab] = useState(0);

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
        <Panel defaultSize={50} minSize={20}>
          <Box sx={{ height: '100%', overflow: 'auto' }}>
            {selectedTab === 0 && <Chat />}
            {selectedTab === 1 && <Settings />}
          </Box>
        </Panel>
        <PanelResizeHandle style={{ width: '8px', background: '#f1f1f1' }} />
        <Panel minSize={20}>
          <Box sx={{ height: '100%', overflow: 'auto', p: 2 }}>
            <Typography variant="h6">
              {selectedTab === 0 ? "Chat Context" : "Settings Details"}
            </Typography>
            <Typography>
              {selectedTab === 0
                ? "This panel can be used to display additional chat context, like retrieved documents."
                : "This panel can display detailed settings or preferences."}
            </Typography>
          </Box>
        </Panel>
      </PanelGroup>
    </Box>
  );
}

export default App;
