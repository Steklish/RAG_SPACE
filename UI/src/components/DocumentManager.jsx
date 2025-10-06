import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Paper,
  CircularProgress,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const DocumentManager = ({ threadId }) => {
  const [documents, setDocuments] = useState([]);
  const [threadDocuments, setThreadDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDocuments();
    if (threadId) {
      fetchThreadDocuments();
    }
  }, [threadId]);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/documents`);
      setDocuments(response.data);
    } catch (err) {
      setError('Failed to fetch documents.');
    } finally {
      setLoading(false);
    }
  };

  const fetchThreadDocuments = async () => {
    try {
      const response = await axios.get(`${API_URL}/threads/${threadId}`);
      setThreadDocuments(response.data.document_ids || []);
    } catch (err) {
      setError('Failed to fetch thread documents.');
    }
  };

  const handleAddDocument = async (documentId) => {
    try {
      await axios.post(`${API_URL}/threads/${threadId}/documents`, { document_id: documentId });
      setThreadDocuments([...threadDocuments, documentId]);
    } catch (err) {
      setError('Failed to add document to thread.');
    }
  };

  const handleRemoveDocument = async (documentId) => {
    try {
      await axios.delete(`${API_URL}/threads/${threadId}/documents/${documentId}`);
      setThreadDocuments(threadDocuments.filter((id) => id !== documentId));
    } catch (err) {
      setError('Failed to remove document from thread.');
    }
  };

  const handleFileUpload = async (event) => {
    const files = event.target.files;
    if (files.length === 0) return;

    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }

    setLoading(true);
    try {
      await axios.post(`${API_URL}/documents`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      fetchDocuments();
    } catch (err) {
      setError('Failed to upload documents.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Document Manager
      </Typography>
      {error && <Typography color="error">{error}</Typography>}
      <Button variant="contained" component="label">
        Upload Documents
        <input type="file" hidden multiple onChange={handleFileUpload} />
      </Button>
      {loading && <CircularProgress sx={{ display: 'block', mt: 2 }} />}
      <Paper sx={{ mt: 2 }}>
        <List>
          {documents.map((doc) => (
            <ListItem
              key={doc.id}
              secondaryAction={
                threadId && (
                  threadDocuments.includes(doc.id) ? (
                    <IconButton edge="end" aria-label="delete" onClick={() => handleRemoveDocument(doc.id)}>
                      <DeleteIcon />
                    </IconButton>
                  ) : (
                    <IconButton edge="end" aria-label="add" onClick={() => handleAddDocument(doc.id)}>
                      <AddIcon />
                    </IconButton>
                  )
                )
              }
            >
              <ListItemText primary={doc.name} secondary={`Size: ${doc.size} bytes`} />
            </ListItem>
          ))}
        </List>
      </Paper>
    </Box>
  );
};

export default DocumentManager;
