"""Marshalling models for events — the fairs and markets the workshop attends."""

from flask_restx import Model, fields

from api.models.common import pagination_model

event_model = Model(
    "Event",
    {
        "id": fields.Integer(readOnly=True, description="Event ID"),
        "name": fields.String(
            required=True, description="Event name, e.g. 'Feira de Artesanato'"
        ),
        "location": fields.String(description="Where it took place"),
        "description": fields.String(description="Optional note about the event"),
        "starts_on": fields.String(
            required=True, description="First day, ISO format (YYYY-MM-DD)"
        ),
        "ends_on": fields.String(
            description="Last day, ISO format. Omit for a single-day event."
        ),
        "url": fields.String(description="Optional link to the event"),
        "year": fields.String(
            readOnly=True, description="Derived from starts_on, for grouping"
        ),
    },
)

event_list_model = Model(
    "EventList",
    {
        "events": fields.List(fields.Nested(event_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

event_write_model = Model(
    "EventWrite",
    {
        "name": fields.String(required=True, description="Event name"),
        "location": fields.String(description="Where it took place"),
        "description": fields.String(description="Optional note"),
        "starts_on": fields.String(
            required=True, description="First day, ISO format (YYYY-MM-DD)"
        ),
        "ends_on": fields.String(description="Last day, ISO format"),
        "url": fields.String(description="Optional link"),
    },
)
