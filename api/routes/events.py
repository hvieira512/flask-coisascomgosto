"""Events: the fairs, markets and shows the workshop has taken part in.

Reads are public — the landing page timeline uses them. Writes require a session,
since only the owners should be adding to the shop's history.
"""

from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.common import pagination_model
from api.models.events import event_list_model, event_model, event_write_model
from api.repositories import EventRepository
from api.routes.crud import page_of
from api.security import PROTECTED_DOC, auth_required

ns = Namespace("events", description="Fairs and markets the workshop attended")

for model in [pagination_model, event_model, event_list_model, event_write_model]:
    ns.models[model.name] = model


@ns.route("/")
class EventList(Resource):
    @ns.marshal_with(event_list_model)
    @ns.param("q", "Search term for event name or location (fuzzy search)")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of events, most recent first")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List events, most recent first."""
        with get_db_connection() as (_, cursor):
            return page_of(EventRepository(cursor), "events")

    @ns.doc(**PROTECTED_DOC)
    @ns.expect(event_write_model, validate=True)
    @ns.marshal_with(event_model, code=201)
    @ns.response(201, "Event created")
    @ns.response(400, "Missing or invalid fields")
    @auth_required
    def post(self):
        """Add an event to the workshop's history."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            events = EventRepository(cursor)
            event_id = events.create(
                name=data["name"],
                starts_on=data["starts_on"],
                location=data.get("location"),
                description=data.get("description"),
                ends_on=data.get("ends_on"),
                url=data.get("url"),
            )
            return events.get(event_id), 201


@ns.route("/<int:event_id>")
@ns.param("event_id", "The event identifier")
class Event(Resource):
    @ns.marshal_with(event_model)
    @ns.response(200, "The event")
    @ns.response(404, "Event not found")
    def get(self, event_id):
        """Get an event by ID."""
        with get_db_connection() as (_, cursor):
            event = EventRepository(cursor).get(event_id)
            if not event:
                ns.abort(404, f"Event #{event_id} not found")

            return event

    @ns.doc(**PROTECTED_DOC)
    @ns.expect(event_write_model, validate=True)
    @ns.marshal_with(event_model)
    @ns.response(200, "Event updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Event not found")
    @auth_required
    def put(self, event_id):
        """Update an event."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            events = EventRepository(cursor)

            if not events.exists(event_id):
                ns.abort(404, f"Event #{event_id} not found")

            events.update(
                event_id,
                name=data["name"],
                starts_on=data["starts_on"],
                location=data.get("location"),
                description=data.get("description"),
                ends_on=data.get("ends_on"),
                url=data.get("url"),
            )
            return events.get(event_id), 200

    @ns.doc(**PROTECTED_DOC)
    @ns.marshal_with(event_model)
    @ns.response(200, "The deleted event")
    @ns.response(404, "Event not found")
    @auth_required
    def delete(self, event_id):
        """Remove an event."""
        with get_db_connection() as (_, cursor):
            events = EventRepository(cursor)

            event = events.get(event_id)
            if not event:
                ns.abort(404, f"Event #{event_id} not found")

            events.delete(event_id)
            return event, 200
