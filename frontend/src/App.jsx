import './App.css'
import { StytchLogin, IdentityProvider, useStytchUser } from '@stytch/react'

function App() {
  const {user} = useStytchUser();
  console.log(user);

  const config = {
    products: [
      "passwords"
    ],
    otpOptions: {
      methods: [],
      expirationMinutes: 1
    },
    passwordOptions: {
      loginRedirectURL: "https://www.stytch.com/login",
      resetPasswordRedirectURL: "https://www.stytch.com/reset-password"
    }
  }
  return (
    <div>
        {!user ? <StytchLogin config={config}/> : <IdentityProvider/>}
        
    </div>
  )
}

export default App
