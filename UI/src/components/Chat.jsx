import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  Typography,
  Paper,
  CircularProgress,
  AppBar,
  Toolbar,
  CssBaseline,
  Divider,
  Grid,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import DocumentManager from './DocumentManager';

const Chat = ({ threadId }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [models, setModels] = useState(null);
  const [chatModelInfo, setChatModelInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const fetchModelInfo = async () => {
      try {
        const [modelsRes, chatInfoRes] = await Promise.all([
          fetch('/api/get_loaded_models'),
          fetch('/api/chat_model_info'),
        ]);
        const modelsData = await modelsRes.json();
        const chatInfoData = await chatInfoRes.json();
        setModels(modelsData);
        setChatModelInfo(chatInfoData);
      } catch (error) {
        console.error("Error fetching model info:", error);
        setMessages(prev => [...prev, {
          id: 'error-fetch',
          text: 'Error: Could not fetch model information from the backend.',
          sender: 'system'
        }]);
      }
    };
    fetchModelInfo();
  }, []);

  const handleSendMessage = async () => {
    if (inputValue.trim()) {
      const userMessage = {
        id: Date.now(),
        text: inputValue,
        sender: 'user',
      };
      setMessages(prev => [...prev, userMessage]);
      setInputValue('');
      setIsLoading(true);

      try {
        const response = await fetch(`/api/threads/${threadId}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ content: inputValue }),
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let botMessage = { id: Date.now() + 1, text: '', sender: 'bot' };
        setMessages(prev => [...prev, botMessage]);

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            const data = JSON.parse(chunk.replace('data: ', ''));
            botMessage.text += data.data;
            setMessages(prev => [...prev.slice(0, -1), botMessage]);
        }

      } catch (error) {
        console.error('Error sending message:', error);
        const errorMessage = {
          id: Date.now() + 1,
          text: "Error: Could not send message.",
          sender: 'system',
        };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            RAGgie BOY Chat
          </Typography>
        </Toolbar>
      </AppBar>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
          height: '100%',
        }}
      >
        <Toolbar />
        <Grid container spacing={2} sx={{ height: '100%' }}>
          <Grid item xs={8} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Paper elevation={3} sx={{ flexGrow: 1, overflowY: 'auto', p: 2, mb: 2 }}>
              <List>
                {messages.map((msg) => (
                  <ListItem key={msg.id} sx={{
                    justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                  }}>
                    <Paper
                      elevation={1}
                      sx={{
                        p: 1.5,
                        bgcolor: msg.sender === 'user' ? 'primary.main' : 'grey.300',
                        color: msg.sender === 'user' ? 'primary.contrastText' : 'text.primary',
                        borderRadius: msg.sender === 'user' ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
                        maxWidth: '70%',
                      }}
                    >
                      <ListItemText primary={msg.text} />
                    </Paper>
                  </ListItem>
                ))}
                {isLoading && (
                  <ListItem sx={{justifyContent: 'flex-start'}}>
                    <CircularProgress size={24} />
                  </ListItem>
                )}
                <div ref={messagesEndRef} />
              </List>
            </Paper>
            <Box sx={{ display: 'flex' }}>
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Type a message..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSendMessage()}
                disabled={isLoading}
              />
              <Button
                variant="contained"
                color="primary"
                onClick={handleSendMessage}
                disabled={isLoading}
                sx={{ ml: 1, px: 3 }}
              >
                <SendIcon />
              </Button>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <DocumentManager threadId={threadId} />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default Chat;