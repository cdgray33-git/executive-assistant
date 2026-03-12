import React, { useState, useEffect } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const localizer = momentLocalizer(moment);

function CalendarView() {
    const [events, setEvents] = useState([]);
    const [selectedEvent, setSelectedEvent] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadEvents();
    }, []);

    const loadEvents = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/calendar/events?days=90');
            const data = await response.json();
            
            if (data.status === 'success' && data.events) {
                // Transform to react-big-calendar format
                const calendarEvents = data.events.map(event => ({
                    id: event.id,
                    title: event.title,
                    start: new Date(`${event.date}T${event.time}`),
                    end: new Date(new Date(`${event.date}T${event.time}`).getTime() + event.duration * 60000),
                    resource: event // Store full event data
                }));
                setEvents(calendarEvents);
            }
        } catch (error) {
            console.error('Error loading calendar events:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSelectEvent = (event) => {
        setSelectedEvent(event.resource);
    };

    const closeModal = () => {
        setSelectedEvent(null);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-xl">Loading calendar...</div>
            </div>
        );
    }

    return (
        <div className="p-6 h-screen flex flex-col">
            <h1 className="text-3xl font-bold mb-6">Calendar</h1>
            
            <div className="flex-1 bg-white rounded-lg shadow-lg p-4">
                <Calendar
                    localizer={localizer}
                    events={events}
                    startAccessor="start"
                    endAccessor="end"
                    style={{ height: '100%' }}
                    onSelectEvent={handleSelectEvent}
                    views={['month']}
                    defaultView="month"
                />
            </div>

            {/* Event Details Modal */}
            {selectedEvent && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full mx-4">
                        <div className="flex justify-between items-start mb-4">
                            <h2 className="text-2xl font-bold">{selectedEvent.title}</h2>
                            <button
                                onClick={closeModal}
                                className="text-gray-500 hover:text-gray-700 text-2xl"
                            >
                                ×
                            </button>
                        </div>
                        
                        <div className="space-y-3">
                            <div>
                                <span className="font-semibold">Date:</span>{' '}
                                {moment(selectedEvent.date).format('dddd, MMMM D, YYYY')}
                            </div>
                            
                            <div>
                                <span className="font-semibold">Time:</span>{' '}
                                {moment(selectedEvent.time, 'HH:mm:ss').format('h:mm A')}
                            </div>
                            
                            <div>
                                <span className="font-semibold">Duration:</span>{' '}
                                {selectedEvent.duration} minutes
                            </div>
                            
                            {selectedEvent.attendees && selectedEvent.attendees.length > 0 && (
                                <div>
                                    <span className="font-semibold">Attendees:</span>
                                    <ul className="list-disc list-inside ml-4 mt-1">
                                        {selectedEvent.attendees.map((attendee, idx) => (
                                            <li key={idx}>{typeof attendee === "object" ? attendee.email || attendee.name : attendee}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            
                            {selectedEvent.description && (
                                <div>
                                    <span className="font-semibold">Description:</span>
                                    <p className="mt-1 text-gray-700">{selectedEvent.description}</p>
                                </div>
                            )}
                            
                            <div>
                                <span className="font-semibold">Status:</span>{' '}
                                <span className={`px-2 py-1 rounded text-sm ${
                                    selectedEvent.status === 'confirmed' ? 'bg-green-100 text-green-800' :
                                    selectedEvent.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-gray-100 text-gray-800'
                                }`}>
                                    {selectedEvent.status}
                                </span>
                            </div>
                        </div>
                        
                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={closeModal}
                                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default CalendarView;
