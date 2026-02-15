import { useState, useEffect } from 'react'
import { Mail, Calendar, Users, Settings, MessageSquare, ChevronDown, ChevronUp, Zap, CheckCircle, Plus, Trash2, TestTube } from 'lucide-react'
import ChatInterface from './ChatInterface'

function App() {
  const [health, setHealth] = useState(null)
  const [functions, setFunctions] = useState(null)
  const [activeTab, setActiveTab] = useState('chat')
  const [config, setConfig] = useState({ ea_name: 'JARVIS', user_name: 'User', banner_text: 'JARVIS, Your Executive Assistant', model: 'llama3.2:latest' })
  const [showSettings, setShowSettings] = useState(false)
  const [showAccounts, setShowAccounts] = useState(false)
  const [showCapabilities, setShowCapabilities] = useState(false)
  const [accounts, setAccounts] = useState([])
  const [selectedProvider, setSelectedProvider] = useState(null)
  const [accountForm, setAccountForm] = useState({ account_id: '', email: '', app_password: '', client_id: '', client_secret: '' })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = () => {
    fetch('/health').then(r => r.json()).then(setHealth).catch(() => {})
    fetch('/api/functions').then(r => r.json()).then(setFunctions).catch(() => {})
    fetch('/api/config').then(r => r.json()).then(data => {
      if (data.config) setConfig(data.config)
    }).catch(() => {})
    loadAccounts()
  }

  const loadAccounts = () => {
    fetch('/api/accounts', {
      headers: { 'X-API-Key': localStorage.getItem('api_key') || 'dev-key-12345' }
    })
      .then(r => r.json())
      .then(data => {
        if (data.accounts) setAccounts(data.accounts)
      })
      .catch(() => {})
  }

  const saveSettings = async (newConfig) => {
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      })
      const data = await response.json()
      if (data.status === 'success') {
        setConfig(data.config)
        setShowSettings(false)
        alert('✅ Settings saved! Reload page to apply model change.')
      }
    } catch (error) {
      alert(`❌ Error: ${error.message}`)
    }
  }

  const addAccount = async () => {
    if (!accountForm.account_id || !accountForm.email) {
      alert('❌ Please fill in Account ID and Email')
      return
    }

    setLoading(true)
    try {
      let endpoint, body

      if (['yahoo', 'comcast', 'apple'].includes(selectedProvider)) {
        if (!accountForm.app_password) {
          alert('❌ App password required')
          setLoading(false)
          return
        }
        endpoint = '/api/accounts/add/password'
        body = {
          account_id: accountForm.account_id,
          provider: selectedProvider,
          email: accountForm.email,
          app_password: accountForm.app_password
        }
      } else {
        if (!accountForm.client_id || !accountForm.client_secret) {
          alert('❌ OAuth credentials required')
          setLoading(false)
          return
        }
        endpoint = '/api/accounts/add/oauth'
        body = {
          account_id: accountForm.account_id,
          provider: selectedProvider,
          email: accountForm.email,
          client_id: accountForm.client_id,
          client_secret: accountForm.client_secret
        }
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': localStorage.getItem('api_key') || 'dev-key-12345'
        },
        body: JSON.stringify(body)
      })

      const data = await response.json()

      if (data.status === 'success') {
        alert('✅ Account added successfully!')
        setAccountForm({ account_id: '', email: '', app_password: '', client_id: '', client_secret: '' })
        setSelectedProvider(null)
        loadAccounts()
      } else {
        alert(`❌ Error: ${data.error || 'Failed to add account'}`)
      }
    } catch (error) {
      alert(`❌ Connection error: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const testAccount = async (accountId) => {
    try {
      const response = await fetch(`/api/accounts/test?account_id=${accountId}`, {
        headers: { 'X-API-Key': localStorage.getItem('api_key') || 'dev-key-12345' }
      })
      const data = await response.json()
      
      if (data.status === 'success') {
        alert(`✅ ${accountId}: Connection successful!`)
      } else {
        alert(`❌ ${accountId}: ${data.error || 'Connection failed'}`)
      }
    } catch (error) {
      alert(`❌ Test failed: ${error.message}`)
    }
  }

  const removeAccount = async (accountId) => {
    if (!confirm(`Remove account ${accountId}?`)) return

    try {
      const response = await fetch(`/api/accounts/${accountId}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': localStorage.getItem('api_key') || 'dev-key-12345' }
      })
      const data = await response.json()
      
      if (data.status === 'success') {
        alert('✅ Account removed')
        loadAccounts()
      } else {
        alert(`❌ Error: ${data.error}`)
      }
    } catch (error) {
      alert(`❌ Error: ${error.message}`)
    }
  }

  const providers = [
    { id: 'yahoo', name: 'Yahoo', type: 'password', icon: '📧', help: 'login.yahoo.com/account/security → Generate app password' },
    { id: 'gmail', name: 'Gmail', type: 'oauth', icon: '📬', help: 'console.cloud.google.com → Create OAuth2 credentials' },
    { id: 'hotmail', name: 'Hotmail/Outlook', type: 'oauth', icon: '📭', help: 'portal.azure.com → Register app for OAuth2' },
    { id: 'apple', name: 'iCloud', type: 'password', icon: '🍎', help: 'appleid.apple.com → Security → App-Specific Passwords' },
    { id: 'comcast', name: 'Comcast', type: 'password', icon: '📮', help: 'xfinity.com → Account settings → App password' }
  ]

  return (
    <div className="min-h-screen bg-cream">
      <header className="bg-white shadow-sm border-b-2 border-gray-100">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="text-3xl">🤖</div>
            <div>
              <h1 className="text-2xl font-bold text-charcoal">{config.banner_text}</h1>
              <p className="text-sm text-gray-600">AI-powered productivity companion</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {health?.ollama && <span className="text-sage flex items-center gap-1">✅ AI Ready</span>}
            <button 
              onClick={() => setShowAccounts(true)}
              className="flex items-center gap-2 bg-sage text-white px-4 py-2 rounded-lg hover:bg-sage/90"
            >
              <Mail className="w-4 h-4" />
              Accounts ({accounts.length})
            </button>
            <button 
              onClick={() => setShowSettings(true)}
              className="flex items-center gap-2 bg-teal text-white px-4 py-2 rounded-lg hover:bg-teal/90"
            >
              <Settings className="w-4 h-4" />
              Settings
            </button>
          </div>
        </div>
      </header>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowSettings(false)}>
          <div className="bg-white rounded-xl p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h2 className="text-2xl font-bold text-charcoal mb-6">Settings</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Assistant Name</label>
                <input
                  type="text"
                  value={config.ea_name}
                  onChange={(e) => setConfig({...config, ea_name: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                  placeholder="JARVIS"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Your Name</label>
                <input
                  type="text"
                  value={config.user_name}
                  onChange={(e) => setConfig({...config, user_name: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                  placeholder="User"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Banner Text</label>
                <input
                  type="text"
                  value={config.banner_text}
                  onChange={(e) => setConfig({...config, banner_text: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                  placeholder="JARVIS, Your Executive Assistant"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">AI Model</label>
                <select
                  value={config.model || 'llama3.2:latest'}
                  onChange={(e) => setConfig({...config, model: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                >
                  <option value="llama3.2:latest">Llama 3.2 (Default - Fast)</option>
                  <option value="llama3.2:latest-mlx">Llama 3.2 MLX (M1-M4 Optimized) ⚡</option>
                  <option value="qwen2.5:7b-instruct">Qwen 2.5 (Smart)</option>
                  <option value="mistral:latest">Mistral (Balanced)</option>
                  <option value="codellama:latest">Code Llama (Programming)</option>
                  <option value="medllama2:latest">Med Llama (Medical)</option>
                  <option value="llama3.2:70b">Llama 3.2 70B (Most Powerful)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  💡 Use MLX models for 3-5x faster performance on M1-M4 Macs
                </p>
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => saveSettings(config)}
                className="flex-1 bg-teal text-white px-6 py-3 rounded-lg hover:bg-teal/90"
              >
                Save Settings
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Accounts Modal */}
      {showAccounts && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowAccounts(false)}>
          <div className="bg-white rounded-xl p-8 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-charcoal">Email Accounts</h2>
              <button onClick={() => setShowAccounts(false)} className="text-gray-500 hover:text-gray-700 text-2xl">×</button>
            </div>

            {/* Configured Accounts */}
            {accounts.length > 0 && (
              <div className="mb-6">
                <h3 className="font-bold text-lg mb-3">Configured Accounts</h3>
                <div className="space-y-2">
                  {accounts.map(acc => (
                    <div key={acc.account_id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium">{acc.email}</div>
                        <div className="text-sm text-gray-600">{acc.provider} • {acc.account_id}</div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => testAccount(acc.account_id)}
                          className="p-2 text-teal hover:bg-teal/10 rounded"
                          title="Test connection"
                        >
                          <TestTube className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => removeAccount(acc.account_id)}
                          className="p-2 text-red-500 hover:bg-red-50 rounded"
                          title="Remove account"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Add New Account */}
            <div className="bg-gray-50 p-6 rounded-lg">
              <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                <Plus className="w-5 h-5" />
                Add New Account
              </h3>

              {!selectedProvider ? (
                <>
                  <p className="text-sm text-gray-600 mb-4">Select your email provider:</p>
                  <div className="grid grid-cols-2 gap-3">
                    {providers.map(provider => (
                      <button
                        key={provider.id}
                        onClick={() => setSelectedProvider(provider.id)}
                        className="p-4 border-2 border-gray-200 rounded-lg hover:border-teal hover:bg-white transition-colors text-left"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-2xl">{provider.icon}</span>
                          <span className="font-medium">{provider.name}</span>
                        </div>
                        <div className="text-xs text-gray-500">{provider.type === 'oauth' ? 'OAuth2 browser auth' : 'App password'}</div>
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <div className="mb-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
                    <strong>📘 {providers.find(p => p.id === selectedProvider)?.name}:</strong>
                    <div className="mt-1">{providers.find(p => p.id === selectedProvider)?.help}</div>
                  </div>

                  <div className="space-y-3">
                    <input
                      type="text"
                      placeholder="Account ID (e.g., my_yahoo)"
                      value={accountForm.account_id}
                      onChange={(e) => setAccountForm({...accountForm, account_id: e.target.value})}
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                    />
                    
                    <input
                      type="email"
                      placeholder="Email address"
                      value={accountForm.email}
                      onChange={(e) => setAccountForm({...accountForm, email: e.target.value})}
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                    />

                    {['yahoo', 'comcast', 'apple'].includes(selectedProvider) ? (
                      <input
                        type="password"
                        placeholder="App password"
                        value={accountForm.app_password}
                        onChange={(e) => setAccountForm({...accountForm, app_password: e.target.value})}
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                      />
                    ) : (
                      <>
                        <input
                          type="text"
                          placeholder="OAuth Client ID"
                          value={accountForm.client_id}
                          onChange={(e) => setAccountForm({...accountForm, client_id: e.target.value})}
                          className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                        />
                        <input
                          type="password"
                          placeholder="OAuth Client Secret"
                          value={accountForm.client_secret}
                          onChange={(e) => setAccountForm({...accountForm, client_secret: e.target.value})}
                          className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
                        />
                      </>
                    )}
                  </div>

                  <div className="flex gap-3 mt-4">
                    <button
                      onClick={addAccount}
                      disabled={loading}
                      className="flex-1 bg-teal text-white px-6 py-3 rounded-lg hover:bg-teal/90 disabled:opacity-50"
                    >
                      {loading ? 'Adding...' : 'Add Account'}
                    </button>
                    <button
                      onClick={() => {
                        setSelectedProvider(null)
                        setAccountForm({ account_id: '', email: '', app_password: '', client_id: '', client_secret: '' })
                      }}
                      className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-6 py-2 flex gap-1">
          {[
            { id: 'chat', label: 'Chat', icon: MessageSquare },
            { id: 'email', label: 'Email', icon: Mail },
            { id: 'calendar', label: 'Calendar', icon: Calendar },
            { id: 'meetings', label: 'Meetings', icon: Users }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                activeTab === tab.id ? 'bg-teal text-white' : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'chat' && (
          <div>
            <ChatInterface />
            
            <div className="mt-6">
              <button
                onClick={() => setShowCapabilities(!showCapabilities)}
                className="w-full bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex justify-between items-center hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-sage" />
                  <span className="font-semibold text-charcoal">
                    Available Capabilities ({functions?.count || 0})
                  </span>
                </div>
                {showCapabilities ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
              </button>
              
              {showCapabilities && functions && (
                <div className="mt-3 bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {Object.keys(functions.functions).map(name => (
                      <div key={name} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                        <Zap className="w-4 h-4 text-teal flex-shrink-0 mt-1" />
                        <div>
                          <div className="font-medium text-charcoal text-sm">{name}</div>
                          <div className="text-xs text-gray-600">{functions.functions[name].description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'email' && (
          <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
            <Mail className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h2 className="text-2xl font-bold text-charcoal mb-2">Email Management</h2>
            <p className="text-gray-500 mb-4">Use the Chat tab to manage your email with natural language</p>
            <div className="text-sm text-gray-400">
              <strong>Try:</strong> "Clean spam from all accounts" • "Setup email folders" • "Check my email"
            </div>
          </div>
        )}

        {['calendar', 'meetings'].map(tab => (
          activeTab === tab && (
            <div key={tab} className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
              <h2 className="text-2xl font-bold text-charcoal mb-4 capitalize">{tab}</h2>
              <p className="text-gray-500">Use the Chat tab to interact with {tab}</p>
            </div>
          )
        ))}
      </main>
    </div>
  )
}

export default App
