import React, { useState } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import CurrencyBitcoinIcon from '@mui/icons-material/CurrencyBitcoin';
import Brightness4Icon from '@mui/icons-material/Brightness4';  // Dark mode icon
import Brightness7Icon from '@mui/icons-material/Brightness7';  // Light mode icon
import DashboardIcon from '@mui/icons-material/Dashboard';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import AssessmentIcon from '@mui/icons-material/Assessment';
import ArticleIcon from '@mui/icons-material/Article';
import MenuIcon from '@mui/icons-material/Menu';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';

const Navbar = ({ toggleTheme, currentTheme }) => {
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  // Menu state for mobile view
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleClose = () => {
    setAnchorEl(null);
  };
  
  // Navigation items with icons
  const navItems = [
    { label: 'Dashboard', path: '/', icon: <DashboardIcon fontSize="small" sx={{ mr: 0.5 }} /> },
    { label: 'Predictions', path: '/predictions', icon: <ShowChartIcon fontSize="small" sx={{ mr: 0.5 }} /> },
    { label: 'Accuracy', path: '/accuracy', icon: <AssessmentIcon fontSize="small" sx={{ mr: 0.5 }} /> },
    { label: 'News', path: '/news', icon: <ArticleIcon fontSize="small" sx={{ mr: 0.5 }} /> },
  ];

  return (
    <AppBar position="static">
      <Toolbar>
        <CurrencyBitcoinIcon sx={{ mr: 1 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Crypto Market Analyzer
        </Typography>
        
        {isMobile ? (
          <Box>
            <IconButton
              color="inherit"
              aria-label="menu"
              aria-controls="nav-menu"
              aria-haspopup="true"
              onClick={handleClick}
            >
              <MenuIcon />
            </IconButton>
            <Menu
              id="nav-menu"
              anchorEl={anchorEl}
              open={open}
              onClose={handleClose}
            >
              {navItems.map((item) => (
                <MenuItem 
                  key={item.path}
                  component={RouterLink} 
                  to={item.path}
                  onClick={handleClose}
                  selected={location.pathname === item.path}
                >
                  {item.icon}
                  {item.label}
                </MenuItem>
              ))}
            </Menu>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {navItems.map((item) => (
              <Button 
                key={item.path}
                color="inherit" 
                component={RouterLink} 
                to={item.path}
                sx={{ 
                  mx: 0.5,
                  fontWeight: location.pathname === item.path ? 'bold' : 'normal',
                  borderBottom: location.pathname === item.path ? '2px solid white' : 'none'
                }}
                startIcon={item.icon}
              >
                {item.label}
              </Button>
            ))}
          </Box>
        )}
        
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
      </Toolbar>
    </AppBar>
  );
};

export default Navbar; 