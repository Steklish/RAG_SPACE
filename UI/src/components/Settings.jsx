import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const Settings = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6">Preferences</Typography>
        <Typography>
          Here you can configure the application settings.
        </Typography>
      </Paper>
    </Box>
  );
};

export default Settings;
