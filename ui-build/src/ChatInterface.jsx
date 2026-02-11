import { useState, useEffect, useRef } from 'react'
import { Send, Trash2, Loader } from 'lucide-react'

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Good day. I\'m JARVIS, your executive assistant. How may I assist you today?' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': localStorage.getItem('api_key') || 'dev-key-12345'
        },
        body: JSON.stringify({ message: userMessage })
      })

      const data = await response.json()

      if (data.status === 'success') {
        // Add assistant response
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          tool_calls: data.tool_calls,
          tool_results: data.tool_results
        }])
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${data.error || 'Unknown error'}`
        }])
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Connection error: ${error.message}`
      }])
    } finally {
      setLoading(false)
    }
  }

  const resetConversation = async () => {
    try {
      await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': localStorage.getItem('api_key') || 'dev-key-12345'
        },
        body: JSON.stringify({ message: '', reset: true })
      })
      
      setMessages([
        { role: 'assistant', content: 'Conversation reset. How can I help you?' }
      ])
    } catch (error) {
      console.error('Reset error:', error)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-white rounded-xl shadow-sm border border-gray-100">
      {/* Chat Header */}
      <div className="flex justify-between items-center p-4 border-b">
        <div>
          <h2 className="text-xl font-bold text-charcoal">JARVIS Assistant</h2>
          <p className="text-sm text-gray-600">AI-powered executive assistant</p>
        </div>
        <button
          onClick={resetConversation}
          className="flex items-center gap-2 text-gray-600 hover:text-coral px-3 py-2 rounded-lg hover:bg-gray-50"
          title="Reset conversation"
        >
          <Trash2 className="w-4 h-4" />
          Reset
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl ${msg.role === 'user' ? 'bg-teal text-white' : 'bg-gray-100 text-charcoal'} rounded-2xl px-6 py-4`}>
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-2 text-teal font-semibold text-sm">
                  <span className="w-2 h-2 bg-teal rounded-full animate-pulse"></span>
                  JARVIS
                </div>
              )}
              
              <div className="whitespace-pre-wrap">{msg.content}</div>
              
              {/* Show function calls if any */}
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-sm">
                  <div className="font-medium mb-2">?? Actions taken:</div>
                  {msg.tool_calls.map((call, i) => (
                    <div key={i} className="ml-4 text-gray-600">
                      • {call.function.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl px-6 py-4">
              <div className="flex items-center gap-2 text-teal">
                <Loader className="w-4 h-4 animate-spin" />
                <span className="text-sm">JARVIS is thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask JARVIS anything... (e.g., 'Check my email' or 'Schedule a meeting with John tomorrow at 2pm')"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal resize-none"
            rows="2"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-teal text-white rounded-lg hover:bg-teal/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send className="w-5 h-5" />
            Send
          </button>
        </div>
        
        <div className="mt-3 text-xs text-gray-500">
          <strong>Try:</strong> "Check my calendar for today" • "Draft an email to support@example.com" • "What meetings do I have this week?"
        </div>
      </div>
    </div>
  )
}
