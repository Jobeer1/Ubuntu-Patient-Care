import React from 'react';
import { AccessibilityProvider } from './components/AccessibilityContext';
import SARadiologyDashboard from './SARadiologyDashboard';

export default function App() {
  return (
    <AccessibilityProvider>
      <SARadiologyDashboard />
    </AccessibilityProvider>
  );
}
