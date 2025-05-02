import React, { useState, useMemo, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';

// Components
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';

function App() {
  // State to track the theme mode
  const [mode, setMode] = useState(() => {
    // Check if a theme preference exists in localStorage
    const savedMode = localStorage.getItem('themeMode');
    return savedMode || 'dark'; // Default to dark mode if no preference exists
  });

  // Save theme preference to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('themeMode', mode);
  }, [mode]);

  // Toggle theme function that will be passed to the Navbar
  const toggleTheme = () => {
    setMode((prevMode) => (prevMode === 'dark' ? 'light' : 'dark'));
  };

  // Create a theme based on the current mode
  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          ...(mode === 'dark'
            ? {
                // Dark theme
                primary: {
                  main: '#90caf9',
                },
                secondary: {
                  main: '#f48fb1',
                },
                background: {
                  default: '#121212',
                  paper: '#1e1e1e',
                },
              }
            : {
                // Light theme
                primary: {
                  main: '#1976d2',
                },
                secondary: {
                  main: '#e91e63',
                },
                background: {
                  default: '#f5f5f5',
                  paper: '#ffffff',
                },
              }),
        },
      }),
    [mode]
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Navbar toggleTheme={toggleTheme} currentTheme={mode} />
        <Box sx={{ flexGrow: 1, p: 3 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            {/* Redirect old routes to the main dashboard */}
            <Route path="/predictions" element={<Navigate to="/" replace />} />
            <Route path="/accuracy" element={<Navigate to="/" replace />} />
            <Route path="/news" element={<Navigate to="/" replace />} />
          </Routes>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App; 