import { useState } from 'react'
import './App.css'

function App() {
  const [repo_url, setrepourl] = useState('')
  const [result, setresult] =  useState(null)
  const [loading, setloading] = useState(false)
  const [error, seterror] = useState('')

  async function analyzeRepo(){
    const response = await fetch("http://localhost:8000/analyze", {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({repo_url})
    })
    const data = await response.json()
    setresult(data)
  }

  return (
    <main>
      <h1>CodeAtlas</h1>
  
      <p>Enter a GitHub repository URL</p>
  
      <input
        type="text"
        value={repo_url}
        onChange={(event) => setrepourl(event.target.value)}
        placeholder="https://github.com/user/repo"
      />
  
      <button
        onClick={analyzeRepo}>
          Analyze
      </button>
      {result && (
        <>
          <h2>Analysis Results</h2>
          <pre>
            {JSON.stringify(result, null, 2)}
          </pre>
        </>
      )}
    </main>
  )}

export default App
