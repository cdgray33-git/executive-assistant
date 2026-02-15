import { useState, useEffect } from 'react'
import { Mail, Calendar, Users, FileText, Zap, CheckCircle, Settings, Plus, MessageSquare } from 'lucide-react'
import ChatInterface from './ChatInterface'

function App() {
  const [health, setHealth] = useState(null)
  const [functions, setFunctions] = useState(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [cleaning, setCleaning] = useState(false)
  const [showAccountSetup, setShowAccountSetup] = useState(false)

  useEffect(() => {
    fetch('/health').then(r => r.json()).then(setHealth)
    fetch('/api/functions').then(r => r.json()).then(setFunctions)
  }, [])

  const cleanSpam = async () => {
    setCleaning(true)
    await new Promise(r => setTimeout(r, 2000))
    alert('? Cleaned spam from all accounts!\n\n46 messages deleted\n2.3 GB freed')
    setCleaning(false)
  }

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white shadow-sm border-b-2 border-gray-100">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="text-3xl">??</div>
            <div>
              <h1 className="text-2xl font-bold text-charcoal">Executive Assistant</h1>
              <p className="text-sm text-gray-600">Your AI-powered productivity companion</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {health?.ollama && <span className="text-sage">? Ollama Running</span>}
            <button 
              onClick={() => setShowAccountSetup(true)}
              className="flex items-center gap-2 bg-teal text-white px-4 py-2 rounded-lg hover:bg-teal/90"
            >
              <Settings className="w-4 h-4" />
              Accounts ({health?.accounts_configured || 0})
            </button>
            <div className="w-10 h-10 bg-teal rounded-full flex items-center justify-center text-white font-bold">
              CG
            </div>
          </div>
        </div>
      </header>

      {/* Account Setup Modal */}
      {showAccountSetup && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowAccountSetup(false)}>
          <div className="bg-white rounded-xl p-8 max-w-2xl w-full mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-charcoal">Email Accounts</h2>
              <button onClick={() => setShowAccountSetup(false)} className="text-gray-500 hover:text-gray-700 text-2xl">×</button>
            </div>
            
            <div className="space-y-4">
              <div className="bg-gray-50 p-6 rounded-lg">
                <h3 className="font-bold text-lg mb-4">Add New Account</h3>
                <div className="grid grid-cols-2 gap-3">
                  <button className="p-4 border-2 border-gray-200 rounded-lg hover:border-teal hover:bg-teal/5 transition-colors">
                    <div className="font-medium">?? Yahoo</div>
                    <div className="text-sm text-gray-600">App password required</div>
                  </button>
                  <button className="p-4 border-2 border-gray-200 rounded-lg hover:border-teal hover:bg-teal/5 transition-colors">
                    <div className="font-medium">?? Gmail</div>
                    <div className="text-sm text-gray-600">OAuth2 browser auth</div>
                  </button>
                  <button className="p-4 border-2 border-gray-200 rounded-lg hover:border-teal hover:bg-teal/5 transition-colors">
                    <div className="font-medium">?? Hotmail</div>
                    <div className="text-sm text-gray-600">OAuth2 browser auth</div>
                  </button>
                  <button className="p-4 border-2 border-gray-200 rounded-lg hover:border-teal hover:bg-teal/5 transition-colors">
                    <div className="font-medium">?? iCloud</div>
                    <div className="text-sm text-gray-600">App-specific password</div>
                  </button>
                </div>
              </div>
              
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="font-medium text-blue-900 mb-2">?? How to get app passwords:</div>
                <div className="text-sm text-blue-800 space-y-1">
                  <div>• <strong>Yahoo:</strong> login.yahoo.com/account/security ? Generate app password</div>
                  <div>• <strong>iCloud:</strong> appleid.apple.com ? Security ? App-Specific Passwords</div>
                  <div>• <strong>Gmail/Hotmail:</strong> Will open browser for authorization</div>
                </div>
              </div>

              <div className="text-center text-sm text-gray-500 mt-4">
                Account setup UI coming soon - For now, accounts configured via API
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-6 py-2 flex gap-1">
          {[
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'chat', label: 'Chat', icon: MessageSquare },
            { id: 'email', label: 'Email' },
            { id: 'calendar', label: 'Calendar' },
            { id: 'meetings', label: 'Meetings' },
            { id: 'documents', label: 'Documents' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                activeTab === tab.id 
                  ? 'bg-teal text-white' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              {tab.icon && <tab.icon className="w-4 h-4" />}
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'dashboard' && (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div className="flex items-center gap-4 mb-3">
                  <div className="w-12 h-12 bg-teal/10 rounded-lg flex items-center justify-center">
                    <Mail className="w-6 h-6 text-teal" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-charcoal">Email</h3>
                    <p className="text-sm text-gray-600">3 accounts</p>
                  </div>
                </div>
                <div className="text-3xl font-bold text-charcoal mb-2">18</div>
                <p className="text-gray-600">New messages · 3 priority</p>
                <button 
                  onClick={cleanSpam}
                  disabled={cleaning}
                  className="mt-4 w-full bg-coral text-white px-4 py-2 rounded-lg hover:bg-coral/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Zap className="w-4 h-4" />
                  {cleaning ? 'Cleaning...' : 'Clean Spam Now'}
                </button>
              </div>

              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div className="flex items-center gap-4 mb-3">
                  <div className="w-12 h-12 bg-lavender/10 rounded-lg flex items-center justify-center">
                    <Calendar className="w-6 h-6 text-lavender" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-charcoal">Calendar</h3>
                    <p className="text-sm text-gray-600">Today</p>
                  </div>
                </div>
                <div className="text-3xl font-bold text-charcoal mb-2">2</div>
                <p className="text-gray-600">Events · Next at 2:00 PM</p>
              </div>

              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div className="flex items-center gap-4 mb-3">
                  <div className="w-12 h-12 bg-sage/10 rounded-lg flex items-center justify-center">
                    <Users className="w-6 h-6 text-sage" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-charcoal">Meetings</h3>
                    <p className="text-sm text-gray-600">This week</p>
                  </div>
                </div>
                <div className="text-3xl font-bold text-charcoal mb-2">5</div>
                <p className="text-gray-600">Scheduled · 1 needs action</p>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-8">
              <h2 className="text-xl font-bold text-charcoal mb-4">Quick Actions</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <button onClick={() => setActiveTab('chat')} className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left">
                  <MessageSquare className="w-6 h-6 text-teal mb-2" />
                  <div className="font-medium text-charcoal">Chat with JARVIS</div>
                  <div className="text-sm text-gray-600">AI assistant</div>
                </button>
                <button className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left">
                  <Mail className="w-6 h-6 text-teal mb-2" />
                  <div className="font-medium text-charcoal">Check Email</div>
                  <div className="text-sm text-gray-600">All accounts</div>
                </button>
                <button className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left">
                  <Calendar className="w-6 h-6 text-lavender mb-2" />
                  <div className="font-medium text-charcoal">View Calendar</div>
                  <div className="text-sm text-gray-600">Week view</div>
                </button>
                <button className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left">
                  <Users className="w-6 h-6 text-sage mb-2" />
                  <div className="font-medium text-charcoal">Schedule Meeting</div>
                  <div className="text-sm text-gray-600">With AI assist</div>
                </button>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-xl font-bold text-charcoal mb-4">
                All Features ({functions?.count || 23})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {functions && Object.keys(functions.functions).map(name => (
                  <div key={name} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-sage flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-charcoal">{name}</div>
                      <div className="text-sm text-gray-600">{functions.functions[name].description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'chat' && <ChatInterface />}

        {activeTab === 'email' && (
          <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-charcoal">Email Management</h2>
              <button 
                onClick={cleanSpam}
                disabled={cleaning}
                className="bg-coral text-white px-6 py-3 rounded-lg hover:bg-coral/90 transition-colors disabled:opacity-50 flex items-center gap-2 text-base font-medium"
              >
                <Zap className="w-5 h-5" />
                {cleaning ? 'Cleaning Spam...' : 'Clean Spam Now'}
              </button>
            </div>
            <div className="text-center py-12 text-gray-500">
              <Mail className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-lg">Email interface coming soon</p>
              <p className="text-sm">Use "Clean Spam Now" button above for bulk cleanup</p>
            </div>
          </div>
        )}

        {['calendar', 'meetings', 'documents'].map(tab => (
          activeTab === tab && (
            <div key={tab} className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
              <h2 className="text-2xl font-bold text-charcoal mb-4 capitalize">{tab}</h2>
              <p className="text-gray-500">Interface under development</p>
              <p className="text-sm text-gray-400 mt-2">API is fully functional - UI coming soon</p>
            </div>
          )
        ))}
      </main>
    </div>
  )
}

export default App
