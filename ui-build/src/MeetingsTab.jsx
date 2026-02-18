import { CheckCircle2, XCircle, Clock, AlertCircle, Calendar } from 'lucide-react'

export default function MeetingsTab({ meetings, loading, onRefresh }) {
  const getStatusIcon = (status) => {
    switch(status) {
      case 'confirmed': return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'pending': return <Clock className="w-5 h-5 text-yellow-500" />
      case 'partial': return <AlertCircle className="w-5 h-5 text-orange-500" />
      case 'cancelled': return <XCircle className="w-5 h-5 text-red-500" />
      default: return <Calendar className="w-5 h-5 text-gray-500" />
    }
  }

  const getResponseStatus = (meeting) => {
    if (!meeting.attendee_responses || meeting.attendee_responses.length === 0) {
      return 'No responses yet'
    }
    
    const total = meeting.attendees?.length || 1
    const responses = meeting.attendee_responses.length
    const accepted = meeting.attendee_responses.filter(r => r.status === 'accept').length
    const declined = meeting.attendee_responses.filter(r => r.status === 'decline').length
    
    return `${responses}/${total} responded (${accepted} accepted, ${declined} declined)`
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Upcoming Meetings</h2>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Refresh
        </button>
      </div>

      {meetings.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Calendar className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>No upcoming meetings</p>
        </div>
      ) : (
        <div className="space-y-3">
          {meetings.map((meeting) => (
            <div
              key={meeting.id}
              className="border rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {getStatusIcon(meeting.response_status)}
                    <h3 className="font-semibold text-lg">{meeting.title}</h3>
                  </div>
                  
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>📅 {new Date(meeting.date).toLocaleDateString()} at {meeting.time}</p>
                    <p>⏱️ Duration: {meeting.duration} minutes</p>
                    <p>👥 Attendees: {meeting.attendees?.length || 0}</p>
                    {meeting.description && (
                      <p className="text-gray-500">📝 {meeting.description}</p>
                    )}
                  </div>

                  <div className="mt-3 text-sm">
                    <span className={`inline-block px-2 py-1 rounded ${
                      meeting.response_status === 'confirmed' ? 'bg-green-100 text-green-800' :
                      meeting.response_status === 'partial' ? 'bg-orange-100 text-orange-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {getResponseStatus(meeting)}
                    </span>
                  </div>

                  {meeting.attendee_responses && meeting.attendee_responses.length > 0 && (
                    <div className="mt-3 pt-3 border-t">
                      <p className="text-sm font-semibold mb-2">Responses:</p>
                      <div className="space-y-1">
                        {meeting.attendee_responses.map((response, idx) => (
                          <div key={idx} className="text-sm flex items-center gap-2">
                            {response.status === 'accept' && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                            {response.status === 'decline' && <XCircle className="w-4 h-4 text-red-500" />}
                            {response.status === 'tentative' && <AlertCircle className="w-4 h-4 text-yellow-500" />}
                            <span>{response.email}</span>
                            <span className="text-gray-500">- {response.status}</span>
                            {response.message && (
                              <span className="text-gray-400 italic">"{response.message}"</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
