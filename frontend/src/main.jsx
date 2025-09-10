import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { StytchProvider } from '@stytch/react';
import { createStytchUIClient } from '@stytch/react/ui';


const stytch = createStytchUIClient('');

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <StytchProvider stytch={stytch}>
        <App/>
    </StytchProvider>
  </StrictMode>,
)
