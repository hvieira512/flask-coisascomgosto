"""The shop's contact details.

A singleton resource: there is one set of details for the shop, so the endpoint
is `/contacts/` with no ID. GET is public (the footer and landing page read it);
PUT replaces the whole record.
"""

from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.contacts import contact_model, contact_write_model
from api.repositories import ContactRepository
from api.security import PROTECTED_DOC, token_required

ns = Namespace(
    "contacts",
    description="Shop contact details. Every endpoint requires a bearer token; "
    "the public site reads these server-side, not through the API.",
)

for model in [contact_model, contact_write_model]:
    ns.models[model.name] = model


@ns.route("/")
class Contact(Resource):
    @ns.doc(**PROTECTED_DOC)
    @ns.marshal_with(contact_model)
    @ns.response(200, "The shop's contact details")
    @ns.response(404, "Contact details have not been set up")
    @token_required
    def get(self):
        """Get the shop's address, email and social links."""
        with get_db_connection() as (_, cursor):
            contact = ContactRepository(cursor).get()
            if not contact:
                ns.abort(404, "Contact details have not been set up.")

            return contact

    @ns.doc(**PROTECTED_DOC)
    @ns.expect(contact_write_model, validate=True)
    @ns.marshal_with(contact_model)
    @ns.response(200, "Contact details updated")
    @ns.response(400, "Invalid fields")
    @token_required
    def put(self):
        """Replace the shop's contact details.

        Every field is optional; omitting one clears it.
        """
        data = ns.payload

        with get_db_connection() as (_, cursor):
            contacts = ContactRepository(cursor)
            contacts.update(
                address=data.get("address"),
                email=data.get("email"),
                whatsapp=data.get("whatsapp"),
                maps_url=data.get("maps_url"),
                facebook_url=data.get("facebook_url"),
                instagram_url=data.get("instagram_url"),
            )
            return contacts.get(), 200
