import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Initialize Cornerstone and related libraries
import { initializeCornerstone } from './core/cornerstone-init';

// Initialize the DICOM viewer core
initializeCornerstone();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);