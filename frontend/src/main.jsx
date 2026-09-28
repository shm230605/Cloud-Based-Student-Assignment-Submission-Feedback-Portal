import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './portal.css'
import App from './Portal.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
