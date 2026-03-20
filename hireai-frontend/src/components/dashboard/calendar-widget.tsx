"use client";

import { useCalendarEvents } from "@/hooks/use-dashboard";
import { Calendar, Clock, ExternalLink, Users } from "lucide-react";

function formatEventTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

function getEventType(title: string): { label: string; color: string } {
  const lower = title.toLowerCase();
  if (lower.includes("interview"))
    return { label: "Interview", color: "bg-blue-500/20 text-blue-400" };
  if (lower.includes("viewing") || lower.includes("property"))
    return { label: "Viewing", color: "bg-green-500/20 text-green-400" };
  if (lower.includes("demo"))
    return { label: "Demo", color: "bg-purple-500/20 text-purple-400" };
  if (lower.includes("meeting"))
    return { label: "Meeting", color: "bg-orange-500/20 text-orange-400" };
  return { label: "Event", color: "bg-gray-500/20 text-gray-400" };
}

export function CalendarWidget() {
  const { data, isLoading } = useCalendarEvents(7);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-bg-2 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="h-5 w-5 text-text-3" />
          <h3 className="text-lg font-semibold text-text-1">Upcoming Events</h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-bg-3 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const events = data?.events ?? [];
  const connected = data?.calendar_connected ?? false;

  return (
    <div className="rounded-xl border border-border bg-bg-2 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-text-3" />
          <h3 className="text-lg font-semibold text-text-1">Upcoming Events</h3>
        </div>
        <span className="text-xs text-text-3">Next 7 days</span>
      </div>

      {!connected ? (
        <div className="text-center py-6 text-text-3">
          <Calendar className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">Calendar not connected</p>
          <p className="text-xs mt-1 opacity-60">
            Connect Google Calendar via OAuth to see events
          </p>
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-6 text-text-3">
          <Calendar className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No upcoming events</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[320px] overflow-y-auto">
          {events.slice(0, 8).map((event) => {
            const eventType = getEventType(event.title);
            return (
              <div
                key={event.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-bg-3 hover:bg-bg-3/80 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${eventType.color}`}
                    >
                      {eventType.label}
                    </span>
                    <h4 className="text-sm font-medium text-text-1 truncate">
                      {event.title}
                    </h4>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-text-3">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatEventTime(event.start)}
                    </span>
                    {event.attendees.length > 0 && (
                      <span className="flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        {event.attendees.length}
                      </span>
                    )}
                  </div>
                </div>
                {event.link && (
                  <a
                    href={event.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-text-3 hover:text-text-1 transition-colors"
                    title="Open in Google Calendar"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
