import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import CurrencyBitcoinIcon from '@mui/icons-material/CurrencyBitcoin';
import Brightness4Icon from '@mui/icons-material/Brightness4';  // Dark mode icon
import Brightness7Icon from '@mui/icons-material/Brightness7';  // Light mode icon

const Navbar = ({ toggleTheme, currentTheme }) => {
  return (
    <AppBar position="static">
      <Toolbar>
        <CurrencyBitcoinIcon sx={{ mr: 1 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Crypto Market Analyzer
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Button color="inherit" component={RouterLink} to="/">
            Dashboard
          </Button>
          
          {/* Theme toggle button */}
          <Tooltip title={`Switch to ${currentTheme === 'dark' ? 'light' : 'dark'} mode`}>
            <IconButton 
              color="inherit" 
              onClick={toggleTheme} 
              sx={{ ml: 1 }}
              aria-label="toggle dark/light mode"
            >
              {currentTheme === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar; 