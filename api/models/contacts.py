"""Marshalling models for the shop's contact details."""

from flask_restx import Model, fields

contact_model = Model(
    "Contact",
    {
        "id": fields.Integer(readOnly=True, description="Always 1 — one shop"),
        "address": fields.String(description="Street address"),
        "email": fields.String(description="Contact e-mail"),
        "whatsapp": fields.String(
            description="WhatsApp number in international format. This doubles "
            "as the shop's phone number; there is no separate phone field."
        ),
        "whatsapp_url": fields.String(
            readOnly=True,
            description="Derived wa.me link, with non-digits stripped",
        ),
        "maps_url": fields.String(
            description="Link the address opens, e.g. a Google Maps place URL"
        ),
        "facebook_url": fields.String(description="Facebook page URL"),
        "instagram_url": fields.String(description="Instagram profile URL"),
    },
)

contact_write_model = Model(
    "ContactWrite",
    {
        "address": fields.String(description="Street address"),
        "email": fields.String(description="Contact e-mail"),
        "whatsapp": fields.String(
            description="WhatsApp number, e.g. '+351939320334'"
        ),
        "maps_url": fields.String(
            description="Link the address opens, e.g. a Google Maps place URL"
        ),
        "facebook_url": fields.String(description="Facebook page URL"),
        "instagram_url": fields.String(description="Instagram profile URL"),
    },
)
