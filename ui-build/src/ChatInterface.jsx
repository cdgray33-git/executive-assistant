import { useState, useEffect, useRef } from 'react'
import { Send, Trash2, Loader, Paperclip, X } from 'lucide-react'

export default function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [config, setConfig] = useState({ ea_name: 'JARVIS', user_name: 'User' })
  const [attachment, setAttachment] = useState(null)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    fetch('/api/config')
      .then(r => r.json())
      .then(data => {
        if (data.config) setConfig(data.config)
      })
      .catch(() => {})

    setMessages([{
      role: 'assistant',
      content: `Good day. I'm ${config.ea_name || 'JARVIS'}, your executive assistant. How may I assist you today?`
    }])
  }, [])

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        alert('File too large. Maximum size is 10MB.')
        return
      }
      
      const reader = new FileReader()
      reader.onload = (event) => {
        setAttachment({
          name: file.name,
          type: file.type,
          size: file.size,
          data: event.target.result.split(',')[1]
        })
      }
      reader.readAsDataURL(file)
    }
  }

  const removeAttachment = () => {
    setAttachment(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const sendMessage = async () => {
    if ((!input.trim() && !attachment) || loading) return

    const userMessage = input.trim() || `[Attached: ${attachment.name}]`
    setInput('')
    
    setMessages(prev => [...prev, { 
      role: 'user', 
      content: userMessage,
      attachment: attachment ? { name: attachment.name, size: attachment.size } : null
    }])
    setLoading(true)

    try {
      const payload = { command: userMessage }
      if (attachment) payload.attachment = attachment

      const response = await fetch('/api/assistant/command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': localStorage.getItem('api_key') || 'dev-key-12345'
        },
        body: JSON.stringify(payload)
      })

      const data = await response.json()

      if (data.status === 'success') {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response || data.result,
          actions: data.actions_taken,
          function_calls: data.tool_calls
        }])
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `⚠️ ${data.error || 'Unable to process request'}`
        }])
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Connection error: ${error.message}`
      }])
    } finally {
      setLoading(false)
      removeAttachment()
    }
  }

  const resetConversation = () => {
    setMessages([{
      role: 'assistant',
      content: `Conversation reset. How can I help you, ${config.user_name}?`
    }])
    removeAttachment()
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-white rounded-xl shadow-sm border border-gray-100">
      <div className="flex justify-between items-center p-4 border-b">
        <div>
          <h2 className="text-xl font-bold text-charcoal">{config.ea_name}</h2>
          <p className="text-sm text-gray-600">Your AI Executive Assistant</p>
        </div>
        <button
          onClick={resetConversation}
          className="flex items-center gap-2 text-gray-600 hover:text-coral px-3 py-2 rounded-lg hover:bg-gray-50"
        >
          <Trash2 className="w-4 h-4" />
          Reset
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl ${msg.role === 'user' ? 'bg-teal text-white' : 'bg-gray-100 text-charcoal'} rounded-2xl px-6 py-4`}>
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-2 text-teal font-semibold text-sm">
                  <span className="w-2 h-2 bg-teal rounded-full animate-pulse"></span>
                  {config.ea_name}
                </div>
              )}
              
              <div className="whitespace-pre-wrap">{msg.content}</div>
              
              {msg.attachment && (
                <div className="mt-2 pt-2 border-t border-white/20 text-sm flex items-center gap-2">
                  <Paperclip className="w-4 h-4" />
                  <span>{msg.attachment.name}</span>
                  <span className="text-xs opacity-75">({(msg.attachment.size / 1024).toFixed(1)}KB)</span>
                </div>
              )}
              
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-sm">
                  <div className="font-medium mb-2">✅ Actions completed:</div>
                  {msg.actions.map((action, i) => (
                    <div key={i} className="ml-4 text-gray-600">• {action}</div>
                  ))}
                </div>
              )}

              {msg.function_calls && msg.function_calls.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-sm">
                  <div className="font-medium mb-2">🔧 Functions executed:</div>
                  {msg.function_calls.map((call, i) => (
                    <div key={i} className="ml-4 text-gray-600">
                      • {call.function?.name || call.name}
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
                <span className="text-sm">{config.ea_name} is processing...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t bg-gray-50">
        {attachment && (
          <div className="mb-3 flex items-center gap-3 bg-white p-3 rounded-lg border border-gray-200">
            <Paperclip className="w-5 h-5 text-teal" />
            <div className="flex-1">
              <div className="font-medium text-sm">{attachment.name}</div>
              <div className="text-xs text-gray-500">
                {(attachment.size / 1024).toFixed(1)}KB • {attachment.type}
              </div>
            </div>
            <button onClick={removeAttachment} className="text-gray-400 hover:text-red-500">
              <X className="w-5 h-5" />
            </button>
          </div>
        )}
        
        <div className="flex gap-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            className="hidden"
            accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.jpg,.jpeg,.png,.gif"
          />
          
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-100"
            disabled={loading}
          >
            <Paperclip className="w-5 h-5 text-gray-600" />
          </button>
          
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={`Ask ${config.ea_name} anything... Try: "Clean my spam" or attach a document`}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal resize-none"
            rows="2"
            disabled={loading}
          />
          
          <button
            onClick={sendMessage}
            disabled={loading || (!input.trim() && !attachment)}
            className="px-6 py-3 bg-teal text-white rounded-lg hover:bg-teal/90 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            <Send className="w-5 h-5" />
            Send
          </button>
        </div>
        
        <div className="mt-3 text-xs text-gray-500">
          <strong>Try:</strong> "Clean spam" • "Setup email folders" • "Check calendar" • Attach files for editing
        </div>
      </div>
    </div>
  )
}
