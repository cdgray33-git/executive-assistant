import { useState, useEffect, useRef } from 'react'
import { Send, Paperclip, X, Mail, Check, Edit2, Trash2 } from 'lucide-react'

export default function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [attachment, setAttachment] = useState(null)
  const [loading, setLoading] = useState(false)
  const [config, setConfig] = useState({ ea_name: 'JARVIS', user_name: 'User' })
  const [pendingDrafts, setPendingDrafts] = useState([])
  const [editingDraft, setEditingDraft] = useState(null)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    fetch('/api/config').then(r => r.json()).then(data => {
      if (data.config) setConfig(data.config)
    }).catch(() => {})
    
    setMessages([{
      role: 'assistant',
      content: `Hello ${config.user_name}, I'm ${config.ea_name}. How can I help you today?`
    }])
    
    loadPendingDrafts()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadPendingDrafts = async () => {
    try {
      const res = await fetch('/api/drafts/pending')
      const data = await res.json()
      setPendingDrafts(data.drafts || [])
    } catch (e) {
      console.error('Failed to load drafts:', e)
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = () => {
        setAttachment({
          name: file.name,
          type: file.type,
          content: reader.result
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
    if (!input.trim() && !attachment) return

    const userMessage = input.trim() || `[Attached: ${attachment.name}]`

    setMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      attachment: attachment
    }])

    setInput('')
    setLoading(true)

    try {
      const payload = { command: userMessage }
      if (attachment) {
        payload.attachment = attachment
      }

      const response = await fetch('/api/assistant/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const data = await response.json()

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response || 'Done!',
        drafts: data.drafts_created || []
      }])

      if (data.drafts_created && data.drafts_created.length > 0) {
        loadPendingDrafts()
      }

      removeAttachment()
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${e.message}`
      }])
    } finally {
      setLoading(false)
    }
  }

  const approveDraft = async (draftId) => {
    try {
      const res = await fetch('/api/drafts/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft_id: draftId })
      })
      
      const data = await res.json()
      
      if (data.status === 'success') {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '✅ Email sent successfully!'
        }])
        loadPendingDrafts()
      }
    } catch (e) {
      alert(`Failed to send email: ${e.message}`)
    }
  }

  const rejectDraft = async (draftId) => {
    try {
      await fetch('/api/drafts/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft_id: draftId })
      })
      loadPendingDrafts()
    } catch (e) {
      alert(`Failed to delete draft: ${e.message}`)
    }
  }

  const startEditDraft = (draft) => {
    setEditingDraft({ ...draft })
  }

  const saveDraftEdit = async () => {
    try {
      await fetch('/api/drafts/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          draft_id: editingDraft.draft_id,
          updates: {
            subject: editingDraft.subject,
            body: editingDraft.body
          }
        })
      })
      setEditingDraft(null)
      loadPendingDrafts()
    } catch (e) {
      alert(`Failed to edit draft: ${e.message}`)
    }
  }

  const resetConversation = async () => {
    setMessages([{
      role: 'assistant',
      content: `Conversation reset. How can I help you, ${config.user_name}?`
    }])
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      {pendingDrafts.length > 0 && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-xl">
          <h3 className="font-semibold text-amber-900 mb-3 flex items-center gap-2">
            <Mail className="w-5 h-5" />
            {pendingDrafts.length} Email{pendingDrafts.length > 1 ? 's' : ''} Awaiting Approval
          </h3>
          <div className="space-y-3">
            {pendingDrafts.map(draft => (
              <div key={draft.draft_id} className="bg-white p-4 rounded-lg border border-amber-100">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1">
                    <div className="text-sm text-gray-500">To: {draft.to}</div>
                    <div className="font-medium text-gray-900">{draft.subject}</div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => startEditDraft(draft)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                      title="Edit"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => approveDraft(draft.draft_id)}
                      className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                      title="Send"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => rejectDraft(draft.draft_id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="text-sm text-gray-600 mt-2 p-3 bg-gray-50 rounded max-h-32 overflow-y-auto whitespace-pre-wrap">
                  {draft.body}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {editingDraft && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <h3 className="text-xl font-bold mb-4">Edit Email</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">To:</label>
                <input
                  type="text"
                  value={editingDraft.to}
                  disabled
                  className="w-full p-2 border rounded bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Subject:</label>
                <input
                  type="text"
                  value={editingDraft.subject}
                  onChange={(e) => setEditingDraft({...editingDraft, subject: e.target.value})}
                  className="w-full p-2 border rounded"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Body:</label>
                <textarea
                  value={editingDraft.body}
                  onChange={(e) => setEditingDraft({...editingDraft, body: e.target.value})}
                  className="w-full p-2 border rounded h-64"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setEditingDraft(null)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={saveDraftEdit}
                  className="px-4 py-2 bg-teal text-white rounded-lg hover:bg-teal-600"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl ${msg.role === 'user' ? 'bg-teal text-white' : 'bg-gray-100 text-charcoal'} rounded-2xl px-6 py-4`}>
              <div className="whitespace-pre-wrap">{msg.content}</div>
              {msg.attachment && (
                <div className="mt-2 text-sm opacity-75">
                  📎 {msg.attachment.name}
                </div>
              )}
              {msg.drafts && msg.drafts.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-300">
                  <div className="text-sm font-semibold mb-2">📧 Email drafts created:</div>
                  {msg.drafts.map((draft, i) => (
                    <div key={i} className="text-sm">• {draft.name} ({draft.to})</div>
                  ))}
                  <div className="text-xs mt-2 opacity-75">Review and approve above ⬆️</div>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl px-6 py-4">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {attachment && (
        <div className="mb-3 flex items-center gap-2 bg-teal-50 px-4 py-2 rounded-lg">
          <Paperclip className="w-4 h-4 text-teal-600" />
          <span className="text-sm text-teal-900">{attachment.name}</span>
          <button onClick={removeAttachment} className="ml-auto text-teal-600 hover:text-teal-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="flex gap-2">
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.ppt,.pptx"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="p-3 text-gray-500 hover:bg-gray-100 rounded-xl"
          title="Attach file"
        >
          <Paperclip className="w-5 h-5" />
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          placeholder={`Ask ${config.ea_name} anything...`}
          className="flex-1 px-6 py-3 bg-gray-50 rounded-xl border-2 border-transparent focus:border-teal focus:outline-none"
          disabled={loading}
        />
        <button
          onClick={sendMessage}
          disabled={loading || (!input.trim() && !attachment)}
          className="px-6 py-3 bg-teal text-white rounded-xl hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Send className="w-5 h-5" />
          Send
        </button>
        <button
          onClick={resetConversation}
          className="px-4 py-3 text-gray-500 hover:bg-gray-100 rounded-xl"
          title="Reset conversation"
        >
          Reset
        </button>
      </div>
    </div>
  )
}
