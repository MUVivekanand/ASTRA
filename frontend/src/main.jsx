import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { StytchProvider } from '@stytch/react';
import { createStytchUIClient } from '@stytch/react/ui';

const stytch = createStytchUIClient("public-token-test-e30dfce9-b079-49f7-a260-cf734549caf5");

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <StytchProvider stytch={stytch}>
        <App/>
    </StytchProvider>
  </StrictMode>,
)
